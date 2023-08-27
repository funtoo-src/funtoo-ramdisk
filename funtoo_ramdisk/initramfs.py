#!/usr/bin/python3
import importlib
import logging
import os
import pkgutil
import shutil
import site
import subprocess

from .modules import ModuleScanner
from .utilities import copy_binary


class InitialRamDisk:
	base_dirs = [
		"dev",
		"bin",
		"etc",
		"usr",
		"mnt",
		"run",
		"sbin",
		"proc",
		"tmp",
		"sys",
		".initrd",
		"sbin",
		"usr/bin",
		"usr/sbin"
	]

	comp_methods = {
		"xz": {
			"ext": "xz",
			"cmd": ["xz", "-e", "-T 0", "--check=none", "-z", "-f", "-5", "-c"]
		},
		"zstd": {
			"ext": "zst",
			"cmd": ["zstd", "-f", "-10", "-c"]
		}
	}

	def __init__(self, action, temp_root, support_root, kernel_version, compression,
				modules_root="/",
				logger=None,
				pypath=None,
				enabled_plugins=None
		):
		self.action = action
		self.enabled_plugins = {"core"}
		if enabled_plugins:
			self.enabled_plugins |= set(enabled_plugins)
		self.temp_root = temp_root
		self.initramfs_root = os.path.join(self.temp_root, "initramfs")
		os.makedirs(self.initramfs_root)
		self.support_root = support_root
		self.modules_root = modules_root
		if pypath is not None:
			self.py_mod_path = [os.path.join(pypath, "plugins")]
		else:
			self.py_mod_path = [site.getsitepackages(), "funtoo_ramdisk/plugins"]
		if logger:
			self.log = logger
		else:
			self.log = logging.getLogger("ramdisk")
		self.module_scanner = ModuleScanner(kernel_version=kernel_version, root=self.modules_root, logger=self.log)
		self.size_initial = None
		self.size_final = None
		self.size_compressed = None
		if compression not in self.comp_methods.keys():
			raise ValueError(f"Specified compression method must be one of: {' '.join(sorted(list(self.comp_methods.keys())))}.")
		self.compression = compression
		self.plugins = {}
		for plugin in pkgutil.iter_modules(self.py_mod_path, "funtoo_ramdisk.plugins."):
			mod = importlib.import_module(plugin.name)
			iter_plugins = getattr(mod, "iter_plugins", None)
			if not iter_plugins:
				self.log.warning(f"Plugin {plugin.name} is missing an iter_plugins function; skipping.")
			else:
				for plugin_obj in iter_plugins():
					plugin_obj_inst = plugin_obj(self)
					self.plugins[plugin_obj.key] = plugin_obj_inst
		if self.plugins:
			out_list = []
			for plugin in sorted(self.plugins.keys()):
				if plugin in self.enabled_plugins:
					out_list.append(f"[orange1]{plugin}[default]")
				else:
					out_list.append(f"[turquoise2]{plugin}[default]")
			self.log.info(f"Registered plugins: {'/'.join(out_list)}")

	def iter_plugins(self):
		for plugin in self.plugins.keys():
			if plugin in self.enabled_plugins:
				self.log.info(f"Running [orange1]{plugin}[default] plugin...")
				success = self.plugins[plugin].run()
				if not success:
					self.log.error("Exiting due to failed plugin.")
					return False
		return True

	def create_baselayout(self):
		for dir_name in self.base_dirs:
			os.makedirs(os.path.join(self.initramfs_root, dir_name), exist_ok=True)
		os.makedirs(os.path.join(self.initramfs_root, "lib"), exist_ok=True)
		os.symlink("lib", os.path.join(self.initramfs_root, "lib64"))
		os.symlink("../lib", os.path.join(self.initramfs_root, "usr/lib"))
		os.symlink("../lib", os.path.join(self.initramfs_root, "usr/lib64"))

	def create_fstab(self):
		with open(os.path.join(self.initramfs_root, "etc/fstab"), "w") as f:
			f.write("/dev/ram0     /           ext2    defaults        0 0\n")
			f.write("proc          /proc       proc    defaults        0 0\n")

	def setup_linuxrc_and_etc(self):
		dest = os.path.join(self.initramfs_root, "init")
		shutil.copy(os.path.join(self.support_root, "linuxrc"), dest)
		os.symlink("init", os.path.join(self.initramfs_root, "linuxrc"))
		os.symlink("../init", os.path.join(self.initramfs_root, "sbin/init"))
		for file in os.listdir(os.path.join(self.support_root, "etc")):
			shutil.copy(os.path.join(self.support_root, "etc", file), os.path.join(self.initramfs_root, "etc"))
		for x in ["init", "etc/initrd.scripts", "etc/initrd.defaults"]:
			os.chmod(os.path.join(self.initramfs_root, x), 0O755)

	def setup_busybox(self):
		self.copy_binary("/bin/busybox")
		self.copy_binary("/sbin/modprobe")
		# Make sure these applets exist even before we tell busybox to create all the applets on initramfs:
		for applet in [
			"ash",
			"sh",
			"mount",
			"uname",
			"echo",
			"cut",
			"cat",
			"modprobe",
			"lsmod",
			"depmod",
			"modinfo"
		]:
			os.symlink("busybox", os.path.join(self.initramfs_root, "bin", applet))

	@property
	def temp_initramfs(self):
		return os.path.join(self.temp_root, "initramfs.cpio")

	def create_ramdisk_binary(self):
		# We use a "starter" initramfs.cpio with some pre-existing device nodes, because the current user may
		# not have permission to create literal device nodes on the local filesystem:
		shutil.copy(os.path.join(self.support_root, "initramfs.cpio"), self.temp_initramfs)
		status = os.system(f'( cd "{self.initramfs_root}" && find . -print | cpio --quiet -o --format=newc --append -F "{self.temp_initramfs}" )')
		if status:
			raise OSError(f"cpio creation failed with error code {status}")
		if not os.path.exists(self.temp_initramfs):
			raise FileNotFoundError(f"Expected file {self.temp_initramfs} did not get created.")
		self.size_initial = os.path.getsize(self.temp_initramfs)
		self.log.debug(f"Created {self.temp_initramfs} / Size: {self.size_initial / 1000000:.2f} MiB")

	def compress_ramdisk(self):
		ext = self.comp_methods[self.compression]["ext"]
		cmd = self.comp_methods[self.compression]["cmd"]
		self.log.info(f"Compressing initial ramdisk using [turquoise2]{' '.join(cmd)}[default]...")
		out_cpio = f"{self.temp_initramfs}.{ext}"
		with open(out_cpio, "wb") as of:
			with open(self.temp_initramfs, "rb") as f:
				comp_process = subprocess.Popen(
					cmd,
					stdin=f,
					stdout=of,
				)
				comp_process.communicate()
				if comp_process.returncode != 0:
					raise OSError(f"{cmd[0]} returned error code {comp_process.returncode} when compressing {self.temp_initramfs}")
		self.size_final = os.path.getsize(out_cpio)

		return out_cpio

	def copy_modules(self):
		self.log.info("Starting modules processing...")
		os.makedirs(f"{self.initramfs_root}/lib/modules", exist_ok=True)
		self.module_scanner.populate_initramfs(initial_ramdisk=self)

	def copy_binary(self, binary):
		copy_binary(binary, dest_root=self.initramfs_root)

	def create_ramdisk(self, final_cpio):
		self.log.debug(f"Using {self.initramfs_root} to build initramfs")
		self.log.info(f"Creating initramfs...")
		self.create_baselayout()
		self.create_fstab()
		self.setup_linuxrc_and_etc()
		self.setup_busybox()
		success = self.iter_plugins()
		if not success:
			return False
		self.copy_modules()
		# TODO: add firmware?
		# TODO: this needs cleaning up:
		self.create_ramdisk_binary()
		out_cpio = self.compress_ramdisk()
		os.makedirs(os.path.dirname(final_cpio), exist_ok=True)
		shutil.copy(out_cpio, final_cpio)
		self.log.info(f"Orig. Size:  [turquoise2]{self.size_initial / 1000000:6.2f} MiB[default]")
		self.log.info(f"Final Size:  [turquoise2]{self.size_final / 1000000:6.2f} MiB[default]")
		self.log.info(f"Ratio:       [orange1]{(self.size_final / self.size_initial) * 100:.2f}% [turquoise2]({self.size_initial/self.size_final:.2f}x)[default]")
		self.log.done(f"Created:     [orange1]{final_cpio}[default]")
		return True
