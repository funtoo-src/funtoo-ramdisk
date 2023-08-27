import os
import shutil
import subprocess


def copy_binary(binary, dest_root):
	"""
	Specify an executable, and it gets copied to the initramfs -- along with all dependent
	libraries, if any.

	This method uses the ``lddtree`` command from paxutils.
	"""
	status, output = subprocess.getstatusoutput(f"/usr/bin/lddtree -l {binary}")
	if status != 0:
		raise OSError(f"lddtree returned error code {status} when processing {binary}")
	for src_abs in output.split('\n'):
		dest_abs = os.path.join(dest_root, src_abs.lstrip("/"))
		os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
		shutil.copy(src_abs, dest_abs)
