**************
Funtoo Ramdisk
**************

Copyright 2023 Daniel Robbins, Funtoo Solutions, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Introduction
============

The Funtoo ramdisk tool, called ``ramdisk`` is a stand-alone tool to create an
initial RAM disk filesystem (initramfs) for booting your Linux system.

The internal initramfs logic is based on the logic found in Gentoo Linux's
genkernel tool, but has been rewritten to be simpler and more efficient.

You can use this tool to create an initramfs to boot to a Funtoo Linux root
ext4 or XFS filesystem, which is what we support in our official installation
documentation at https://www.funtoo.org/Install -- but that's about it.

What's Not Included
===================

Nearly all "extra" genkernel features are intentionally not yet implemented.
This tool doesn't build your kernel or modules.

It also currently doesn't support dmraid, zfs, btrfs, encrypted root, or LiveCD
or LiveUSB booting.

Why not? Because one of the main design goals of this project is to create a
very elegant and easy-to-understand initramfs whose core logic is not cluttered
with tons of complicated features. To start from a clean slate, we are starting
from very minimal functionality and then will very carefully add back various
features while keeping the code clean, simple, elegant and effective.

What's Included
===============

So, what *does* Funtoo's ramdisk tool actually offer? Here's a list:

* genkernel-style initramfs without the cruft. In comparison to genkernel's
  initramfs, the shell code is about 10x simpler and a lot cleaner and has
  been modernized. About 100 lines of shell script, with another 215 lines
  of functions in a support file.

* Copies over the modules you specify -- and automatically figures out any
  kernel module dependencies, so any depended-upon modules are also copied.
  This eliminates the need to track these dependencies manually.

* Rootless operation. You do not need enhanced privileges to create the
  initramfs.

* You can read the ``linuxrc`` script and actually understand what it does.
  It is written to be easy to understand and adapt. So it's not just short,
  but easy to grasp.

* Enhanced module loading engine on the initramfs which is significantly
  faster than genkernel. This effectively eliminates the "watching the
  stream of useless modules being loaded" issue with genkernel. Modern
  systems with NVMe drives will load just a handful of modules to boot
  -- all without requiring any special action from the user.

* "kpop" functionality allows for building ramdisks with just the modules
  you need. For example, ``ramdisk --kpop=nvme,ext4`` will create a
  ramdisk that can boot on NVMe ext4 root filesystems, and only include
  these necessary modules, leaving all other modules to be loaded by
  your Funtoo Linux system.

* Effective Python-based command to actually build the ramdisk, which is
  called: ``ramdisk``. This gives us an extensible platform for the future.

* Enhanced ini-style system for selecting modules to include on your initramfs.
* Enhanced ini-style system for selecting module groups to autoload on the initramfs.
* Support for xz and zstd compression.

How To Use It
=============

First, install the package, via ``emerge ramdisk`` on Funtoo Linux, or alternatively
``pip3 install --user funtoo-ramdisk``. You will then have a ``ramdisk`` command
in your path, which can be used to build a ramdisk.

Then, as a regular user, you can run::

  ramdisk /var/tmp/my-new-initramfs
  sudo cp /var/tmp/my-new-initramfs /boot

By default, ``ramdisk`` will use your ``/usr/src/linux`` symlink to determine which
kernel to use to build a ramdisk for. It will parse ``/usr/src/linux/Makefile``,
extract kernel version information, and then find the appropriate directory in
``/lib/modules/<kernel_name>`` for copying modules. You can type:
``ramdisk list kernels`` and ``ramdisk --kernel <kernel_name>`` to build a ramdisk
for a non-default kernel.

Since this is brand-new software, it is highly recommended that you DO NOT OVERWRITE
YOUR EXISTING, WORKING INITRAMFS THAT YOU CURRENTLY USE TO BOOT YOUR SYSTEM.

Instead -- create a NEW BOOT ENTRY to test your initramfs. In GRUB, you can also
press 'e' to edit an entry and type in the name of the new initramfs to give it a try.

Enjoy -- and let me know how it works for you! Please report issues and feature
requests to https://bugs.funtoo.org.

Plugins
=======

``ramdisk`` ships with a collection of different plugins that add various
boot features to a Funoo Linux system. Included plugins:

* ``btrfs`` -- Adds support for booting off a root volume formatted with `btrfs <https://docs.kernel.org/filesystems/btrfs.html>`_.

* ``core`` -- Adds core components required by every ``ramdisk`` generated initramfs.

* ``luks`` -- Adds support for booting off a `LUKS <https://gitlab.com/cryptsetup/cryptsetup/blob/master/README.md>`_ encrypted root volume.

* ``lvm`` -- Adds support for booting off a LVM root volume.

* ``zfs`` -- Adds support for booting off a ZFS root volume.

Plugin Development Tips
=======================

To contribute and develop new plugins that can extend the functionality of ``ramdisk``
there are various things to consider before diving in.

* All plugin source code is located in the ``funtoo_ramdisk/plugins/`` source directory.

* If you are including new binaries with your plugin in the ``binaries`` Class function,
  they do not have to be statically linked. ``ramdisk`` will automatically include any shared
  libraries that a dynamically linked ELF binary is dependent on.

* Plugin file should match the plugin's Class ``key`` variable's value, which sets the
  ``ramdisk.activate`` name of the plugin.

* Always define the plugin's Class variable called ``hooks`` to set which execution hook
  layers you want the plugin to run at. A list of support hook levels can be found with
  ``git grep execute_plugins funtoo_ramdisk/support/linuxrc``

* Every plugin is represents by a boilerplate Python Class that can be loaded by the main
  ``ramdisk`` application. This Python class acts as an interface to define the attributes
  and functions your ``ramdisk`` plugin.

* To actually do work in a ``ramdisk`` plugin you must define a Class function called
  ``{hook_level}_script(self)`` where ``{hook_level}`` matches hook level name defined in
  the ``hooks`` Class variable. For example ``post_scan_script(self)``

* In this hook level function, a busybox compatible ``/bin/sh`` script is written and embedded.

* A key gotcha to understand when writing these Python plugin embedded shell scripts is
  variable scoping due to recursive shell function calls used in other ``ramdisk`` shell
  init scripts. The plugin scripts are invoked by ``funtoo_ramdisk/support/linuxrc``, then
  a helper function from ``funtoo_ramdisk/support/etc/initrd.scripts`` called ``execute_plugins``
  iteratively executes each hook level plugin shell script.

* If you need to import any common shell functions as part of the initrd scripts or other plugins,
  always source the absolute ramdisk path of those scripts. Common ones include ``/etc/initrd.scripts``
  and ``/etc/plugins/scan_mode/legacy.sh``. You can always verify the validity of this path in a
  ``ramdisk`` rescue shell or by directly deflating a ``ramdisk`` generated initramfs.

* If you need to access kernel boot parameter shell variables in your plugin embedded shell function
  calls, simple add ``. /etc/initrd.scripts``, which will import the ``parse_cmdline`` helper function
  used to properly scope shell variables parsed from ``/proc/cmdline``. This is essentially how you
  propagate downwards important kernel boot parameters that control plugin functionality.

* Another note on shell sourcing within Python plugin embedded shell scripts: Always ensure to
  source everything needed in your plugin script. This allows the plugin to be independently run
  in the ``ramdisk`` rescue shell for extra easy debugging when iteratively testing it.

* If you want to inspect the ``ramdisk`` generated initramfs compressed file contents before
  rebooting with it for additional debugging, you can easily do so in Funtoo Linux. Simply run
  these commands: ``mkdir /tmp/ramdisk ; cd /tmp/ramdisk``, ``cat PATH_TO_INITRAMFS | xz -d -T 0 | cpio -id``.
