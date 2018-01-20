#!/bin/bash
#
# Demo of traps.

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

"$@"
