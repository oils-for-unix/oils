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
    set -x
    ltrace -e getpwuid -- $sh -c 'echo hi' 2> $trace
    set +x
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
  test-home-dir bash
}

task-five "$@"
