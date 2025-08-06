#!/bin/sh
#
# Enter an Alpine rootfs with bwrap, not chroot.

set -e
 
user=$1
shift

# This is an alternative to alpine-chroot-install/enter-hook-chroot
#
# chroot . /usr/bin/env -i su -l "$user" \
# 	sh -c '. /etc/profile; . /env.sh; "$@"' \
# 	-- "$@"
#
# But note: we could do this all with bwrap?
#
# - instead of su $user, look up the uid and gid outside
# - instead of su, look up the login shell, $HOME, and $PATH
# - instead of su -l - not sure?
#   - oh does that just mean we invoke it with argv[0] as -sh?
# - insetad of env -i, --clearenv instead of env -i
# - instead of . /env.sh --setenv instead of . /env.sh

# Notes:
# - enter-chroot does cd $CHROOT_DIR
# - overflow{uid,gid} is necessary for nested bwrap

bwrap \
  --bind . / \
  --proc /proc \
  --bind /proc/sys/kernel/overflowuid /proc/sys/kernel/overflowuid \
  --bind /proc/sys/kernel/overflowgid /proc/sys/kernel/overflowgid \
  --dev /dev \
  -- \
  /usr/bin/env -i su -l "$user" \
  sh -c '. /etc/profile; . /env.sh; "$@"' \
  -- "$@"
