funtoo-ramdisk 1.1.16
---------------------

Released on June 27, 2024.

This is a feature release.

* Add btrfs boot support.
* Added v1 cryptsetup luks plugin (add more)
* Add generic settle_root function.

funtoo-ramdisk 1.1.15
---------------------

Released on April 28, 2024.

This is a feature and bug fix release. ``1.1.14`` contains the same
code but is missing this ChangeLog update and more detail to the
``lsblk`` output for rescue shell.

* Add man page options on the kernel boot options for the initramfs.

* Add ``lsblk`` to the initramfs and use it to generate nice output
  when falling to the rescue shell to aid troubleshooting.

* Only print errors if we have problems loading kpop modules.
  Otherwise ignore errors. Most modules don't throw errors and fail
  to load when the underlying hardware is not found, but there are
  exceptions to this that was previously cluttering output.

* FL-12290: Include "vmscsi" modules definition to enable SCSI boot
  support for VirtualBox and likely other VMs, and make this fairly
  high priority in the scan order.


funtoo-ramdisk 1.1.13
---------------------

Released on April 23, 2024.

This is a bug fix release.

* Integrate siris' PR which gets the lvm plugin working under Funtoo.
  This should allow for official support of LVM root filesystems.


funtoo-ramdisk 1.1.12
---------------------

Released on April 19, 2024.

This is a bug fix release.

* Fix man page generation (docutils recently renamed ``rst2man.py`` to
  ``rst2man``)

funtoo-ramdisk 1.1.11
---------------------

Released on April 17, 2024.

This is a feature release.

* Linux 6.6+ now builds and installs kernel modules with the ``.ko.xz``
  suffix. This requires several code updates to support this new naming
  scheme. This is the initial implementation and there may be additional
  needed fixes for things like the initramfs after this is tested using
  this updated initramfs-build code.

funtoo-ramdisk 1.1.10
---------------------

Released on April 16, 2024.

This is a minor bug fix release.

* Attempting to fix an issue where the temporary kernel modules directory
  is not properly created, resulting in an error.

funtoo-ramdisk 1.1.9
--------------------

Released on April 16, 2024.

This is a minor feature release.

* Add a ``--keep`` option which will preserve the contents of the
  temporary directory so that errors and tracebacks can be investigated. 
  This can be enabled via ebuilds to allow exploration of any ramdisk-
  related errors.

* Improve handling of a permissions error when copying the ramdisk to
  a final location (provide error message instead of full traceback.)

funtoo-ramdisk 1.1.8
--------------------

Released on April 16, 2024.

This is a minor bug release.

* Fix for the previous fix.

funtoo-ramdisk 1.1.7
--------------------

Released on April 15, 2024.

This is a minor bug release.

* Fix a possible issue where ``__pycache__`` directories can mess
  up copying of files to the initramfs.

funtoo-ramdisk 1.1.6
--------------------

Released on April 14, 2024.

This is a maintenance and minor features release.

* Various minor bug fixes.

* Change ``--enable`` to ``--plugins`` since it's more
  self-explanatory.

* Continue to flesh out the plugin system. I added support for
  plugins to have an activation script which will get executed
  on startup. This is a work in progress and I still need to
  add support for listing needed modules for a plugin which
  will get loaded automatically.

* Fix a bug in argument parsing where the code was not scanning
  for invalid options which could result in odd parsing behavior.

* Start adding support for udev. This is not yet completed but
  the plugin system for this has been incorporated into the
  linuxrc.


funtoo-ramdisk 1.1.5
--------------------

Released on September 15, 2023.

This is a packaging fix for the manpage.


funtoo-ramdisk 1.1.4
--------------------

Released on September 15, 2023.

This release adds a "ramdisk" man page.


funtoo-ramdisk 1.1.3
--------------------

Released on September 14, 2023.

* FL-11606: ``/sbin/blkid`` can't be run as non-root, and will
  trigger a sandbox violation inside an ebuild. So don't do it --
  we were just running it to convieniently spit out the UUID for
  the user to put in their ``/etc/fstab``. Now we instruct the
  user to run ``blkid`` as root and avoid the sandbox violation.


funtoo-ramdisk 1.1.2
--------------------

Released on September 4, 2023.

* Fix exit code (zero on success.)


funtoo-ramdisk 1.1.1
--------------------

Released on September 4, 2023.

Fix three bugs:

* Allow plugins to be loaded when installed in ``site-packages``.

* Don't assume ``/usr/src/linux`` symlink exists in two places and
  handle this situation gracefully. This situation may exist during
  metro builds on incomplete systems. (2 bugs fixed).


funtoo-ramdisk 1.1.0
--------------------

Released on September 3, 2023.

* Add plugin system for ramdisk:

  To use, pass ``--enable=<plugin1>,<plugin2>``. The ``core`` plugin is
  always enabled and copies ``/sbin/blkid``. There are currently ``btrfs``
  and ``lvm`` plugins as well -- these are not yet fully-implemented and
  just ensure necessary binaries are copied over (no extra setup commands
  are run by the initramfs.)

  This is a starting point for enabling support for advanced
  features on the initramfs.

* New "module configurations". The default module configuration is "full",
  which means "make a ramdisk with lots of modules to support a lot of
  hardware." Different module configurations can be added in the future.
  Module configurations can be specified via ``--kmod_config=``.

* ``--kpop=`` feature to make minimal module ramdisks by specifying a
  dynamic module configuration via the command-line, rather than via
  static config files.

  If you specify ``--kpop=nvme,ext4`` then a ramdisk with just those
  modules (and their dependencies) will be included. This can dramatically
  reduce the size of your ramdisk. Note that this doesn't include the
  necessary modules to allow USB keyboards to work in the rescue shell,
  so it's only for known-good configurations. Enabling this feature also
  disables any static module configuration (see above.)

* Change the binary plugin API so lists of binaries can be dynamically
  created and programmatic decisions can be made. Previously, we used a
  static list. This allows us to use ``lvm.static`` if available, but
  fall back to dynamic ``lvm``, for example.

* To support ``kpop`` functionality, the ability to add a module by its
  basic name, not just via its full path or glob, was added to
  ``modules.copy``.

* Modules code can now accept ``modules.copy`` and ``modules.autoload``
  as dynamically-generated line data rather than just as static files
  that must exist on the filesystem. (Again, used by ``kpop``).

* ``linuxrc`` has been improved/fixed to not have a hard-coded list of
  module groups to try to load, and instead use the ``modules.autoload``
  groups to determine these.

* ``ramdisk list kernels`` and ``ramdisk list plugins`` actions added.
  The former makes use of ``ramdisk --kernel <kv>`` easier because it
  prints the available kernel names which can be copy/pasted for the
  ``--kernel`` option.

* Implemented our own argument parsing as ``argparse`` was not worth
  using.

* Lots of code organized into their own ``.py`` files.

* Make ``/etc/fstab`` sanity check a warning as this file may not be
  set up at all if doing a metro build.

* Disable colors if we don't have an interactive shell.


funtoo-ramdisk 1.0.7
--------------------

Released on August 22, 2023.

Changes:

* Get rid of ``--modules_root``. Instead, added ``--fs_root`` which
  specifies where modules *and* the kernel sources will be. This
  allows the tool to work from an ebuild.

* Improve output and add nice colors. Optimize information to be
  more useful to users.


funtoo-ramdisk 1.0.6
--------------------

Released on August 21, 2023.

Two new options:

* ``--modules_root`` to set the root filesystem to scan for modules.
  It defaults to ``/``.

* ``--temp_root`` to set the default path to use for creating a
   temporary directory. It defaults to ``/var/tmp``.

funtoo-ramdisk 1.0.5
--------------------

Released on August 21, 2023.

This is a features/maintenance/bug fix release.

In addition to a bunch of minor fixes and clean-ups, which you can
view in the git history, the following significant changes were
made:

* Use kmod ``/sbin/modprobe`` instead of busybox's modprobe. Busybox's modprobe
  may be fine, but for it to work, we must use busybox's ``depmod`` -- and we're
  not. We're using ``kmod``'s. So for now, let's just copy the right modprobe
  over. This fixes an issue where we get invalid symbols when loading modules
  using busybox ``modprobe``. ``modprobe`` is now resolving deps properly! :)

  At some point, we could make a "toggle" to select kmod/busybox mode. The
  best time to run ``depmod`` for busybox is probably once the ramdisk first
  boots, since it doesn't have a "root" option, making it hard to call from our
  ramdisk script.

* Remove unused control character definitions in ``initrd.defaults``.

* Mitigate an issue where ``ash`` shell could start before all USB keyboards
  have been detected, resulting in lack of input. We now wait 5 seconds
  before starting a rescue shell, to give the kernel time to enumerate
  devices on the USB2/3 bus. This isn't a full fix, but should resolve
  the problem of ``ash`` starting and not having any way to type, because
  it didn't connect to your main keyboard.

Try to work around issues related to ATA/SCSI disk enumeration which could
prevent the root filesystem from being mounted (see FL-11532).

* Detect when a user has a ``/dev/sd*`` root block device and warn them that
  this is not a good idea, and can cause problems if you have multiple
  disks. Show them how to fix the problem by switching to UUID.

* Remove scsi_debug module which is evil and if we force-load it, will create
  a new SCSI device 8MB in size and trigger the problem above for anyone
  with a SATA disk.

* To implement above feature, added a feature to allow masking of modules in
  ``modules.copy`` via "-mod_shortname" in a specific section. Also added a
  lot of sanity checking and warnings. If you happen to mask a module in the
  wrong section, so it still gets included on the initramfs due to other
  section(s), we will warn you.


funtoo-ramdisk 1.0.4
--------------------

Released on August 18, 2023.

This is a maintenance/bug fix release.

* Fix ability to run from the git repo. This wasn't working.

* Fix issue found by grouche, where if a module is built-in to the
  kernel but listed in ``modules.autoload``, ``ramdisk`` would throw
  an error because it would think it's not copied to the initramfs.
  We now read in the ``modules.builtin`` file and use this in the
  internal logic -- if a module is built-in to the kernel, we can
  not worry if it is our ``modules.autoload`` list. We still have it.
  We will also not worry about trying to load it at boot.

* Add a debug output whenever a module is referenced that is actually
  a built-in. This helps to audit the behavior of the above
  functionality and could be useful to users of the tool as well.

* Announce we are in debug mode with ``log.info()`` instead of a
  warning. Looks a bit nicer.

