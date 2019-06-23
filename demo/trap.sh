#!/bin/bash
#
# Demo of traps.

sigint-batch() {
  trap 'echo [got SIGINT]' INT
  echo "Registered SIGINT trap.  Run 'kill -INT $$' to see a message."
  sleep 5
}

sigterm-batch() {
  trap 'echo [got SIGTERM]' TERM
  echo "Registered SIGTERM trap.  Run 'kill -TERM $$' to see a message."
  sleep 5
}

# BUG: OSH gets two sigterms?
sigterm-then-kill-test() {
  local sh=${1:-bash}
  #### SIGTERM trap should run upon 'kill'
  $sh -c 'echo "> PID $$ started";
    echo $$ > _tmp/pid.txt;
    trap "echo SIGTERM" TERM;
    sleep 1;
    echo "< PID $$ done"' &

  sleep 0.5
  local pid=$(cat _tmp/pid.txt)
  echo "killing $pid"
  kill -TERM $pid
  wait
  echo status=$?
}

sigterm() {
  echo "sigterm [$@] $?"
  # quit the process -- otherwise we resume!
  exit
}

child() {
  trap 'sigterm x y' SIGTERM
  echo child
  for i in $(seq 5); do
    sleep 1
  done
}


readonly SH=bash
#readonly SH=dash  # bad trap
#readonly SH=mksh
#readonly SH=zsh

child2() {
  $SH -c '
  sigterm() {
    echo "sigterm [$@] $?"
    # quit the process -- otherwise we resume!
    exit
  }

  trap "sigterm x y" SIGTERM
  trap -p
  echo child
  for i in $(seq 5); do
    sleep 1
  done
  ' &
}

start-and-kill() {
  $0 child &

  #child2 

  echo "started $!"
  sleep 0.1  # a little race to allow things to be printed

  # NOTE: The process only dies after one second.  The "sleep 1" is run until
  # completion, and then the signal handler is run, which calls "exit".

  echo "killing $!"
  kill -s SIGTERM $!
  wait $!
  echo status=$?
}

num_signals=0

ignore-n-times() {
  (( num_signals++ ))

  if [[ $num_signals -le 2 ]]; then
    echo "Received signal $num_signals -- IGNORING"
  else
    echo "Removing this signal handler; next one will be the default"
    trap - TERM
  fi
}

# In bash: Run this and hit Ctrl-C four times to see the handler in action!
#
# NOTE: Ctrl-C doesn't work in Python because Python does stuff with SIGINT!
# We could disable KeyboardInterrupt entirely in the OVM build?  But still need
# the signal module!

sleep-and-ignore() {
  trap ignore-n-times TERM
  for i in $(seq 10); do
    echo $i
    sleep 0.2
  done
}

# NOTE: osh has EINTR problems here!
#
# File "/home/andy/git/oilshell/oil/bin/../core/process.py", line 440, in WaitUntilDone
# if not waiter.Wait():
# File "/home/andy/git/oilshell/oil/bin/../core/process.py", line 632, in Wait
#   pid, status = os.wait()
# OSError: [Errno 4] Interrupted system call

kill-sleep-and-ignore() {
  sleep-and-ignore &
  local last_pid=$!

  echo "Started $last_pid"

  # Hm sometimes the signal gets ignored?  You can't just kill it 3 times?
  for i in $(seq 5); do
    kill -s SIGTERM $last_pid
    echo kill status=$?
    sleep 0.1
  done

  wait
  echo wait status=$?
}

"$@"

