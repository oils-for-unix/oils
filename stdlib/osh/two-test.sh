#!/usr/bin/env bash

source stdlib/osh/two.sh
source stdlib/osh/byo-server-lib.sh

source test/common.sh  # assert

set -o nounset
set -o pipefail
set -o errexit

test-log() {
  local stderr
  local status

  set +o errexit
  stderr=$(log hi 2>&1)
  status=$?
  set -o errexit

  assert 'hi' = "$stderr"
  assert 0 -eq "$status"
}

test-die() {
  local status

  set +o errexit
  ( die "bad" )
  status=$?
  set -o errexit

  assert 1 -eq "$status"
}

byo-maybe-main
