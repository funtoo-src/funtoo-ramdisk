import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class BtrfsRamDiskPlugin(RamDiskPlugin):
	key = "btrfs"

	@property
	def binaries(self):
		if os.path.exists("/sbin/btrfs"):
			yield "/sbin/btrfs"
		else:
			raise BinaryNotFoundError("/sbin/btrfs", dep="sys-fs/btrfs-progs")


def iter_plugins():
	yield BtrfsRamDiskPlugin
