import os


class BinaryNotFoundError(Exception):

	def __init__(self, binary, dep=None):
		self.binary = binary
		self.dep = dep


class RamDiskPlugin:

	key = "generic"

	@property
	def binaries(self):
		yield

	def __init__(self, ramdisk):
		self.ramdisk = ramdisk

	@property
	def activation_script(self):
		return None

	def run(self):
		for binary in self.binaries:
			try:
				if isinstance(binary, tuple):
					final_name = binary[1]
					binary = binary[0]
				else:
					final_name = binary
				if binary == final_name:
					self.ramdisk.log.info(f"Copying [turquoise2]{binary}[default] to initramfs...")
				else:
					self.ramdisk.log.info(f"Copying [turquoise2]{binary}[default] to initramfs as [turquoise2]{final_name}[default]...")
				self.ramdisk.copy_binary(binary, out_path=final_name)
			except BinaryNotFoundError as bne:
				self.ramdisk.log.error(f"Required binary [turquoise2]{bne.binary}[default] for plugin [orange1]{self.key}[default] does not exist. Please emerge {bne.dep} to fix this.")
				return False
		script = self.activation_script
		if script is not None:
			self.ramdisk.install_activation_script(self.key, script)
		return True
