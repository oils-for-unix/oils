#!/usr/bin/env bash
#
# Usage:
#   test/ltrace.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/run-task.sh
source test/common.sh  # log

BASE_DIR=_tmp/ltrace

test-home-dir() {

  mkdir -p $BASE_DIR

  # ltrace doesn't work with ASAN, etc.
  local osh=_bin/cxx-dbg/osh
  ninja $osh

  local status=0

  # zsh calls getpwuid
  # bash on my Ubuntu machine doesn't call it, but seems to in the Debian CI
  # image
  for sh in $osh dash mksh "$@"; do
    local trace
    trace=$BASE_DIR/$(basename $sh).txt

    ltrace -e getpwuid -- $sh -c 'echo hi' 2> $trace

    if grep getpwuid $trace; then
      log "ERROR: $sh should not call getpwuid()"
      status=1
    fi
  done

  return $status
}

soil-run() {
  test-home-dir
}

run-task "$@"
