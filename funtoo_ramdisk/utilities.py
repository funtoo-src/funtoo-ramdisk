import os
import shutil
import subprocess


def copy_binary(binary, dest_root, out_path=None):
	"""
	Specify an executable, and it gets copied to the initramfs -- along with all dependent
	libraries, if any.

	``dest_tree`` is the destination filesystem tree root, and ``out_path`` can be used to
	specify a different output filename.

	This method uses the ``lddtree`` command from paxutils.
	"""
	if out_path is None:
		out_path_abs = binary
	else:
		out_path_abs = out_path
	status, output = subprocess.getstatusoutput(f"/usr/bin/lddtree -l {binary}")
	if status != 0:
		raise OSError(f"lddtree returned error code {status} when processing {binary}")
	for src_abs in output.split('\n'):
		# lddtree outputs a bunch of things besides our original binary. If we are
		# processing our original binary and have an alternate destination name, use
		# it:
		if src_abs == binary:
			dest_abs = os.path.join(dest_root, out_path_abs.lstrip("/"))
		else:
			dest_abs = os.path.join(dest_root, src_abs.lstrip("/"))
		os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
		shutil.copy(src_abs, dest_abs)


def iter_lines(config_file):
	"""
	Yield individual lines in a configuration file. Use this to pass configs to
	our classes rather than having them actually open the file themselves.
	"""
	with open(config_file, "r") as cf:
		for line in cf.read().split('\n'):
			yield line
