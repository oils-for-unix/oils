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

grep-bug-c() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-04-he}

  local bad='cannot create executable|cannot compile programs|No working C compiler'

  egrep -l "$bad" $epoch_dir/*/baseline/log/* | filter-basename > _tmp/b.txt
  egrep -l "$bad" $epoch_dir/*/osh-as-sh/log/* | filter-basename > _tmp/o.txt

  wc -l _tmp/{b,o}.txt
  diff -u _tmp/{b,o}.txt || true
  echo
  echo done
}

grep-builddeps() {
  local epoch_dir=${1:-$REPORT_DIR/2025-08-04-he}

  local bad='builddeps failed'
  egrep "$bad" $epoch_dir/*/baseline/log/* 

  egrep -l "$bad" $epoch_dir/*/baseline/log/* | filter-basename > _tmp/b-b.txt
  egrep -l "$bad" $epoch_dir/*/osh-as-sh/log/* | filter-basename > _tmp/b-o.txt

  wc -l _tmp/b-{b,o}.txt
  diff -u _tmp/b-{b,o}.txt || true
  echo
  echo done
}

update-build-server() {
  ssh -A he.oils.pub 'set -x; cd git/oils-for-unix/oils; git fetch; git status'
}

task-five "$@"
