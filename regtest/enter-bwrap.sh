#!/bin/sh
#
# Enter an Alpine rootfs with bwrap, not chroot.
#
# This

set -e

# TODO: do we need an ENV argument?  
# enter-chroot uses that for TRAVIS_* variables and such.
 
rootfs_dir=${1:-}
if test -z "$rootfs_dir"; then
  # $this_dir idiom
  rootfs_dir=$(cd $(dirname "$0"); pwd)
fi
#echo rootfs_dir=$rootfs_dir

user=${2:-root}

# abuild rootbld has --unshare-ipc, etc. but has OPTION for --unshare-net
# It doesn't use --unshare-all - don't use that; specify everything explicitly
bwrap_flags=${3:-}

shift 3

# note:
# - su must be root to work
# - I'd like it unprivileged

echo RUN "$@"
set -x

# note weird su syntax, without the shell
# su -l "$user" -- -c

bwrap \
  $bwrap_flags \
  --bind "$rootfs_dir" / \
  --proc /proc \
  --bind /proc/sys/kernel/overflowuid /proc/sys/kernel/overflowuid \
  --bind /proc/sys/kernel/overflowgid /proc/sys/kernel/overflowgid \
  --dev /dev \
  -- \
  /usr/bin/env -i -- \
  su -l "$user" -- -c '. /etc/profile; . /env.sh; "$@"' dummy0 "${@:-sh}"

