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


def parse_opt_args(argv, find_opt_args, existing_opt_args=None):
	"""
	This is a key part of our custom argument parser. Given input arguments ``argv``, scan these arguments
	for any optional arguments specified in ``find_opt_args``, which is a dictionary of key/value pairs of
	options. Keys are literal "--foobar" values, and values in the dict can be used to set default values.

	An ``OptionalArgs`` object is returned with the found optional values set to ``True``. You can also
	pass in an ``existing_opt_args`` object if you want to collect all your optional toggles in a single
	object. Any not-specified argument will have a ``False`` default value.

	This function returns the optional arguments object, as well as any extra, unparsed arguments, which
	could require further parsing, or potentially be invalid, unrecognized arguments.
	"""
	pos = 0
	# parse main arguments -- optional and leftover actions:
	if existing_opt_args:
		opt_args = existing_opt_args
		opt_args.set_defaults(find_opt_args)
	else:
		opt_args = OptionalArgs(default=False, default_dict=find_opt_args)
	extra_args = []
	while pos < len(argv):
		arg = argv[pos]
		if arg in find_opt_args.keys():
			opt_args.set_value(arg.lstrip("-"), True)
		else:
			extra_args.append(arg)
		pos += 1
	return opt_args, extra_args


def parse_opt_settings(argv, find_opt_settings, existing_opt_args=None):
	"""
	This function is very similar to ``find_opt_args``, above, but we assume that if any of these
	optional settings are specified, they also come along with a value, either in the form of
	``--foo=bar`` or ``--foo bar``. The command-line-supplied value is stored as a string in an
	optional arguments object, which is returned with any unparsed/unrecognized arguments.
	"""
	pos = 0
	# parse main arguments -- optional and leftover actions:
	if existing_opt_args:
		opt_args = existing_opt_args
		opt_args.set_defaults(find_opt_settings)
	else:
		opt_args = OptionalArgs(default=False, default_dict=find_opt_settings)
	extra_args = []
	while pos < len(argv):
		arg = argv[pos]
		eq_pos = arg.find("=")
		if eq_pos == -1:
			# next argument is the value
			pos += 1
			if arg not in find_opt_settings:
				extra_args.append(arg)
				continue
			if pos >= len(argv):
				raise ArgParseError(f"Command-line setting '{arg}' requires a value, set with either '{arg}=val' or '{arg} val'")
			arg_key = arg
			arg_val = argv[pos]
		else:
			# include --foo=bar value:
			arg_key = arg[:eq_pos]
			arg_val = arg[eq_pos+1:]
		if arg_key in find_opt_settings:
			opt_args.set_value(arg_key.lstrip('-'), arg_val)
		else:
			extra_args.append(arg)
		pos += 1
	return opt_args, extra_args


def parse_action(argv, actions, default_action=None):
	"""
	Given input arguments ``argv``, and a set of possible valid actions inside ``actions``, and a possible
	default action specified in ``default_action``, parse all input arguments, and return the detected action,
	plus any unparsed/unrecognized arguments.

	``ArgParseError`` will be thrown if:

	1. More than one valid action specified.
	2. No action specified, and no default action.
	"""
	action = None
	extra_args = []
	for arg in argv:
		if arg in actions:
			if action:
				raise ArgParseError(f"Duplicate action '{arg}' -- '{action}' already specified.")
			else:
				action = arg
		else:
			# This could be sub-options for a specific action:
			extra_args.append(arg)
	if action is None:
		if default_action:
			action = default_action
		else:
			raise ArgParseError(f"No action specified. Specify one of: {' '.join(sorted(actions))}")
	return action, extra_args
