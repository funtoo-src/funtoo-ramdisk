import os
import subprocess

from funtoo_ramdisk.log import get_logger
log = get_logger()


def get_kernel_version_from_symlink(kernel_link):
	"""
	Provide a symlink, which could be either ``/usr/src/linux`` or ``/lib/modules/<kv>/sources``, and this will extract
	the version info from the Makefile, and return it as a single formatted string containing the full kernel
	version.

	Typically, modules for this kernel can be found at ``/lib/modules/<kernel version>``.
	"""
	link_target = os.readlink(kernel_link)
	link_target = os.path.join(os.path.dirname(kernel_link), link_target)
	if not os.path.exists(link_target):
		raise FileNotFoundError(f"Could not find kernel from symlink {kernel_link} -- looking for {link_target} symlink target.")
	# grab data from Makefile, so we can determine correct kernel name for finding modules:
	datums = ["VERSION", "PATCHLEVEL", "SUBLEVEL", "EXTRAVERSION"]
	got_datums = {}
	with open(os.path.join(link_target, "Makefile"), "r") as mkf:
		while len(got_datums.keys()) != 4:
			line = mkf.readline()
			if not line:
				break
			for datum in datums:
				if datum not in got_datums:
					if line.startswith(f"{datum} ="):
						got_datums[datum] = line.split("=")[1].strip()
	if len(got_datums.keys()) != 4:
		raise ValueError(f"Could not extract: {datums} from {kernel_link}/Makefile.")
	return "{VERSION}.{PATCHLEVEL}.{SUBLEVEL}{EXTRAVERSION}".format(**got_datums)


def get_modpath_and_kv_from_linux_symlink():
	kernel_link = os.path.join(args.fs_root, "usr/src/linux")
	log.info(f"No kernel specified, so going to try to use [turquoise2]{kernel_link}[default] symlink.")
	if not os.path.islink(kernel_link):
		raise FileNotFoundError(f"{kernel_link} does not exist or is not a symlink.")

	kernel_version = get_kernel_version_from_symlink(kernel_link)

	module_path = os.path.join(args.fs_root, f"lib/modules/{kernel_version}")
	if not os.path.exists(module_path):
		raise FileNotFoundError(f"Expected kernel module path {module_path} not found.")
	return module_path, kernel_version


def get_current_kernel_version():
	status, current_version = subprocess.getstatusoutput("uname -r")
	return current_version.strip()
