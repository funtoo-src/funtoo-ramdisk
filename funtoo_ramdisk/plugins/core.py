import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class CoreRamDiskPlugin(RamDiskPlugin):
	key = "core"

	@property
	def binaries(self):
		for bin in ["/sbin/blkid", "/bin/lsblk"]:
			if os.path.exists(bin):
				yield bin
			else:
				raise BinaryNotFoundError(bin, dep="sys-apps/util-linux")


def iter_plugins():
	yield CoreRamDiskPlugin
