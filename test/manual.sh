#!/usr/bin/env bash
#
# Manual tests
#
# Usage:
#   test/manual.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

readonly OSHRC=_tmp/manual-oshrc

setup() {
  cat >$OSHRC <<EOF
OILS_COMP_UI=nice
EOF
}

test-osh() {
  # Test it manually
  bin/osh --rcfile $OSHRC
}

test-ysh() {
  # same OSHRC?  Should it respect ENV.OILS_COMP_UI?
  bin/ysh --rcfile $OSHRC
}

task-five "$@"
