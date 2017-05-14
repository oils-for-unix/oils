#!/bin/bash
#
# Usage:
#   ./background-status.sh <function name>

set -o nounset
#set -o pipefail
#set -o errexit  # wait waill fail with this

do_some_work() {
  sleep 0.2
  exit $1
}

wait_pids() {
  { sleep 0.1; exit 5; } &
  pid1=$!

  do_some_work 6 &
  pid2=$!

  { sleep 0.3; exit 7; } &
  pid3=$!

  do_some_work 8 &
  pid4=$!

  echo "Waiting for PIDs $pid1 $pid2 $pid3"

  wait $pid1; echo $?
  wait $pid2; echo $?
  wait $pid3; echo $?
  wait $pid4; echo $?

  echo 'Done'
}

# NOTE: dash/mksh/zsh all lack the -n option.  That seems like an oversight.
wait_next() {
  { sleep 0.1; exit 8; } &
  pid1=$!

  { sleep 0.2; exit 9; } &
  pid2=$!

  { sleep 0.3; exit 10; } &
  pid3=$!

  wait -n; echo $?
  wait -n; echo $?
  wait -n; echo $?

  echo 'Done'
}

both() {
  wait_pids
  wait_next
}

# ERROR: says "no job control"
job_control() {
  { sleep 0.1; exit 8; } &
  fg
}

# ERROR: says "no job control"
job_control2() {
  { sleep 0.1; exit 8; } &
  %1
}

"$@"
