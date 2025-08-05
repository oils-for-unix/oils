#!/usr/bin/env bash
#
# Usage:
#   ./aports-debug.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source regtest/aports-common.sh

chroot-manifest() {
  local name=${1:-foo}

  # TODO: use this to help plan OCI layers
  # 251,904 files after a build of mpfr

  local out=_tmp/$name.manifest.txt

  # pipefail may fail
  set +o errexit
  sudo find $CHROOT_DIR \
    -name proc -a -prune -o \
    -type f -a -printf '%P %s\n' |
    sort | tee $out

  echo
  echo "Wrote $out"
}

show-chroot() {
  sudo tree $CHROOT_HOME_DIR/oils/_tmp
}

sizes() {
  set +o errexit

  # 312 MB
  sudo du --si -s $CHROOT_DIR 

  # 29 MB after 80 source packages, that's not so much

  # getting up to 373 M though - worth sharding
  sudo du --si -s $CHROOT_DIR/var/cache

  sudo du --si -s $CHROOT_DIR/var/cache/distfiles

  # 110 MB just of logs
  # need to thin these out
  sudo du --si -s $CHROOT_HOME_DIR/oils/_tmp/

  sudo du --si -s $BASE_DIR/
}

archived-fetched() {
  local tar=_chroot/distfiles.tar
  tar --create --file $tar --directory $CHROOT_DIR/var/cache/distfiles .

  tar --list < $tar
  echo
  ls -l --si $tar
  echo
}

filter-basename() {
  sed 's|.*/||g'
}

readonly C_BUG='cannot create executable|cannot compile programs|No working C compiler'
readonly B_BUG='builddeps failed'

grep-c-bug-2() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-05-baseline}

  egrep "$C_BUG" $epoch_dir/*/baseline/log/* #| filter-basename 
}

grep-b-bug-2() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-05-baseline}

  egrep "$B_BUG" $epoch_dir/*/baseline/log/* #| filter-basename 
}

grep-c-bug() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-04-rootbld}

  egrep -l "$C_BUG" $epoch_dir/*/baseline/log/* | filter-basename > _tmp/b.txt
  egrep -l "$C_BUG" $epoch_dir/*/osh-as-sh/log/* | filter-basename > _tmp/o.txt

  wc -l _tmp/{b,o}.txt
  diff -u _tmp/{b,o}.txt || true
  echo
  echo done
}

grep-b-bug() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-04-rootbld}

  egrep "$B_BUG" $epoch_dir/*/baseline/log/* 

  egrep -l "$B_BUG" $epoch_dir/*/baseline/log/* | filter-basename > _tmp/b-b.txt
  egrep -l "$B_BUG" $epoch_dir/*/osh-as-sh/log/* | filter-basename > _tmp/b-o.txt

  wc -l _tmp/b-{b,o}.txt
  diff -u _tmp/b-{b,o}.txt || true
  echo
  echo done
}

update-build-server() {
  ssh -A he.oils.pub 'set -x; cd git/oils-for-unix/oils; git fetch; git status'
}

bwrap-demo() {
  # chroot only
  user-chroot sh -c '
  whoami; pwd; ls -l /
  set -x
  cat /proc/sys/kernel/unprivileged_userns_clone
  cat /proc/sys/user/max_user_namespaces
  unshare --user echo "Namespaces work"
  '

  user-chroot sh -c 'bwrap ls -l /'
}

task-five "$@"
