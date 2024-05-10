import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class LVMRamDiskPlugin(RamDiskPlugin):
	key = "lvm"
	hooks = ["post_scan"]

	# TODO: add ability to add a list of required modules for any plugin, as well as load info

	@property
	def binaries(self):
		if os.path.exists("/sbin/lvm.static"):
			yield "/sbin/lvm.static", "/sbin/lvm"
		elif os.path.exists("/sbin/lvm"):
			yield "/sbin/lvm"
		else:
			raise BinaryNotFoundError(f"Binary /sbin/lvm or /sbin/lvm.static not found", dep="sys-fs/lvm2")

	@property
	def post_scan_script(self):
		return """
. /etc/initrd.scripts
good_msg "Scanning for volume groups..."
/sbin/lvm vgchange -ay --sysinit 2>&1
if [ $? -ne 0 ]
then
	bad_msg "Scanning for volume groups failed!"
else
	good_msg "Changed and loaded volume groups..."
	settle_root
	good_msg "Determining root volume device..."
	return 0
fi
"""


def iter_plugins():
	yield LVMRamDiskPlugin

# vim: ts=4 sw=4 noet
