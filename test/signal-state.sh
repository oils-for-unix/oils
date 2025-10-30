#!/usr/bin/env bash
#
# Test kernel state: which signals caught, ignored, etc.
#
# Usage:
#   test/signal-state.sh <function name>

do_child() {
  echo
  echo 'BACKGROUND CHILD'
  $sh -c 'script=$1; sleep 0.5 & { sleep 0.2; $script report $!; }' -- $0

  # TODO: I think we need a foreground child too.  It can just be a C program that
  # prints its own PID, and then waits for a byte on stdin before it exits?
}

compare-shells() {
  local do_child=${1:-}
  local do_trap=${2:-}

  local osh_cpp=_bin/cxx-dbg/osh
  ninja $osh_cpp

  local -a shells=(bash dash mksh zsh bin/osh $osh_cpp)

  # Hm non-interactive shells have consistency.
  # SIGCHLD and SIGINT are caught in bash, dash, zsh, mksh.  mksh catches
  # several more.

  for sh in ${shells[@]}; do
    echo
    echo "---- $sh ----"
    echo

    #echo "Parent PID $$"
    #grep '^SigIgn:' "/proc/$$/status" 
    #trap

    $sh test/signal-report.sh report "$do_trap"

    if test -n "$do_child"; then
      do_child $sh
    fi
  done
}

old() {
  echo
  echo

  # -i messes things up
  return

  for sh in ${shells[@]}; do
    echo
    echo "---- $sh -i ----"
    echo

    # NOTE: If we don't set --rcfile, somehow this parent shell gets
    # [2]+ Stopped   devtools/sigparse.sh compare-shells
    # Seems related to spec test flakiness.

    local more_flags=''
    case $sh in
      bash|bin/osh)
        more_flags='--rcfile /dev/null'
        ;;
    esac

    $sh $more_flags -i -c 'script=$1; $script report $$' -- $0

    if test -n "$do_child"; then
      do-child $sh
    fi
  done
}

"$@"
