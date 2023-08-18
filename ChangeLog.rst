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

