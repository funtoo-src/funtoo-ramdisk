udev_setup() {
	good_msg 'Activating mdev'
	touch /dev/mdev.seq
	[ -f /proc/sys/kernel/hotplug ] && echo /sbin/mdev > /proc/sys/kernel/hotplug
	mdev -s || bad_msg "mdev device scan failed"
}

settle_root(){
	# This generic function can be used by any ramdisk plugin
	# It will busy wait for the root block device to become available
	# Positional parameters:
	# $1 -- total boot delay time in seconds, default is 20 seconds
	if [ -z "$1" ]; then
		TOTAL_DELAY="20"
	else
		TOTAL_DELAY="$1"
	fi

	# Default delay for sleeping in the busy wait loop is 0.1 seconds
	# ash does not support floating point arithmetic with its built in operators
	# We have to instead use bustybox's awk for the correct math
	LOOP_DELAY="0.1"
	ITERS=$(/bin/busybox echo $TOTAL_DELAY $LOOP_DELAY | /bin/busybox awk '{print $1 / $2 }
')

	good_msg "Waiting for root block device..."
	ITER="0"
	while [ "$ITER" -lt "$ITERS" ]; do
		ROOT_DEV=$(/sbin/blkid -o device -l -t "${REAL_ROOT}")
		if [ $? -eq 0 ] && [ -b "${ROOT_DEV}" ]; then
			good_msg "Root block device ready ${ROOT_DEV}"
			break
		else
			ITER=$(($ITER + 1))
			sleep $LOOP_DELAY
		fi
	done

	good_msg "Waited ${TOTAL_DELAY} seconds for root block device"
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

# vim: ts=4 sw=4 noet
