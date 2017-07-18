#!/bin/bash
#
# Usage:
#   ./count-procs.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

count-procs() {
  local sh=$1
  local code=$2

  # Hm I didn't know -e is like a mini-language.  '-e open' is thes same as '-e
  # trace=open'.  signal=none turns off the SIGCHLD lines.
  #
  # NOTE we grep for [pid and rely on the code itself to echo [pid-of-sh $$].

  code='echo "[pid-of-sh $$]";'" $code"
  strace -e 'trace=fork,execve' -e 'signal=none' -e 'verbose=none' -ff -- \
    $sh -c "$code" 2>&1 | fgrep '[pid' || true
}

test-many() {
  for code in "$@"; do
    echo
    echo
    echo "--- $code ---"
    echo

    for sh in dash bash mksh zsh; do
      echo
      echo
      echo "--- $sh ---"
      echo
      count-procs $sh "$code"
    done
  done
}

t1() {
  test-many \
    'echo hi' \
    '/bin/echo one; /bin/echo two' \
    '{ /bin/echo one; /bin/echo two; }' \
    '{ echo one; echo two; } | wc -l' \
    '( echo one; echo two ) | wc -l' 
}

"$@"
