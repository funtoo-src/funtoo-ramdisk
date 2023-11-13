import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class LVMRamDiskPlugin(RamDiskPlugin):
	key = "lvm"

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
	def activation_script(self):
		return """
good_msg "Scanning for volume groups..."
/bin/lvm vgchange -ay --sysinit 2>&1
if [ $? -ne 0 ]
then
	bad_msg "Scanning for volume groups failed!"
else
	udev_settle
fi
"""


def iter_plugins():
	yield LVMRamDiskPlugin
