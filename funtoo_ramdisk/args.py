import sys


class OptionalArgs:

	default = None

	def __init__(self, default_dict=None, default=False):
		self.default = default
		self.changed_keys = set()
		if default_dict:
			self.set_defaults(default_dict)

	def set_defaults(self, default_dict):
		# If we have a dictionary, treat it as a bunch of default values for a bunch of settings:
		for key, val in default_dict.items():
			setattr(self, key.lstrip('-'), val)

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

	def __init__(self, find_opt_args=None, find_opt_settings=None, defined_actions=None, default_action=None):
		self.defined_actions = defined_actions
		self.default_action = default_action
		self.find_opt_args = find_opt_args
		self.find_opt_settings = find_opt_settings
		if self.find_opt_args:
			self.opt_args = OptionalArgs(default=False, default_dict=find_opt_args)
		else:
			self.opt_args = OptionalArgs()
		self.unparsed_args = sys.argv[1:]
		self.action = None

	def parse_opt_args(self):
		"""
		This is a key part of our custom argument parser.

		Given input arguments sourced from ``self.unparsed_args``, scan these arguments for any optional arguments
		specified in ``self.find_opt_args``, which is a dictionary of key/value pairs of
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
			if arg in self.find_opt_args.keys():
				self.opt_args.set_value(arg.lstrip("-"), True)
			else:
				still_unparsed.append(arg)
			pos += 1
		self.unparsed_args = still_unparsed

	def parse_opt_settings(self):
		"""
		This function is very similar to ``find_opt_args``, above, but we are looking for
		optional settings in the form of ``--foo=bar`` or ``--foo bar``.
		"""
		pos = 0
		still_unparsed = []
		self.opt_args.set_defaults(self.find_opt_settings)
		while pos < len(self.unparsed_args):
			arg = self.unparsed_args[pos]
			eq_pos = arg.find("=")
			if eq_pos == -1:
				# next argument is the value
				pos += 1
				if arg not in self.find_opt_settings:
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
			if arg_key in self.find_opt_settings:
				self.opt_args.set_value(arg_key.lstrip('-'), arg_val)
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
			if self.default_action:
				self.action = self.default_action
			else:
				raise ArgParseError(f"No action specified. Specify one of: {' '.join(sorted(self.defined_actions))}")


