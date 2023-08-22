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
  initramfs, the shell code is about 10x simpler and a lot cleaner, but does
  the same thing and has been modernized. About 100 lines of shell script,
  with another 215 lines of functions in a support file.

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

* If you are still able to find some modules that got loaded that you
  don't want loaded, you can use the "magic modules" feature to specify
  just the modules you want to load. Specify ``magic=mod1,mod2,mod3``
  as a kernel argument and just these modules will be loaded.

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
``/lib/modules/<kernel_name>`` for copying modules.

Since this is brand-new software, it is highly recommended that you DO NOT OVERWRITE
YOUR EXISTING, WORKING INITRAMFS THAT YOU CURRENTLY USE TO BOOT YOUR SYSTEM.

Instead -- create a NEW BOOT ENTRY to test your initramfs. In GRUB, you can also
press 'e' to edit an entry and type in the name of the new initramfs to give it a try.

Enjoy -- and let me know how it works for you! Please report issues and feature
requests to https://bugs.funtoo.org.
