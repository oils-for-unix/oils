#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o errexit

: ${LIB_OSH=stdlib/osh}

source $LIB_OSH/two.sh  # module under test

source $LIB_OSH/no-quotes.sh
source $LIB_OSH/task-five.sh

test-log() {
  local status stderr

  nq-capture-2 status stderr \
    log hi

  nq-assert 'hi' = "$stderr"
  nq-assert 0 = "$status"
}

test-die() {
  local status

  # This calls exit, so we don't use nq-capture

  set +o errexit
  ( die "bad" )
  status=$?
  set -o errexit

  nq-assert 1 -eq "$status"
}

task-five "$@"
