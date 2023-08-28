import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class CoreRamDiskPlugin(RamDiskPlugin):
	key = "core"

	@property
	def binaries(self):
		if os.path.exists("/sbin/blkid"):
			yield "/sbin/blkid"
		else:
			raise BinaryNotFoundError("/sbin/blkid", dep="sys-apps/util-linux")


def iter_plugins():
	yield CoreRamDiskPlugin
