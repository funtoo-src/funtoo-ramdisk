import os


class RamDiskPlugin:

	key = "generic"
	binaries = {}

	def __init__(self, ramdisk):
		self.ramdisk = ramdisk

	def run(self):
		for pkg, binary_list in self.binaries.items():
			for binary in binary_list:
				if not os.path.exists(binary):
					self.ramdisk.log.error(f"Required binary [turquoise2]{binary}[default] for plugin [orange1]{self.key}[default] does not exist. Please emerge {pkg} to fix this.")
					return False
				else:
					self.ramdisk.log.info(f"Copying [turquoise2]{binary}[default] to initramfs...")
					self.ramdisk.copy_binary(binary)
		return True
