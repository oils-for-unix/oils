#!/usr/bin/env bash
#
# Figuring out how GNU timeout works.
#
# Usage:
#   soil/timeout-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

test-simple() {
  time timeout 0.1 sleep 10
}

one() {
  echo "- sleep 0.$1 in pid $$"
  sleep 0.$1
}

many() {
  seq 5 8 | xargs -n 1 -P 3 $0 one
}

test-xargs() {
  local pid=$$
  set +o errexit

  # This shows the full process tree
  $0 many &

  #timeout 0.1 $0 many &

  sleep 0.1
  pstree --ascii -p $pid

  echo 'Any sleep processes alive?'
  pgrep sleep

  wait
  echo status=$?
}

all() {
  run-test-funcs
}

"$@"
