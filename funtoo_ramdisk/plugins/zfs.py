import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class ZfsRamDiskPlugin(RamDiskPlugin):
	key = "zfs"
	hooks = ["post_scan"]

	@property
	def binaries(self):
		if os.path.exists("/sbin/mount.zfs"):
			yield "/sbin/mount.zfs"
		else:
			raise BinaryNotFoundError("/sbin/mount.zfs", dep="sys-fs/zfs")

		if os.path.exists("/sbin/zdb"):
			yield "/sbin/zdb"
		else:
			raise BinaryNotFoundError("/sbin/zdb", dep="sys-fs/zfs")

		if os.path.exists("/sbin/zfs"):
			yield "/sbin/zfs"
		else:
			raise BinaryNotFoundError("/sbin/zfs", dep="sys-fs/zfs")

		if os.path.exists("/sbin/zpool"):
			yield "/sbin/zpool"
		else:
			raise BinaryNotFoundError("/sbin/zpool", dep="sys-fs/zfs")

	@property
	def post_scan_script(self):
		return """
. /etc/initrd.scripts
good_msg "Attempting to import ZFS pool ..."
if [ ! -z $(/sbin/zpool import -N -a && /sbin/zpool list -H -o bootfs) ]; then
	good_msg "At least one ZFS pool with bootfs flag was found!"
fi
"""


def iter_plugins():
	yield ZfsRamDiskPlugin
