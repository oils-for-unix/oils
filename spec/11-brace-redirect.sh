#!/bin/bash

set -o nounset
set -o pipefail
set -o errexit

# TODO: Move this
redirect-test() {
  local pid=$$

  echo "PID: $pid"

  # NOTE: no subshells for this.  Just file descriptor manipulation.

  { i=0
    while true; do
      sleep 0.5
      echo $i
      i=$((i+1))
      if test $i -eq 20; then
        break
      fi
    done
  } 1>&2

  #proc_tree $pid
  wait
}

redirect-test "$@"
