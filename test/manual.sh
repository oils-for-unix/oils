#!/usr/bin/env bash
#
# Manual tests
#
# Usage:
#   test/manual.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

readonly OSHRC=_tmp/manual-oshrc

setup() {
  cat >$OSHRC <<EOF
OILS_COMP_UI=nice
EOF
}

test-osh() {
  # Test it manually
  bin/osh --rcfile $OSHRC
}

test-ysh() {
  # same OSHRC?  Should it respect ENV.OILS_COMP_UI?
  bin/ysh --rcfile $OSHRC
}

no-home-dir() {
  ### Trying to tickle code path hit via oily-pine

  local sh=${1:-bash}
  # env -i gets rid of $HOME
  # unshare allows us to fake /etc/passwd
  env -i -- unshare --user --mount --map-root-user bash -c '
  sh=$1

  #set -x

  cmd="wc -l /etc/passwd; echo home \$HOME; echo tilde ~"

  whoami
  $sh -c "$cmd"
  echo

  #mount --bind /dev/null /etc/passwd
  echo "bob:x:1001:1001:Bob:/tmp:/bin/bash" > /tmp/passwd
  mount --bind /tmp/passwd /etc/passwd

  echo "bob:x:1001:h" > /tmp/group
  mount --bind /tmp/group /etc/group

  getent passwd bob
  su - bob
  #sudo -u bob bash

  #wc -l /etc/passwd
  #cat /etc/passwd

  #su -s $sh "#1001" -c "$cmd"
  #su -s $sh bob -c "$cmd"

  #setuidgid 1000 $sh -c "$cmd"

  #setpriv --reuid=1001 --regid=1001 --clear-groups -- $sh -c "$cmd"
  #sudo -u "#1001" $sh -c "$cmd"
  ' dummy0 $sh
}

# MANUAL TEST
# - external sleep can be killed with TERM, but it's unaffacted

start-sleep() {
  local osh=${1:-}  # start with bin/osh or _bin/cxx-asan/osh
  local do_trap=${2:-}

  local traps='
    trap "echo GOT-INT" INT
    trap "echo GOT-WINCH" WINCH
    trap "sleep 0.3" USR1
  '

  local code='sleep 100 & last_pid=$!; echo "pid $last_pid"; test/signal-state.sh report $last_pid; wait; echo "sleep done"'

  if test -n "$osh"; then
    code="builtin $code"
    if test -n "$do_trap"; then
      code="$traps $code"
    fi
    set -x
    $osh -c "$code"
  else
    sh -c "$code"
  fi
}

read-t-sleep() {
  echo "PID = $$"

  local do_trap=${1:-}

  if test -n "$do_trap"; then
    # bash does run signal handlers immediately
    # I can see int multiple times
    set -x
    trap 'echo GOT-INT' INT
    trap 'echo GOT-WINCH' WINCH

    # Test out remaining time logic.  It still sleeps for 5 seconds total.
    trap 'sleep 0.3' USR1
  fi
  # note:
  # - untrapped SIGINT/Ctrl-C interrupts it
  # - trapped SIGINT does not!

  # sleep
  read -t 5.0
}

task-five "$@"
