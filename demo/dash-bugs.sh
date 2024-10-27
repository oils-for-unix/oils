#!/bin/sh
#
# Bug copied from _build/oils.sh

# Usage:
#   demo/dash-bugs.sh <function name>

set -o nounset
#set -o pipefail
set -o errexit

compile_one() {
  echo compile_one "$@"
  sleep 1
}

_compile_one() {
  #local src=$4

  #echo "CXX $src"

  echo _do_fork=${_do_fork:-}

  # Delegate to function in build/ninja-rules-cpp.sh
  if test "${_do_fork:-}" = 1; then
    echo FORKING
    compile_one "$@" &   # we will wait later
  else
    compile_one "$@"
  fi
}

demo() {
  # Early versions of dash run this incorrectly!

  _do_fork=1 _compile_one A
  _compile_one B
  _compile_one C
}


"$@"
