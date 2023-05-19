#!/usr/bin/env bash
#
# Demonstrate some OSH debug/development features.
#
# Usage:
#   ./osh-debug.sh <function name>

set -o nounset
set -o pipefail

set -o errexit

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
  OILS_HIJACK_SHEBANG=bin/osh \
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
  OSH_DEBUG_DIR=$RELEASE_LOGS_DIR OILS_HIJACK_SHEBANG=$(which osh) osh
}

analyze() {
  grep '^Hijacked' $RELEASE_LOGS_DIR/*
}

"$@"
