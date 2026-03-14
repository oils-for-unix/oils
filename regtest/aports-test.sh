#!/usr/bin/env bash
#
# Misc tests
#
# Usage:
#   regtest/aports-test.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

test-unshare() {
  # These work (at least on Debian, but it may not work on Red Hat)
  unshare --map-root-user whoami
  unshare --map-root-user /usr/sbin/chroot $CHROOT_DIR ls

  # Hm multiple problems with enter-chroot

  # su: can't set groups: Operation not permitted
  # mv: cannot move '/tmp/tmp.6FHJHwbdMd' to 'env.sh': Permission denied

  unshare --map-root-user \
    sh -x enter-rootfs sh -c 'echo hi; whoami'

  unshare --map-root-user \
    enter-rootfs -u udu sh -c 'echo hi; whoami'
}

test-timeout() {
  ### syntax of timeout command


  # doesn't accept --
  # lame!

  # give 10 second grace period

  # TODO: osh doesn't properly fix this

  local -a cmd=( sh -c 'trap "echo TERM" TERM; sleep 5' )

  # Give it 1 second to respond to SIGTERM, then SIGKILL
  local -a timeout_cmd=( timeout -k 1 0.5 "${cmd[@]}" )

  set +o errexit

  "${timeout_cmd[@]}"

  #return

  # Hm this one doesn't return for 5 seconds?  With either busybox or OSH.  Is
  # that a busybox issue?
  # It falls back on KILL?
  # Could be something in enter-chroot
  # - chroot
  # - env
  # - su
  # - sh -c

  echo
  echo 'CHROOT'

  # alpine uses busybox
  # my version doesn't have -k, but the one in the chroot should
  enter-rootfs-user "${timeout_cmd[@]}"
}

# Note:
# - /var/cache is 5.8 GB after fetching all sources for Alpine main
# - All APKG packages are 6.9 GB, according to APKINDEX

download-apk-index() {
  wget --no-clobber --directory-prefix _tmp \
    http://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/APKINDEX.tar.gz
}

apk-stats() {
  #tar --list -z < _tmp/APKINDEX.tar.gz

  # 5650 packages
  grep 'S:' _tmp/APKINDEX | wc -l

  gawk -f regtest/aports/stats.awk < _tmp/APKINDEX
}

count-lines() {
  for f in regtest/aports-* regtest/aports/*; do
    echo $f
  done | egrep -v 'old|notes' | xargs wc -l | sort -n
}

test-bind-mount() {
  local host_dir=_tmp/bind-test
  mkdir -p $host_dir
  touch $host_dir/foo.txt

  local chroot_dir=$PWD/$CHROOT_DIR
  local guest_dir=$chroot_dir/home/oils/bind-test

  # OK this works; it's a bit awkward

  sudo mkdir -p $guest_dir
  sudo mount --bind $PWD/$host_dir $guest_dir
  sudo chroot $chroot_dir sh -c 'ls /home/oils/bind-test'
  sudo umount $guest_dir

  #mount
}

task-five "$@"
