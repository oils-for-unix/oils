#!/usr/bin/env bash
#
# Usage:
#   test/ltrace.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source test/common.sh  # log

BASE_DIR=_tmp/ltrace

test-home-dir() {
  mkdir -p $BASE_DIR
  rm -f -v $BASE_DIR/*

  # ltrace doesn't work with ASAN, etc.
  local osh=_bin/cxx-dbg/osh
  ninja $osh

  # zsh calls getpwuid
  # bash on my Ubuntu machine doesn't call it, but seems to in the Debian CI
  # image
  # could test mksh, but it's not in the CI image
  for sh in $osh dash "$@"; do
    local trace
    trace=$BASE_DIR/$(basename $sh).txt

    set +o errexit

    set -x
    ltrace -e getpwuid -- $sh -c 'echo hi' 2> $trace
    local status=$?
    set +x
    echo "status=$status"

    set -o errexit
    echo
  done

  wc -l $BASE_DIR/*.txt
  echo

  head $BASE_DIR/*.txt

  if grep getpwuid $BASE_DIR/*.txt; then
    log "ERROR: shells should not call getpwuid()"
    return 1
  fi

  return 0
}

soil-run() {
  # 2025-11: ltrace doesn't seem to work on Github Actions, with podman, even
  # podman 4.9 on Ubuntu
  #
  # This test does NOT fail, but it doesn't test anything either.
  # This is even with PTRACE_FLAGS in soil/host-shim.sh, which fixed ASAN, but
  # not ltrace.
  #
  # ==> _tmp/ltrace/dash.txt <==
  # failed to init breakpoints 1648
  # failed to initialize process 1648: Permission denied
  # couldn't open program '/usr/bin/dash': Permission denied
  # 
  # ==> _tmp/ltrace/osh.txt <==
  # failed to init breakpoints 1645
  # failed to initialize process 1645: Permission denied
  # couldn't open program '_bin/cxx-dbg/osh': Permission denied

  # Did it ever work with Docker?  It's not clear.
  # In any case, we want to switch to podman, and this test is not that
  # important.
  # We could make it a separate Soil task in the future, so it's easier to
  # debug.

  test-home-dir
}

task-five "$@"
