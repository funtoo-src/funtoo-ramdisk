#!/usr/bin/python3
import os


class ConfigFstab:
	def __init__(self, root="/"):
		self.root = root
		self.devices = {}
		self.mount_points = {}
		self.path = os.path.join(self.root, "etc/fstab")
		with open(self.path, "r") as fn:
			for line in fn.readlines():
				line = line.strip()
				if line.startswith("#"):
					continue
				comment_pos = line.find("#")
				if comment_pos != -1:
					line = line[0:comment_pos]
				split = line.split()
				if len(split) != 6:
					continue
				self.devices[split[0]] = split
				self.mount_points[split[1]] = split

	def get_line_by_mount(self, mount_point="/"):
		if mount_point not in self.mount_points:
			raise KeyError(f"Mount point {mount_point} not found in {self.path}")
		return self.mount_points["/"]
