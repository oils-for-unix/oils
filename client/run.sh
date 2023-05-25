#!/usr/bin/env bash
#
# Usage:
#   client/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

demo() {
  echo mystdin | client/headless_demo.py
}

errors() {
  set +o errexit

  # Invalid netstring
  client/headless_demo.py 'zzz'
  echo status=$?   # TODO: assert status

  # Invalid command
  client/headless_demo.py '3:foo,'
  echo status=$?

  # Command doesn't have file descriptors
  client/headless_demo.py '4:ECMD,'
  echo status=$?
}

# Hm what is this suppose to do?  It waits for input
demo-pty() {
  echo mystdin | client/headless_demo.py --to-new-pty
}

soil-run() {
  demo
  echo

  errors
  echo
}


"$@"
