import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class BtrfsRamDiskPlugin(RamDiskPlugin):
	key = "btrfs"
	hooks = ["post_scan"]

	@property
	def binaries(self):
		if os.path.exists("/sbin/btrfs.static"):
			yield "/sbin/btrfs.static", "/sbin/btrfs"
		elif os.path.exists("/sbin/btrfs"):
			yield "/sbin/btrfs"
		else:
			raise BinaryNotFoundError("Binary /sbin/btrfs.static or /sbin/btrfs not found", dep="sys-fs/btrfs-progs")

	@property
	def post_scan_script(self):
	        return """
. /etc/initrd.scripts
good_msg "Scanning for btrfs volumes and subvolumes..."
/sbin/btrfs -q device scan
if [ $? -ne 0 ]
then
	bad_msg "Scanning for btrfs volumes failed!"
else
	good_msg "Loaded btrfs volumes..."
	good_msg "Determining root volume device..."
	return 0
fi
"""

def iter_plugins():
	yield BtrfsRamDiskPlugin

# vim: ts=4 sw=4 noet
