#!/usr/bin/env bash
#
# Usage:
#   client/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python3
source devtools/task-five.sh

py-demo() {
  echo mystdin | client/headless_demo.py --sh-binary bin/osh
}

cpp-demo() {
  local bin=_bin/cxx-dbg/osh
  ninja $bin
  echo mystdin | client/headless_demo.py --sh-binary $bin
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

soil-run-py() {
  py-demo
  echo

  errors
  echo
}

soil-run-cpp() {
  which python3
  echo

  cpp-demo
}


task-five "$@"
