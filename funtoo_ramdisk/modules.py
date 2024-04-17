#!/usr/bin/python3

import glob
import os
import re
import shutil
import subprocess
from collections import defaultdict

from funtoo_ramdisk.log import get_logger


class ModuleScanner:

	"""
	This class exists to scan for kernel modules, and also help us to determine dependencies of kernel modules,
	so we grab all the necessary ones for an initramfs.

	In the constructor, ``root`` is the root filesystem -- which defaults to "/". The kernel modules we look at
	are assumed to exist at ``os.path.join(self.root, "lib/modules", self.kernel_version)``. Any sub-paths we
	look at are assumed to be relative to this path.

	``self.copy_config``: A dictionary, which contains three key-value pairs: "sections", which is a defaultdict
	containing K:V pairs of each section name (string) and the value being a set of all absolute file path
	to all associated modules included in the section (including dependencies of these modules.). In addition,
	a dict key-value pair: "by_name", which will map each module name (i.e. "ext4") to the absolute path of
	that module. The "names_in_sections" is used to map kernel module short names ("ext4") to the set of sections
	it is in.

	Remember (or understand) that a module can be included in more than one section. "by_name" is the global
	list of modules across all sections. It should also not be considered authoritative. That is, we may mask
	out stuff in "by_name". Use "names_in_sections" as the authoritative list of modules for each section.

	``self.copy_config_mask`` contains a set of all module short-names that are masked out in each section.
	We record this because we have to grab all the masks and process them at the end.
	"""

	def __init__(self, modconfig, kernel_version, copy_lines=None, autoload_lines=None, root="/", logger=None):
		self.modconfig = modconfig
		self.root = root
		self.kernel_version = kernel_version
		self.copy_lines = copy_lines
		self.autoload_lines = autoload_lines
		self.log = get_logger()
		self.builtins_by_name = {}
		self.builtins_by_path = set()
		self.copy_config = {
			"sections": defaultdict(set),
			"by_name": {},
			"names_in_sections": defaultdict(set)
		}
		self.copy_config_mask = defaultdict(set)
		self.autoload_sections = []

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
				fang = os.path.normpath(re.sub(f'^insmod ', '', line).split()[0])
				if fang.startswith("//"):
					# The mechanism we use gives us a double "/" if self.root == "/", and this breaks stuff. This is a workaround:
					fang = fang[1:]
				out_set.add(fang)
		return out_set

	def recursively_get_module_paths(self, scan_dir, root=None) -> set:
		"""
		Given a "scan dir", which is a module sub-path relative to "/lib/modules/<kernel_name>/", scan for all kernel modules, and return
		their absolute paths in a set.

		For each module we find, we also need to scan for any dependencies it has. So, we will call ``get_module_deps_by_name`` for each
		module found.
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
		"""
		This method will look in the module path rooted at ``root`` (defaulting to ``self.root``) and find all modules
		that match the glob.

		This is used for finding modules to copy and also scanning already-copied modules, with ``root=initramfs_root``.
		"""
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

	def get_specific_module(self, entry, root=None):
		"""
		Walk paths and find a specific module by name.
		"""
		if root is None:
			root = self.root
		scan_path = os.path.join(root, "lib/modules", self.kernel_version)
		find_me = f"{entry}.ko"
		for path, dirs, fns in os.walk(scan_path):
			for fn in fns:
				if fn == find_me:
					return self.get_module_deps_by_name(entry)
		raise FileNotFoundError(f"Could not find kernel module: {entry}")

	def process_copy_line(self, section, entry: str) -> set:
		"""
		This method processes a single line in a ``modules.copy`` file.
		"""
		out_set = set()
		if entry.startswith("-"):
			# This is a mask entry, which gets applied later:
			self.copy_config_mask[section].add(entry[1:].strip())
			self.log.debug(f"Module {entry[1:]} mask recorded for {section} section.")
		elif entry.endswith("/**"):
			out_set |= self.recursively_get_module_paths(entry[:-3])
		elif "/" not in entry:
			# literal module name, get module and deps:
			out_set |= self.get_specific_module(entry)
		else:
			# assume glob:
			out_set |= self.glob_walk_module_paths(entry)
		return out_set

	def process_copy_config(self):
		"""
		This method processes a ``modules.copy`` file which has a simplified ini-style format:

		  [ethernet]
		  kernel/drivers/net/ethernet/**

		  [iscsi]
		  kernel/drivers/scsi/*iscsi*      # glob
		  kernel/drivers/target/iscsi/**   # include entire tree
		  -scsi_debug                      # exclude by module name
		  foobar						   # include by module name

		When we specify a module or a bunch of modules, we will also grab all *dependencies* of these
		modules.

		Masking of modules you want to exclude via the "-(modname)" is supported, and this step is
		performed in a second phase. We remove these modules from being included in the initramfs if
		they are not included by another section.

		TODO: Also remove any modules that are unused that were dependent on the to-be-masked module.
		      Right now, we could possibly include some extra modules needed by masked modules. To
		      fix this, ``self.get_module_deps_by_name()`` should return a tuple of the original module
		      and its dependencies. Then we should not create a final set of modules until masking is
		      done. This will allow us to wipe a masked module, plus its dependencies. This will be nice
		      but is not a critical feature as masking is currently used to remove "naughty" modules
		      that cause problems rather than just general trimming of module bloat.

		This file will be scanned, and a bunch of information will be returned (see ``return``, below.)

		:param config_file: the file to read.
		"""
		section = None
		for line in self.copy_lines:
			line = line.strip()
			if line.startswith("[") and line.endswith("]"):
				section = line[1:-1]
				continue
			elif not len(line):
				continue
			elif line.startswith("#"):
				continue
			new_items = self.process_copy_line(section, line)
			self.copy_config["sections"][section] |= new_items
			for mod_path in new_items:
				mod_name = os.path.basename(mod_path)[:-3]  # strip .ko
				self.copy_config["by_name"][mod_name] = mod_path
				self.copy_config["names_in_sections"][mod_name].add(section)

		# Process masks. Modules masked from existence will not be purged from ``self.copy_config["by_name"]``, though,
		# so use it only for lookups and not as authoritative list of all modules to copy or expect on initramfs:

		for section, names_to_mask in self.copy_config_mask.items():
			if names_to_mask.intersection(self.copy_config["by_name"]):
				for mod_name in names_to_mask:
					self.log.debug(f"Removing {mod_name} from {section} due to mask.")
					mod_path_to_remove = self.copy_config["by_name"][mod_name]
					self.copy_config["sections"][section] -= {mod_path_to_remove}
					self.copy_config["names_in_sections"][mod_name] -= {section}

	def copy_modules_to_initramfs(self, initramfs_root, strip_debug=True):
		out_path = os.path.join(initramfs_root, "lib/modules", self.kernel_version)
		if not os.path.exists(out_path):
			os.makedirs(out_path, exist_ok=True)
		if not os.path.isdir(out_path):
			raise FileExistsError(f"{out_path} is not a directory -- cannot continue.")
		src_modroot = os.path.join(self.root, "lib/modules", self.kernel_version)
		src_modroot_len = len(src_modroot)
		mod_count = 0

		# This will contain things like "kernel/fs/ext4.ko" and we will use it later to filter the ``modules`.order`` file.
		all_subpaths = set()

		all_mods_names = set()

		for mod_name, sections in self.copy_config["names_in_sections"].items():
			if not len(sections):
				# This module was masked out of any sections, so we don't need to copy it:
				continue
			else:
				all_mods_names.add(mod_name)

		all_masked = set()
		for masked_set in self.copy_config_mask.values():
			all_masked |= masked_set

		stray_mods = sorted(list(all_mods_names.intersection(all_masked, all_mods_names)))
		if stray_mods:
			out = """The following modules were copied to the initramfs, even though they were
masked in a section. This could indicate a mask that was added to the wrong
section, or an incomplete masking. Please review modules.copy entries for
the following masked modules:\n\n"""
			for mod in stray_mods:
				out += f"  * {mod}: still included by sections: {' '.join(self.copy_config['names_in_sections'][mod])}\n"
			self.log.warning(out)
		for mod_name in all_mods_names:
			mod_abs = self.copy_config["by_name"][mod_name]
			# This gets us the "kernel/fs/ext4.ko" path:
			sub_path = mod_abs[src_modroot_len:].lstrip("/")
			all_subpaths.add(sub_path)
			mod_abs_dest = os.path.join(out_path, sub_path)
			os.makedirs(os.path.dirname(mod_abs_dest), exist_ok=True)
			shutil.copy(mod_abs, mod_abs_dest)
			mod_count += 1

		if strip_debug:
			subprocess.getstatusoutput(f'cd "{initramfs_root}" && find -iname "*.ko" -exec strip --strip-debug {{}} \\;')
		for mod_file in ["modules.builtin", "modules.builtin.modinfo"]:
			mod_path = os.path.join(src_modroot, mod_file)
			if os.path.exists(mod_path):
				shutil.copy(mod_path, out_path)

		# Copy over modules.order file, but strip out lines for modules that don't exist on the initramfs. This is actually
		# pretty easy to do, and is an easy way to get a total copied modules count:

		mod_order = os.path.join(src_modroot, "modules.order")
		if os.path.exists(mod_order):
			with open(mod_order, "r") as mod_f:
				with open(os.path.join(out_path, "modules.order"), "w") as mod_f_out:
					for line in mod_f.readlines():
						if line.strip() in all_subpaths:
							mod_f_out.write(line)

		self.log.info(f"[turquoise2]{mod_count}[default] kernel modules copied to initramfs.")

	def process_autoload_config(self, initramfs_root):
		out_dict = defaultdict(list)
		section = None
		lineno = 1
		for line in self.autoload_lines:
			found_mods = set()
			line = line.strip()
			if line.startswith("[") and line.endswith("]"):
				section = line[1:-1]
				self.autoload_sections.append(section)
				self.log.debug(f"process_autoload_config: section {section}")
				lineno += 1
				continue
			elif not len(line):
				lineno += 1
				continue
			elif line.startswith("#"):
				lineno += 1
				continue
			if "/" not in line and not line.endswith(".ko"):

				# We are directly-specifying a module name like "ext4". Make sure it was copied. This following conditional
				# is how to check -- is it in at least one section? (remember, don't use copy_config["by_name"], as it may
				# include masked (removed) modules:

				kmod = line
				if kmod in self.copy_config["names_in_sections"] and len(self.copy_config["names_in_sections"][kmod]):

					if section not in self.copy_config["names_in_sections"][kmod]:
						self.log.warning(f"""modules.autoload, line {lineno}: You are specifying a module to autoload that was added to other sections: 

  {self.copy_config['names_in_sections'][kmod]}
  
You should fix this so that the module you are asking to autoload is also included in the '{section}' section.
""")
					out_dict[section] += [kmod]
				else:
					if kmod in self.builtins_by_name:
						self.log.debug(f"Module {kmod} referenced in modules.autoload is built-in to the kernel.")
					else:
						self.log.debug(repr(self.copy_config['names_in_sections']))
						raise ValueError(f"modules.autoload, section {section}, line {lineno}: Specified kernel module {kmod} was not copied to initramfs and is not built-in to kernel.")
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
		self.process_copy_config()
		self.copy_modules_to_initramfs(initramfs_root=initial_ramdisk.initramfs_root)
		retval = os.system(f'/sbin/depmod -b "{initial_ramdisk.initramfs_root}" {self.kernel_version}')
		if retval:
			raise OSError(f"Encountered error {retval} when running depmod.")
		auto_out = self.process_autoload_config(
			initramfs_root=initial_ramdisk.initramfs_root
		)
		# Write out category files which will be used by the autoloader on the initramfs
		os.makedirs(os.path.join(initial_ramdisk.initramfs_root, "etc/modules"), exist_ok=True)
		for mod_cat, mod_names in auto_out.items():
			with open(os.path.join(initial_ramdisk.initramfs_root, "etc/modules", mod_cat), "w") as f:
				for mod in mod_names:
					f.write(f"{mod}\n")
			self.log.debug(f"Wrote {len(mod_names)} modules to /etc/modules/{mod_cat}")
		with open(os.path.join(initial_ramdisk.initramfs_root, "etc/modules.autoload"), "w") as f:
			for sect in self.autoload_sections:
				f.write(f"{sect}\n")
