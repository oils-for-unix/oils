#!/bin/sh
#
# Enter an Alpine rootfs with bwrap, not chroot.
#
# This is an alternative to 'enter-chroot'.  It's not a "hook", like
# regtest/enter-hook-{bwrap,chroot}

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

# this prints the line, but it's hard to parse in shell
#  getent passwd "$user"

# this seems like the most reliable way to get

temp_prefix="/tmp/$$"

uid_file=$temp_prefix.uid.txt
gid_file=$temp_prefix.gid.txt
home_file=$temp_prefix.home.txt
shell_file=$temp_prefix.shell.txt

awk -F : \
  -v user=$user \
  -v uid_file=$uid_file \
  -v gid_file=$gid_file \
  -v home_file=$home_file \
  -v shell_file=$shell_file \
  '
  $1 == user {
    #printf("FOUND User %s in the rootfs\n", user);
    print $3 > uid_file
    print $4 > gid_file
    print $6 > home_file
    print $7 > shell_file
    found = 1
    exit  # jumps to the END block
  }

  END {
    if (found == 0) {
      printf("User %s not found in the rootfs\n", user);
      exit 1
    }
  }
  ' $rootfs_dir/etc/passwd

# Note: there is a slurp operator in bash/ksh $(<file)
uid=$(cat $uid_file)
gid=$(cat $gid_file)
user_home=$(cat $home_file)
user_shell=$(cat $shell_file)

# Clean up
rm $temp_prefix*

if false; then
  echo uid=$uid
  echo gid=$gid
  echo home=$user_home
  echo shell=$user_shell
fi

if true; then
# rootless method

bwrap \
  $bwrap_flags \
  --unshare-user \
  --uid $uid \
  --gid $gid \
  --clearenv \
  --setenv USER $user \
  --setenv LOGNAME $user \
  --setenv SHELL $user_shell \
  --setenv HOME $user_home \
  --bind "$rootfs_dir" / \
  --proc /proc \
  --bind /proc/sys/kernel/overflowuid /proc/sys/kernel/overflowuid \
  --bind /proc/sys/kernel/overflowgid /proc/sys/kernel/overflowgid \
  --dev /dev \
  -- \
  $user_shell -c '. /etc/profile; "$@"' dummy0 "${@:-sh}"

else
  # this requires root, because su requires root

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
fi
