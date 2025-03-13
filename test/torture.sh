#!/usr/bin/env bash
#
# Torture the shell
#
# Usage:
#   test/torture.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/no-quotes.sh

source test/common.sh  # run-test-funcs

test-infinite-redir() {
  local sh=${1:-bash}

  # dash: 1: Maximum function recursion depth (1000) reached

  # bash environment: redirection error: cannot duplicate fd: Too many open files
  # environment: line 1: /dev/null: Too many open files

  # osh finds this
  # [ -c flag ]:1: I/O error applying redirect: Too many open files

  $sh -c 'f() { f > /dev/null; }; f'
}


run-for-release() {
  run-other-suite-for-release torture run-test-funcs
}

soil-run() {
  run-test-funcs
}

"$@"
