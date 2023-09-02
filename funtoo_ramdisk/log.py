from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.theme import Theme

LOGGER = None


class FakeLogger:
	class MyHighlighter(RegexHighlighter):
		base_style = "ramdisk."
		highlights = [r"(?P<stats>^ ::.*)"]

	def __init__(self, debug=False):
		self.theme = Theme({"ramdisk.stats": "bold magenta"})
		self.console = Console(highlighter=None, theme=self.theme)
		if not self.console.is_interactive:
			self.console = Console(highlighter=None, theme=self.theme, color_system=None)
		self.debug_mode = debug

	def enable_debug(self):
		self.debug_mode = True

	def info(self, msg):
		self.console.print(" [turquoise2]::[default] " + msg)

	def warning(self, msg):
		self.console.print(" [orange1]::[default] " + msg)

	def error(self, msg):
		self.console.print(" [bright_white on dark_red]:collision::collision:[default] " + msg + " ")

	def done(self, msg):
		self.console.print(" [light_salmon1]:sparkle::sparkle:[default] " + msg)

	def debug(self, msg):
		if not self.debug_mode:
			return
		self.console.log(msg)

	def print_exception(self, show_locals=False):
		self.console.print_exception(show_locals=show_locals)


if LOGGER is None:
	LOGGER = FakeLogger()


def get_logger():
	global LOGGER
	return LOGGER