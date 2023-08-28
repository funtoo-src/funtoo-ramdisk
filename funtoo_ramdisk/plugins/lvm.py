import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class LVMRamDiskPlugin(RamDiskPlugin):
	key = "lvm"

	@property
	def binaries(self):
		if os.path.exists("/sbin/lvm.static"):
			yield "/sbin/lvm.static", "/sbin/lvm"
		elif os.path.exists("/sbin/lvm"):
			yield "/sbin/lvm"
		else:
			raise BinaryNotFoundError(f"Binary /sbin/lvm or /sbin/lvm.static not found", dep="sys-fs/lvm2")


def iter_plugins():
	yield LVMRamDiskPlugin
