#!/usr/bin/python3
import os
import re
import subprocess

from funtoo_ramdisk.log import get_logger
log = get_logger()


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


def fstab_sanity_check():
	fstab = ConfigFstab()
	try:
		root_entry = fstab.get_line_by_mount("/")
	except KeyError:
		log.warning("Cannot find '/' mount point in /etc/fstab -- assuming not-yet-configured system or metro build.")
		return
	if re.match("^/dev/sd.*", root_entry[0]):
		cmd = f"/sbin/blkid -s UUID -o value {root_entry[0]}"
		status, uuid = subprocess.getstatusoutput(cmd)
		if status != 0:
			raise ValueError(f"command: '{cmd}' failed with exit code {status}.")
		uuid = uuid.strip()
		if not uuid:
			raise ValueError(f"command: '{cmd}' was unable to give us a UUID.")
		log.warning(f"""Detected root device {root_entry[0]}, which could be a problem if you have more
	than one ATA/SCSI disk. Since /dev/sd* device nodes are not consistently 
	assigned, the initramfs could see this as a different device. Please do the the
	following:

	1. In /etc/fstab, change your root entry from:

	   {'    '.join(root_entry)} 

	   to:

	   UUID={uuid}    {'    '.join(root_entry[1:])}

	2. *Re-run* ego boot update so that GRUB will look for your root block device
	    by UUID.

	3. This problem should now be resolved, since now you are referring to the root
	   block device using a UUID which will not change. Now, go ahead and try to
	   create your ramdisk again.
		""")
