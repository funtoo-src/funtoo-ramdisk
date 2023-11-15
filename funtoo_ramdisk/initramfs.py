#!/usr/bin/python3
import importlib
import os
import pkgutil
import shutil
import site
import subprocess
import tempfile

from funtoo_ramdisk.config_files import fstab_sanity_check
from funtoo_ramdisk.log import get_logger
from funtoo_ramdisk.modules import ModuleScanner
from funtoo_ramdisk.utilities import copy_binary, iter_lines
from funtoo_ramdisk.kernel import get_kernel_version_from_symlink, get_current_kernel_version, get_link_target


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

	def __init__(self, args, support_root, pypath=None):
		self.log = get_logger()
		self.args = args

		if pypath is not None:
			self.plugins_search_paths = [os.path.join(pypath, "plugins")]
		else:
			# Did you know that Python can have multiple site-packages directories? This is a list:
			self.plugins_search_paths = map(lambda x: os.path.join(x, "funtoo_ramdisk/plugins"), site.getsitepackages())

		self.plugins = {}

		if not self.plugins_search_paths:
			raise FileNotFoundError("Unable to find plugins directory -- aborting.")

		for plugin in pkgutil.iter_modules(self.plugins_search_paths, "funtoo_ramdisk.plugins."):
			mod = importlib.import_module(plugin.name)
			iter_plugins = getattr(mod, "iter_plugins", None)
			if not iter_plugins:
				self.log.warning(f"Plugin {plugin.name} is missing an iter_plugins function; skipping.")
			else:
				for plugin_obj in iter_plugins():
					plugin_obj_inst = plugin_obj(self)
					self.plugins[plugin_obj.key] = plugin_obj_inst

		# Initramfs-creation-related variables:

		self.temp_root = None
		self.initramfs_root = None
		self.kpop = self.args.values.kpop
		self.support_root = support_root
		self.compression = self.args.values.compression
		self.module_scanner = None
		self.size_initial = None
		self.size_final = None
		self.size_compressed = None
		# When creating initramfs, enable correct plugins:
		self.enabled_plugins = {"core"}
		if self.args.values.plugins:
			enabled_plugins = self.args.values.plugins.split(",")
			self.enabled_plugins |= set(enabled_plugins)
		self.kernel_version = None
		self.current_version = None

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
			src = os.path.join(self.support_root, "etc", file)
			if os.path.isfile(src):
				shutil.copy(src, os.path.join(self.initramfs_root, "etc"))
		for x in ["init", "etc/initrd.scripts", "etc/initrd.defaults"]:
			os.chmod(os.path.join(self.initramfs_root, x), 0o755)
		os.makedirs(os.path.join(self.initramfs_root, "etc/plugins/scan_mode"), exist_ok=True)
		for file in os.listdir(os.path.join(self.support_root, "etc/plugins/scan_mode")):
			shutil.copy(os.path.join(self.support_root, "etc/plugins/scan_mode", file), os.path.join(self.initramfs_root, "etc/plugins/scan_mode"))

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
		ext = self.args.comp_methods[self.compression]["ext"]
		cmd = self.args.comp_methods[self.compression]["cmd"]
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

	def copy_binary(self, binary, out_path=None):
		copy_binary(binary, dest_root=self.initramfs_root, out_path=out_path)

	def install_activation_script(self, name, contents):
		plugins_dir = os.path.join(self.initramfs_root, "etc/plugins")
		os.makedirs(plugins_dir, exist_ok=True)
		script_fn = os.path.join(plugins_dir, f"{name}.sh")
		with open(script_fn, "w") as script_file:
			script_file.write(contents)
		os.chmod(script_fn, 0o775)

	def display_enabled_plugins(self):
		if self.plugins:
			out_list = []
			for plugin in sorted(self.plugins.keys()):
				if plugin in self.enabled_plugins:
					out_list.append(f"[orange1]{plugin}[default]")
				else:
					out_list.append(f"[turquoise2]{plugin}[default]")
			self.log.info(f"Registered plugins: {'/'.join(out_list)}")

	def init_module_scanner(self):
		if self.args.values.kmod_config == "kpop":
			if not self.kpop:
				raise ValueError("The kpop option requires a list of modules specified to include.")
			copy_lines = autoload_lines = iter([
				"[kpop]",
			] + self.kpop)
		else:
			copy_lines = iter_lines(os.path.join(self.support_root, "module_configs", self.args.values.kmod_config, "modules.copy"))
			autoload_lines = iter_lines(os.path.join(self.support_root, "module_configs", self.args.values.kmod_config, "modules.autoload"))
		self.module_scanner = ModuleScanner(
			self.args.values.kmod_config,
			kernel_version=self.kernel_version,
			root=self.args.values.fs_root,
			logger=self.log,
			copy_lines=copy_lines,
			autoload_lines=autoload_lines
		)

	def get_lib_modules(self) -> dict:
		out = {}
		module_path = os.path.join(self.args.values.fs_root, "lib/modules")
		for kv in os.listdir(module_path):
			link_dest = None
			full_path = os.path.join(module_path, kv)
			if not os.path.isdir(full_path):
				continue
			symlink = os.path.join(module_path, kv, "source")
			if os.path.islink(symlink):
				link_dest = get_link_target(symlink)
			out[kv] = link_dest
		return out

	@property
	def valid_kernel_versions(self):
		return set(self.get_lib_modules().keys())

	def find_kernel(self):
		if self.args.values.kernel is None:
			link = os.path.join(self.args.values.fs_root, "usr/src/linux")
			if not os.path.islink(link):
				self.log.error(f"Default linux symlink at {link} not found -- please specify a kernel. Type 'ramdisk list kernels' for a list.")
			else:
				self.kernel_version = get_kernel_version_from_symlink(link)
		else:
			if self.args.values.kernel not in self.valid_kernel_versions:
				self.log.error(f"Specified kernel version '{self.args.values.kernel}' not found. Type 'ramdisk list kernels' to see list of all kernels.")
			else:
				self.kernel_version = self.args.values.kernel
		if not self.kernel_version:
			raise ValueError("Kernel not found")
		self.current_version = get_current_kernel_version()
		if self.kernel_version == self.current_version:
			self.log.info(f"Building initramfs for: [orange1]{self.kernel_version}[default] (currently-active kernel)")
		else:
			self.log.info(f"Building for: [orange1]{self.kernel_version}[default] ([turquoise2]{self.current_version}[default] active)")

	def print_banner(self):
		self.log.debug(f"[turquoise2]funtoo-ramdisk [orange1]{self.args.version}[default] [grey63]:wolf:[default]")
		if self.args.from_git:
			self.log.debug(f"Running from git repository [turquoise2]{os.path.dirname(self.args.git_path)}[default]")

	def create_ramdisk(self):
		self.find_kernel()
		self.print_banner()
		self.display_enabled_plugins()
		self.init_module_scanner()
		with tempfile.TemporaryDirectory(prefix="ramdisk-", dir=self.args.values.temp_root) as self.temp_root:
			self.initramfs_root = os.path.join(self.temp_root, "initramfs")
			os.makedirs(self.initramfs_root)
			final_cpio = os.path.abspath(self.args.values.destination)
			if os.path.exists(final_cpio) and not self.args.values.force:
				raise FileExistsError("Specified destination initramfs already exists -- use --force to overwrite.")
			fstab_sanity_check()
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

	def list_plugins(self):
		for plugin in self.plugins:
			print(plugin)

	def list_kernels(self):
		link = os.path.join(self.args.values.fs_root, "usr/src/linux")
		if os.path.islink(link):
			link_kv = get_kernel_version_from_symlink(link)
		else:
			link_kv = None
		kv_dict = self.get_lib_modules()
		if link_kv is not None and link_kv in kv_dict:
			print(f"{link_kv} ({link})")
			del kv_dict[link_kv]
		for kv, link_target in kv_dict.items():
			if link_target:
				print(f"{kv} ({link_target})")
			else:
				print(kv)

	def run(self):
		if self.args.action == "build":
			return self.create_ramdisk()
		elif self.args.action == "list":
			if self.args.values.target == "plugins":
				self.list_plugins()
			elif self.args.values.target == "kernels":
				self.list_kernels()
			return True