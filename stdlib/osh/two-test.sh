#!/usr/bin/env bash

source stdlib/osh/two.sh  # module under test

source stdlib/osh/byo-server.sh
source stdlib/osh/testing.sh

set -o nounset
set -o pipefail
set -o errexit

test-log() {
  local status stderr

  capture-cmd-2 status stderr \
    log hi

  sh-assert 'hi' = "$stderr"
  sh-assert 0 = "$status"
}

test-die() {
  local status

  # This calls exit, so we don't use capture-cmd

  set +o errexit
  ( die "bad" )
  status=$?
  set -o errexit

  sh-assert 1 -eq "$status"
}

byo-must-run
