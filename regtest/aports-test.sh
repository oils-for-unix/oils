#!/usr/bin/env bash
#
# Usage:
#   regtest/aports-test.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

test-unshare() {
  # These work (at least on Debian, but it may not work on Red Hat)
  unshare --map-root-user whoami
  unshare --map-root-user /usr/sbin/chroot $CHROOT_DIR ls

  # Hm multiple problems with enter-chroot

  # su: can't set groups: Operation not permitted
  # mv: cannot move '/tmp/tmp.6FHJHwbdMd' to 'env.sh': Permission denied

  unshare --map-root-user \
    sh -x $CHROOT_DIR/enter-chroot sh -c 'echo hi; whoami'

  unshare --map-root-user \
    $CHROOT_DIR/enter-chroot -u builder sh -c 'echo hi; whoami'
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
  user-chroot "${timeout_cmd[@]}"
}

# Note:
# - /var/cache is 5.8 GB after fetching all sources for Alpine main
# - All APKG packages are 6.9 GB, according to APKINDEX

download-apk-index() {
  wget --no-clobber --directory _tmp \
    http://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/APKINDEX.tar.gz
}

apk-stats() {
  #tar --list -z < _tmp/APKINDEX.tar.gz

  # 5650 packages
  grep 'S:' _tmp/APKINDEX | wc -l

  gawk -f regtest/aports.awk < _tmp/APKINDEX
}

count-lines() {
  ls regtest/aports* | egrep -v 'aports-old|aports-notes' | xargs wc -l | sort -n
}

task-five "$@"
