#!/usr/bin/env bash

source stdlib/osh/two.sh  # module under test

source stdlib/osh/byo-server.sh
source stdlib/osh/no-quotes.sh

set -o nounset
set -o pipefail
set -o errexit

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

byo-must-run
