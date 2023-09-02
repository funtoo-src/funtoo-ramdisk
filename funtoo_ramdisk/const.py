ACTIONS = {
	"build": None,
	"kernel": ["list"],
	"plugins": ["list"]
}

ACTION_KEYS = set(sorted(ACTIONS.keys()))

OPTIONAL_ARGS = {
	"--debug": False,
	"--backtrace": False,
	"--force": False,
	"--help": False,
}

BUILD_SETTINGS = {
	"--kernel": None,
	"--compression": "xz",
	"--fs_root": "/",
	"--temp_root": "/var/tmp",
	"--enable": "",
	"--modconfig": "full",
	"--kpop": None,
}

# 	"version": {"action": "version", "version": f"funtoo-ramdisk {__version__}"},
BUILD_CLI_ARGS ={
	"destination": {"default": None, "action": "store", "positional": True, "help": "The output initramfs filename to create."},
}
