#!/bin/bash
#
# Demonstrate some OSH debug/development features.
#
# Usage:
#   ./osh-debug.sh <function name>

set -o nounset
set -o pipefail

set -o errexit

parser-mem-dump() {
  local big=benchmarks/testdata/configure-coreutils
  #local big=_tmp/e.sh

  local dump=_tmp/parser-mem-dump.txt 

  set +o errexit
  rm -f $dump
  bin/osh --parser-mem-dump $dump $big
  grep '^Vm' $dump

  echo '==='

  # It ONLY works with -n, because we don't load the whole thing into memory
  # otherwise?
  rm -f $dump
  bin/osh --parser-mem-dump $dump -n --ast-format none $big
  grep '^Vm' $dump
}

runtime-mem-dump() {
  #local big=_tmp/e.sh
  local big=devtools/release.sh  # just run through all the functions
  local dump=_tmp/runtime-mem-dump.txt 

  set +o errexit
  rm -f $dump
  bin/osh --runtime-mem-dump $dump $big
  grep '^Vm' $dump
}

myfunc() {
  metrics/source-code.sh osh-cloc
}

# Make sure it works recursively
#
# Problem: xargs, find -exec, make, etc. won't respect this!  They will use the
# real shebang.

recursive() {
  echo ===
  $0 myfunc
  echo ===
}

hijack-recursive() {
  # $(which osh)

  local dir=_tmp/osh-debug
  mkdir -p $dir

  OSH_DEBUG_DIR=$dir \
  OSH_HIJACK_SHEBANG=bin/osh \
    bin/osh $0 recursive
}

#
# For the release
#

# Must be an absolute path!  Otherwise it will fail.
readonly RELEASE_LOGS_DIR=$PWD/_tmp/osh-debug-release

osh-for-release() {
  mkdir -p $RELEASE_LOGS_DIR
  rm -f $RELEASE_LOGS_DIR/*

  # NOTE: This runs the SYSTEM osh, because running bin/osh while doing the
  # release doesn't work!
  OSH_DEBUG_DIR=$RELEASE_LOGS_DIR OSH_HIJACK_SHEBANG=$(which osh) osh
}

analyze() {
  grep '^Hijacked' $RELEASE_LOGS_DIR/*
}

"$@"
