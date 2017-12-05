#!/usr/bin/env bash
#
# Wild tests that actually run code.
#
# TODO:
# - Use a better name.  Maybe move Python's configure to conf-wild.  This could
#   be misc-wild.
# - There are a lot of hard-coded paths in this script.
#
# Usage:
#   ./wild2.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly OSH=~/git/oilshell/oil/bin/osh

replace-shebang() {
  local dir=$1
  find $dir -name '*.sh' \
    | xargs -- sed -i 's|^#!/bin/bash|#!/home/andy/git/oil/bin/osh|'
}

readonly TOYBOX_DIR=~/git/other/toybox

replace-toybox() {
  replace-shebang $TOYBOX_DIR
}

build-toybox() {
  cd $TOYBOX_DIR
  make clean
  make
}

#
# Debootstrap
#

readonly DE_DIR=~/git/basis-build/_tmp/debootstrap

sh-debootstrap() {
  local sh=$1
  shift
  DEBOOTSTRAP_DIR=$DE_DIR $sh $DE_DIR/debootstrap "$@"
}

osh-de-help() {
  time sh-debootstrap $OSH --help
  #time sh-debootstrap bash --help
  #time sh-debootstrap dash --help
}

# Probably not great to run as root.
sh-de-xenial() {
  local sh=$1
  local target_dir=_tmp/debootstrap/$sh-xenial
  mkdir -p $target_dir
  time sudo $0 debootstrap $sh xenial $target_dir || true
}

#
# Configure (NOTE: Subsumed by benchmarks/osh-runtime.sh)
#

readonly PYTHON_DIR=$PWD/Python-2.7.13

sh-py-configure() {
  local sh=${1:-bash}
  local out=_tmp/wild2/$(basename $sh)-py-configure
  mkdir -p $out

  pushd $out
  time $sh $PYTHON_DIR/configure || true
  popd

  tree $out
}

# ~18 seconds vs ~10 seconds.
osh-py-configure() {
  OIL_TIMING=1 sh-py-configure $OSH
}

# NOTE: These would compare more equally if we put them in the same dir, and
# then copied it elsewhere.
compare-pyconfig() {
  diff -u -r _tmp/wild2/{bash,osh}-py-configure
  #diff -u -r _tmp/wild2/{bash,osh}-py-configure/config.status
}

# Hm this is behavior differently.  Ideas for better xtrace in osh:
#
# - PID (not just +)
# - indent by callstack
# - maybe even the line number.  That should be easy to get from
#   SimpleCommand.

sh-config-status() {
  local sh=${1:-bash}
  local out=_tmp/wild2/$(basename $sh)-py-configure

  pushd $out
  $sh ./config.status
  #sh -x ./config.status
  #strace -e close,dup2,fcntl -- $sh ./config.status
  popd
  echo status=$?

  tree $out
}

osh-config-status() {
  #OIL_TIMING=1 
  sh-config-status $OSH
}

# TODO: Save these files and make sure they are the same! 

"$@"
