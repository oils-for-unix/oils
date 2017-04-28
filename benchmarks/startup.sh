#!/bin/bash
#
# Usage:
#   ./startup.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly TIMEFORMAT='%R'

# 3 groups:
# dash/mksh/lua/awk: < 90 syscalls
# bash/zsh/perl: 145-289 syscalls
# python -S/python3 -S/ruby: 200-800 syscalls

# This throws off absolute timing, but relative still makes sense.
# TODO: get rid of wc -l if not.


strace-callback() {
  strace "$@" 2>&1 | wc -l
}

time-callback() {
  time "$@" >/dev/null
}

compare() {
  local callback=${1:-strace-callback}

  # dash is the fastest: 0 ms.
  for sh in bash dash mksh zsh; do
    echo $sh
    $callback $sh -c 'echo "hi" > /dev/null'
    echo
  done

  # gawk is slower than mawk
  for awk in gawk mawk; do
    echo $awk
    $callback $awk '{ print "hi" } ' < /dev/null
    echo
  done

  echo lua
  $callback lua -e 'print "hi"'
  echo

  echo perl
  $callback perl -e 'print "hi\n"'
  echo

  # Woah 247 ms?  Ruby is slower than Python.
  echo ruby
  $callback ruby -e 'print "hi\n"'
  echo

  # Oh almost all stats come from -S!
  for py in python python3; do
    echo $py -S
    $callback $py -S -c 'print("hi")'
    echo
  done

  for py in python python3; do
    echo $py import
    $callback $py -S -c 'import json;print("hi")'
    echo
  done

  for py in python python3; do
    echo $py import
    $callback $py -S -c 'import json;print("hi")'
    echo
  done

  for py in python python3; do
    echo $py two import
    $callback $py -S -c 'import traceback;import json;print("hi")' || true
    echo
  done
}

compare-strace() {
  compare strace-callback
}

compare-time() {
  compare time-callback
}

import-stats() {
  # 152 sys calls!  More than bash needs to start up.
  echo json
  strace python -c 'import json' 2>&1 | grep json | wc -l

  echo nonexistent___
  strace python -c 'import nonexistent___' 2>&1 | grep nonexistent___ | wc -l
}

"$@"
