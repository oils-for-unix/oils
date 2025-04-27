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
  local start_what=${1:-process}  # or pipeline
  local wait_style=${2:-all}

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
    case $start_what in 
      process)
        { sleep $i; echo i=$i; exit $i; } &
        pid=$!
        ;;
      pipeline)
        sleep $i | echo i=$i | ( exit $i ) &
        pid=$!
        ;;
      *)
        echo "Invalid arg '$start_what'" >&2
        return 1
        ;;
    esac

    pids_down="$pids_down $pid"
    pids_up="$pid $pids_up"
    echo "--- started $i"
    jobs -l
    echo

  done
  echo $pids_down
  echo $pids_up

  pid_list=''
  case $wait_style in
    pass_all)
      wait $pids_down
      ;;
    all)
      wait
      ;;
    next)
      for i in $pids_down; do
        wait -n
        echo "--- wait -n --> status=$?"
      done
      ;;
    down_one)
       pid_list=$pids_down
      ;;
    up_one)
       pid_list=$pids_up
      ;;
    down_jobs)
       pid_list='%3 %2 %1'
      ;;
    up_jobs)
       pid_list='%1 %2 %3'
      ;;
    none)
      echo 'Not waiting'

      # When can we remove the (pid -> status) mapping?
      # If we don't wait, We never do.  The shell exists, and the processes
      # keep going!
      # So the actual 'wait' command is the thing that removes records, NOT
      # process death.

      # Some dummy processes
      for i in 1 2 3; do
        sleep 0.01
      done
      ;;
    *)
      echo "Invalid wait style '$wait_style'" >& 2
      wait
      return 1
  esac

  case $wait_style in
    down_*|up_*)
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
      ;;
  esac

  echo '--- Jobs after waiting'
  jobs -l
  echo '---'

  # the status is the last one, which is 2
  echo status=$?
}

stopped_process() {
  sleep 5 &
  local pid=$!

  set -x
  sleep 0.1
  kill -STOP $pid

  #kill -TERM $pid

  # wait is only for exiting
  wait $pid
  echo status=$?
}

# from test/process-table-portable.sh
readonly PS_COLS='pid,ppid,pgid,sid,tpgid,comm'

last_id() {
  sleep 1 | cat &

  # But what's the progress group leader?
  #
  # In non-interactive shell, it's the shell itself
  # In an interactive shell, it's the FIRST part of the pipeline.
  #
  # This is super confusing.
  # So when you do wait $! on the LAST part of the pipeline, are you waiting on
  # an individual process, or a JOB that's the pipeline.  Gah
  ps -o $PS_COLS

  # 6277 is the last part of the pipeline!  You can 'wait' on it?
  pid=$!
  jobs -l
  echo pid=$pid
  set -x
  wait $pid

}

"$@"
