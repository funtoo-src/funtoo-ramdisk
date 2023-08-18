#!/usr/bin/python3

import glob
import logging
import os
import re
import shutil
import subprocess
from collections import defaultdict


class ModuleScanner:

	"""
	This class exists to scan for kernel modules, and also help us to determine dependencies of kernel modules, so we grab all the
	necessary ones for an initramfs.

	In the constructor, ``root`` is the root filesystem -- which defaults to "/". The kernel modules we look at are assumed to exist at
	``os.path.join(self.root, "lib/modules", self.kernel_version)``. Any sub-paths we look at are assumed to be relative to this
	path.
	"""

	def __init__(self, kernel_version, root="/" ):
		self.root = root
		self.kernel_version = kernel_version
		self.log = logging.getLogger("ramdisk")

		self.builtins_by_name = {}
		self.builtins_by_path = set()

		# Create a list of built-in modules. Use this list in our sanity checks. If a module is built-in to the
		# kernel, we won't be able to copy it to the initramfs, and that's OK. It's still "there" in spirit.
		# Due to our use of os.walk() and globs for finding modules most of the time, this only will surface as
		# a real-world issue when we are literally specifying a module we want to autoload, like "xfs", which
		# is built-in. We want to fail if the module isn't on the initramfs -- and if it's not also built-in.

		builtin_path = os.path.join(self.root, "lib/modules", self.kernel_version, "modules.builtin")
		with open(builtin_path, "r") as bif:
			for line in bif.readlines():
				line = line.strip()
				if not line:
					continue
				builtin_mod_name = os.path.basename(line)[:-3]  # strip .ko
				self.builtins_by_name[builtin_mod_name] = line
				self.builtins_by_path.add(line)

	def get_module_deps_by_name(self, mod: str) -> set:
		"""
		Given a "mod", which is a name of a module like "ext4", return a list of full paths of this module and any dependent modules
		that must exist for this module to work.

		The idea here is if ``mod_list`` is "ext4", we will get a list of the path to the ext4.ko module as well as any other modules
		it needs. We can then copy these to the initramfs.
		"""
		out_set = set()
		# The /var/cache is a bogus directory to override the default /etc/modprobe.d
		status, out = subprocess.getstatusoutput(f"modprobe -C /var/cache -d {self.root} -S {self.kernel_version} --show-depends {mod}")
		if status != 0:
			self.log.error(f"Kernel module {mod} not found; continuing...")
		for line in out.split("\n"):
			# If it's a built-in, we don't need to copy it, because it's in the kernel:
			if line.startswith("builtin "):
				continue
			else:
				# remove provided "insmod " prefix, the split is there because module options from /etc/modprobe.d can be after the path:
				out_set.add(re.sub(f'^insmod {self.root}', '', line).split()[0].strip())
		return out_set

	def recursively_get_module_paths(self, scan_dir, root=None) -> set:
		"""
		Given a "scan dir", which is a module sub-path relative to "/lib/modules/<kernel_name>/" which is specified in ``INSTALL_MOD_PATH``,
		scan for all kernel modules, and return their absolute paths in a set.

		For each module we find, we also need to scan for any dependencies it has. So, we will call ``get_module_deps_by_name`` for each
		module found.

		Note that the optional keyword argument ``root=`` can be used to specify an alternate root, which ``process_autoload_config``
		actually uses to scan the initramfs for already-copied modules when building the autoload lists.
		"""
		out_set = set()
		if root is None:
			root = self.root
		scan_path = os.path.join(root, "lib/modules", self.kernel_version, scan_dir)
		if not os.path.isdir(scan_path):
			self.log.error(f"recursively_get_module_deps: Can't find directory {scan_path}")
			return out_set
		for path, dirs, fns in os.walk(scan_path):
			for fn in fns:
				if fn.endswith(".ko"):
					out_set |= self.get_module_deps_by_name(fn[:-3])
		return out_set

	def glob_walk_module_paths(self, entry, root=None):
		out_set = set()
		if root is None:
			root = self.root
		search_path = os.path.join(root, "lib/modules", self.kernel_version, entry)
		for match in glob.glob(search_path):
			if not match.endswith(".ko"):
				continue
			module_name = os.path.basename(match)[:-3]  # strip .ko
			out_set |= self.get_module_deps_by_name(module_name)
		return out_set

	def process_copy_line(self, entry : str) -> set:
		"""
		This method processes a single line in a ``modules.copy`` file. We support two formats::

		  kernel/fs/**

		The above means: recursively scan ``kernel/fs`` for all kernel modules, and return a set of all modules found, and their
		dependencies.

		The other format we can use is (this is two examples, only pass one of these strings in ``entry`` at a time):

		  kernel/fs/ext4.ko
		  drivers/net/foo*

		The two examples above are both treated as globs -- we will find all matches, and then return a set containing all matches,
		as well as the dependencies of all matches.
		:param entry:
		:return:
		"""
		out_set = set()
		if entry.endswith("/**"):
			out_set |= self.recursively_get_module_paths(entry[:-3])
		else:
			out_set |= self.glob_walk_module_paths(entry)
		return out_set

	def process_copy_config(self, config_file) -> dict:
		"""
		This method processes a ``modules.copy`` file which has a simplified ini-style format:

		  [ethernet]
		  kernel/drivers/net/ethernet/**

		  [iscsi]
		  kernel/drivers/scsi/*iscsi*
		  kernel/drivers/target/iscsi/**

		This file will be scanned, and a bunch of information will be returned (see ``return``, below.)

		:param config_file: the file to read.
		:return: Return a dictionary, which contains two key-value pairs: "sections", which is a defaultdict
		         containing K:V pairs of each section name (string) and the value being a set of all absolute
		         file paths to all associated modules included in the section (including dependencies of
		         these modules.). In addition, a dict key-value pair: "by_name", which will map each module
		         name (i.e. "ext4") to the absolute path of that module.
		"""
		out_dict = {
			"sections": defaultdict(set),
			"by_name": {}
		}
		section = None
		with open(config_file, "r") as cfg:
			for line in cfg.read().split("\n"):
				line = line.strip()
				if line.startswith("[") and line.endswith("]"):
					section = line[1:-1]
					continue
				elif not len(line):
					continue
				elif line.startswith("#"):
					continue
				new_items = self.process_copy_line(line)
				out_dict["sections"][section] |= new_items
				for mod_path in new_items:
					mod_name = os.path.basename(mod_path)[:-3] # strip .ko
					out_dict["by_name"][mod_name] = mod_path
		return out_dict

	def copy_modules_to_initramfs(self, copy_output, initramfs_root, strip_debug=True):
		out_path = os.path.join(initramfs_root, "lib/modules", self.kernel_version)
		strip_path = os.path.join(self.root, "lib/modules", self.kernel_version)
		strip_len = len(strip_path)
		mod_count = 0

		# This will contain things like "kernel/fs/ext4.ko" and we will use it later to filter the ``modules`.order`` file.
		all_subpaths = set()

		for mod_name, mod_abs in copy_output["by_name"].items():
			# This gets us the "kernel/fs/ext4.ko" path:
			sub_path = mod_abs[strip_len:].lstrip("/")
			all_subpaths.add(sub_path)
			mod_abs_dest = os.path.join(out_path, sub_path)
			os.makedirs(os.path.dirname(mod_abs_dest), exist_ok=True)
			shutil.copy(mod_abs, mod_abs_dest)
			mod_count += 1
		if strip_debug:
			subprocess.getstatusoutput(f'cd "{initramfs_root}" && find -iname "*.ko" -exec strip --strip-debug {{}} \\;')
		for mod_file in [ "modules.builtin", "modules.builtin.modinfo" ]:
			mod_path = os.path.join(strip_path, mod_file)
			if os.path.exists(mod_path):
				shutil.copy(mod_path, out_path)

		# Copy over modules.order file, but strip out lines for modules that don't exist on the initramfs. This is actually
		# pretty easy to do:

		mod_order = os.path.join(strip_path, "modules.order")
		if os.path.exists(mod_order):
			with open(mod_order, "r") as mod_f:
				with open(os.path.join(out_path, "modules.order"), "w") as mod_f_out:
					for line in mod_f.readlines():
						if line.strip() in all_subpaths:
							mod_f_out.write(line)

		self.log.info(f"{mod_count} kernel modules copied to initramfs.")

	def process_autoload_config(self, config_file, copy_output, initramfs_root):
		"""

		"""
		out_dict = defaultdict(list)
		section = None
		lineno = 1
		with open(config_file, "r") as cfg:
			for line in cfg.read().split("\n"):
				found_mods = set()
				line = line.strip()
				if line.startswith("[") and line.endswith("]"):
					section = line[1:-1]
					continue
				elif not len(line):
					continue
				elif line.startswith("#"):
					continue
				if "/" not in line and not line.endswith(".ko"):
					# We are directly-specifying a module name like "ext4". Make sure it was copied:
					if line not in copy_output["by_name"]:
						if line in self.builtins_by_name:
							self.log.debug(f"Module {line} referenced in modules.autoload is built-in to the kernel.")
						else:
							raise ValueError(f"modules.autoload, line {lineno}: Specified kernel module {line} was not copied to initramfs and is not built-in to kernel.")
					else:
						out_dict[section] += [line]
				elif line.endswith("/**"):
					# Recursively scan the specified directory on the initramfs for all matching
					# already-copied modules, and set these to autoload:
					found_mods = self.recursively_get_module_paths(line[:-3], initramfs_root)
				else:
					# Scan the initramfs and match glob against all already-copied modules, and set these to autoload:
					found_mods = self.glob_walk_module_paths(line, root=initramfs_root)
				# Convert all absolute paths of modules to raw module names, which is what the initramfs autoloader uses:
				for mod in sorted(list(found_mods)):
					out_dict[section] += [os.path.basename(mod)[:-3]]
				lineno += 1
		return out_dict

	def populate_initramfs(self, initial_ramdisk):
		copy_out = self.process_copy_config(os.path.join(initial_ramdisk.support_root, "modules.copy"))
		self.copy_modules_to_initramfs(copy_out, initramfs_root=initial_ramdisk.root)
		retval = os.system(f'/sbin/depmod -b "{initial_ramdisk.root}" {self.kernel_version}')
		if retval:
			raise OSError(f"Encountered error {retval} when running depmod.")
		auto_out = self.process_autoload_config(
			os.path.join(initial_ramdisk.support_root, "modules.autoload"),
			copy_out,
			initramfs_root=initial_ramdisk.root
		)
		# Write out category files which will be used by the autoloader on the initramfs
		os.makedirs(os.path.join(initial_ramdisk.root, "etc/modules"), exist_ok=True)
		for mod_cat, mod_names in auto_out.items():
			with open(os.path.join(initial_ramdisk.root, "etc/modules", mod_cat), "w") as f:
				for mod in mod_names:
					f.write(f"{mod}\n")

