from funtoo_ramdisk.plugin_base import RamDiskPlugin


class CoreRamDiskPlugin(RamDiskPlugin):
	key = "core"

	binaries = {
		"sys-apps/util-linux": [
			"/sbin/blkid"
		]
	}


def iter_plugins():
	yield CoreRamDiskPlugin
