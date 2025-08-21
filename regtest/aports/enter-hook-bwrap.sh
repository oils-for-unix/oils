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

# TODO:
# - We want --unshare-all by default?
#   - Well abuild rootbld already does --unshare net unless you configure it
#     'options_has net'
# - Then --unshare-all --share-net to allow the network

# So then how do we allow these options from enter-chroot?
#
# enter-chroot -k contain-chroot
# enter-chroot -k contain-bwrap-default
# enter-chroot -k contain-bwrap-net
#
# The top-level script:
# - accepts -u flag
# - sets _sudo if we need it
# - preserves env like ARCH|CI|QEMU_EMULATOR|TRAVIS - we can do without this
#   - yeah honestly I wonder if we can get rid of this whole damn thing
#   - we want to preserve SOME of the environment
#
# But we should just allow --setenv VAR value then?  Make it opt-in, not opt-out
#
# Or we could have BWRAP_FLAGS='' env variable?  Or OILS_APORTS_BWRAP_FLAGS?
# because it only is read by this script
#
# Yeah the sudo hook is not useful.  Because bwrap is ROOTLESS.
# 
# All we need is to parse -u ourselves; it's tiny

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
