#!/usr/bin/env bash
#
# Usage:
#   demo/background-status.sh <function name>

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

jobs_list() {
  local wait_one=${1:-}
  local in_order=${2:-}

  # Works with: dash/ash, bash mksh yash
  # Does NOT work with zsh
  #
  # OSH:
  # - jobs list looks weird
  # - extra stuff on stderr
  # but otherwise it works

  pids_down=''
  pids_up=''
  for i in 3 2 1; do
    { sleep $i; echo i=$i; exit $i; } &
    pid=$!

    pids_down="$pids_down $pid"
    pids_up="$pid $pids_up"
    echo "--- started $i"
    jobs -l
    echo

  done
  echo $pids_down
  echo $pids_up

  if test -n "$wait_one"; then
    if test -n "$in_order"; then
       pid_list=$pids_up
     else
       pid_list=$pids_down
    fi

    for p in $pid_list; do
      wait $p
      echo "--- pid $p --> status $?"

      # Hm dash/ash, and yash have a SIMILAR bug as OSH - status can be 127,
      # but only jobs -l
      #
      # bash and mksh do it correctly
      # zsh is messed up in other ways
      #
      # So this means that our way of handling failure only works in BASH/mksh,
      # not in POSIX shell!  There are similar problems with xargs.  Need a
      # blog post about this.
      jobs -l  # problem: this can "lose" exit codes
    done
  else
    wait $pid_down
  fi

  echo '--- done'
  jobs -l
  echo

  # the status is the last one, which is 2
  echo status=$?
}

"$@"
