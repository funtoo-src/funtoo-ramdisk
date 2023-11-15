import sys

from funtoo_ramdisk.args import Arguments, ArgParseError
from funtoo_ramdisk.log import get_logger
log = get_logger()


class RamDiskArguments(Arguments):

	default_action = "build"

	# TODO: implement sub-actions:
	defined_actions = {
		"build": None,
		"list": None,
	}

	global_options = {
		"--debug": False,
		"--backtrace": False,
		"--force": False,
		"--help": False,
		"--version": False
	}

	global_settings = {
		"--fs_root": "/",
	}

	action_settings = {
		"build": {
			"--kernel": None,
			"--compression": "xz",
			"--temp_root": "/var/tmp",
			"--plugins": "",
			"--kmod_config": "full",
			"--kpop": None,
		}
	}

	final_positionals = {
		"build": ["destination"],
		"list": ["target"]
	}

	comp_methods = {
		"xz": {
			"ext": "xz",
			"cmd": ["xz", "-e", "-T 0", "--check=none", "-z", "-f", "-5", "-c"]
		},
		"zstd": {
			"ext": "zst",
			"cmd": ["zstd", "-f", "-10", "-c"]
		}
	}

	list_targets = ["plugins", "kernels"]

	def __init__(self, app=None, version=None, from_git=False, git_path=None):
		super().__init__(app=app, version=version)
		self.from_git = from_git
		self.git_path = git_path

	def parse(self):
		super().parse()
		if self.values.debug:
			log.info("DEBUG enabled.")
			log.enable_debug()
		if self.values.backtrace:
			from rich.traceback import install
			install(show_locals=True)
		if self.action == "build":
			# Convert kpop to list:
			if self.values.kpop is not None:
				self.values.set_value("kpop", self.values.kpop.split(','))
				# --kpop implies "--kmod_config=kpop"
				self.values.kmod_config = "kpop"
			if self.values.compression not in self.comp_methods.keys():
				raise ArgParseError(f"Specified compression method must be one of: {' '.join(sorted(list(self.comp_methods.keys())))}.")
		elif self.action == "list":
			if self.values.target not in self.list_targets:
				raise ArgParseError(f"list target must be one of: {' '.join(self.list_targets)}")
