#!/usr/bin/env bash
#
# Torture the shell
#
# Usage:
#   test/torture.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/task-five.sh

test-infinite-func() {
  local sh=${1:-bash}

  # bash goes forever?
  # mksh  segfaults
  # ash: default
  # dash limits to 1000; zsh limits to FUNCNEST
  # osh: seg fault

  $sh -c 'f() { f; }; f'
}

test-infinite-redir() {
  local sh=${1:-bash}

  # dash: 1: Maximum function recursion depth (1000) reached

  # bash environment: redirection error: cannot duplicate fd: Too many open files
  # environment: line 1: /dev/null: Too many open files

  # osh finds this
  # [ -c flag ]:1: I/O error applying redirect: Too many open files

  $sh -c 'f() { f > /dev/null; }; f'
}

task-five "$@"
