from funtoo_ramdisk.plugin_base import RamDiskPlugin


class LVMRamDiskPlugin(RamDiskPlugin):
	key = "lvm"

	binaries = {
		"sys-fs/lvm2": [
			"/sbin/lvm"
		]
	}


def iter_plugins():
	yield LVMRamDiskPlugin
