udev_setup() {
	good_msg 'Activating mdev'
	touch /dev/mdev.seq
	[ -f /proc/sys/kernel/hotplug ] && echo /sbin/mdev > /proc/sys/kernel/hotplug
	mdev -s || bad_msg "mdev device scan failed"
}

udev_settle() {
  return
}

exhaustive_modules_scan() {
  if [ "${MOUNTED_ROOT_FS}" != '1' ] && [ "${DETECT}" != '0' ]; then
    good_msg "Starting modules scanning..."
    while read -r section; do
      modules_scan "${section}"
      # The "quick" boot option: try to short-circuit module loading if we appear successful:
      [ -n "$QUICK" ] && determine_root && mount_real_root && sanity_check_root && break
    done < /etc/modules.autoload
  fi
}