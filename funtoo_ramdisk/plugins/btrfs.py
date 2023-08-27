from funtoo_ramdisk.plugin_base import RamDiskPlugin


class BtrfsRamDiskPlugin(RamDiskPlugin):
	key = "btrfs"

	binaries = {
		"sys-fs/btrfs-progs": [
			"/sbin/btrfs"
		]
	}


def iter_plugins():
	yield BtrfsRamDiskPlugin
