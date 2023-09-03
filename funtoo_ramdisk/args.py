import sys

from funtoo_ramdisk.log import get_logger
log = get_logger()


class ArgumentValues:

	default = None

	def __init__(self, default_dict=None, default=None):
		self.default = default
		self.changed_keys = set()
		if default_dict:
			self.set_defaults(default_dict)

	def set_defaults(self, default_dict):
		# If we have a dictionary, treat it as a bunch of default values for a bunch of settings:
		for key, val in default_dict.items():
			key = key.lstrip('-')
			log.debug(f"Setting default value {key} to {val}")
			setattr(self, key, val)

	def set_value(self, key, value):
		"""
		Use this method to set any value!!!

		You can specify key as "--foobar" or "foobar".
		"""
		self.changed_keys.add(key)
		setattr(self, key.lstrip('-'), value)

	def __getattr__(self, item):
		return self.default

	def __repr__(self):
		return f"<OptionalArgs: keys: {sorted(list(self.changed_keys))}>"


class ArgParseError(Exception):
	pass


class Arguments:

	default_action = None
	defined_actions = {}

	global_options = {}
	action_options = {}

	global_settings = {}
	action_settings = {}

	final_positionals = {}

	def __init__(self, app=None, version=None):
		self.app = app
		self.version = version
		self.values = ArgumentValues(default=None)
		self.unparsed_args = sys.argv[1:]
		self.action = None
		if 'help' not in self.defined_actions:
			self.defined_actions['help'] = None

	def __repr__(self):
		return f"<{self.__class__.__name__}: action: {self.action} keys: {sorted(list(self.values.changed_keys))}>"

	def parse_options(self, options):
		"""
		This is a key part of our custom argument parser.

		Given input arguments sourced from ``self.unparsed_args``, scan these arguments for any optional arguments
		specified in ``self.defined_options``, which is a dictionary of key/value pairs of
		options. Keys are literal "--foobar" values, and values in the dict can be used to set default values.

		Results are stored in ``self.opt_args`` with the found optional values set to ``True``. Any not-specified
		argument will have a ``False`` default value.

		This function returns sets ``self.unparsed_args`` to the remaining unparsed arguments.
		"""
		pos = 0
		still_unparsed = []
		# parse main arguments -- optional and leftover actions:
		while pos < len(self.unparsed_args):
			arg = self.unparsed_args[pos]
			if arg in options.keys():
				self.values.set_value(arg.lstrip("-"), True)
			else:
				still_unparsed.append(arg)
			pos += 1
		self.unparsed_args = still_unparsed

	def parse_settings(self, settings):
		"""
		This function is very similar to ``find_opt_args``, above, but we are looking for
		optional settings in the form of ``--foo=bar`` or ``--foo bar``.
		"""
		pos = 0
		still_unparsed = []
		self.values.set_defaults(settings)
		while pos < len(self.unparsed_args):
			arg = self.unparsed_args[pos]
			eq_pos = arg.find("=")
			if eq_pos == -1:
				# next argument is the value
				pos += 1
				if arg not in settings:
					still_unparsed.append(arg)
					continue
				if pos >= len(self.unparsed_args):
					raise ArgParseError(f"Command-line setting '{arg}' requires a value, set with either '{arg}=val' or '{arg} val'")
				arg_key = arg
				arg_val = self.unparsed_args[pos]
			else:
				# include --foo=bar value:
				arg_key = arg[:eq_pos]
				arg_val = arg[eq_pos + 1:]
			if arg_key in settings:
				self.values.set_value(arg_key.lstrip('-'), arg_val)
			else:
				still_unparsed.append(arg)
			pos += 1
		self.unparsed_args = still_unparsed

	def parse_action(self):
		"""
		Given a set of possible valid actions inside ``actions``, and a possible
		default action specified in ``default_action``, parse all input arguments, and return the detected action,
		plus any unparsed/unrecognized arguments.

		``ArgParseError`` will be thrown if:

		1. More than one valid action specified.
		2. No action specified, and no default action.
		"""
		still_unparsed = []
		for arg in self.unparsed_args:
			if arg in self.defined_actions:
				if self.action:
					raise ArgParseError(f"Duplicate action '{arg}' -- '{self.action}' already specified.")
				else:
					self.action = arg
			else:
				# This could be sub-options for a specific action:
				still_unparsed.append(arg)
		if self.action is None:
			if self.values.help:
				self.action = "help"
			elif self.values.version:
				self.action = "version"
			elif self.default_action:
				self.action = self.default_action
			else:
				raise ArgParseError(f"No action specified. Specify one of: {' '.join(sorted(self.defined_actions))}")
		self.unparsed_args = still_unparsed

	def parse_positionals(self):
		if self.action in self.final_positionals:
			fin_pos = self.final_positionals[self.action]
			if len(self.unparsed_args) < len(fin_pos):
				missing = len(fin_pos) - len(self.unparsed_args)
				out = "Expecting additional argument"
				if missing == 1:
					out += ": "
				else:
					out += "s: "
				out += ' '.join(fin_pos[-missing:])
				raise ArgParseError(out)
			elif len(self.unparsed_args) > len(fin_pos):
				extra = len(self.unparsed_args) - len(fin_pos)
				out = "Unexpected additional argument"
				if extra == 1:
					out += ": "
				else:
					out += "s: "
				out += ' '.join(self.unparsed_args[-extra:])
				raise ArgParseError(out)
			else:
				for pos_arg in fin_pos:
					self.values.set_value(pos_arg, self.unparsed_args[0])
					self.unparsed_args.pop(0)

	def do_help(self):
		print("HELP!")
		sys.exit(1)

	def do_version(self):
		if self.app:
			app = self.app
		else:
			app = sys.argv[0]
		sys.stdout.write(f"{app} {self.version}\n")
		sys.exit(1)

	def parse(self):
		if self.global_options:
			self.parse_options(self.global_options)
		if self.global_settings:
			self.parse_settings(self.global_settings)
		if self.defined_actions:
			self.parse_action()
		if self.action in self.action_options:
			self.parse_options(self.action_options[self.action])
		if self.action in self.action_settings:
			self.parse_settings(self.action_settings[self.action])
		self.parse_positionals()
		if self.action == "help":
			self.do_help()
		elif self.action == "version":
			self.do_version()

