import os

from funtoo_ramdisk.plugin_base import RamDiskPlugin, BinaryNotFoundError


class LUKSRamDiskPlugin(RamDiskPlugin):
	'''
	https://gitlab.com/cryptsetup/cryptsetup/blob/master/README.md
	Plugin to decrypt cryptsetup encrypted LUKS root volumes
	'''
	key = "luks"
	hooks = ["post_scan"]

	# TODO: add ability to add a list of required modules for any plugin, as well as load info

	@property
	def binaries(self):
		if os.path.exists("/sbin/cryptsetup"):
			yield "/sbin/cryptsetup"
		else:
			raise BinaryNotFoundError(f"Binary /sbin/cryptsetup not found", dep="sys-fs/cryptsetup")

	@property
	def post_scan_script(self):
		return """
. /etc/initrd.scripts
good_msg "Attempting to open cryptsetup LUKS encrypted root volume..."
open_crypt
"""


def iter_plugins():
	yield LUKSRamDiskPlugin

# vim: ts=4 sw=4 noet
