#!/usr/bin/env bash
#
# Test kernel state: which signals caught, ignored, etc.
#
# Copied from:
# https://unix.stackexchange.com/questions/85364/how-can-i-check-what-signals-a-process-is-listening-to
#
# Usage:
#   test/signal-state.sh <function name>

sigparse() {
  # Parse signal format in /proc.
  local hex_mask=$1

  local i=0

  # bits="$(printf "16i 2o %X p" "0x$1" | dc)" # variant for busybox

  # hex to binary.  Could also do this with Python.
  bits="$(printf 'ibase=16; obase=2; %X\n' "0x$hex_mask" | bc)"
  while test -n "$bits"; do
    i=$((i + 1))
    case "$bits" in
      *1)
        local sig_name=$(kill -l "$i")
        printf ' %s(%s)' "$sig_name" "$i"
        ;;
    esac
    bits="${bits%?}"
  done
}

report() {
  grep '^Sig...:' "/proc/$1/status" | while read state hex_mask; do
    printf "%s%s\n" "$state" "$(sigparse "$hex_mask")"
  done
}

do-child() {
  echo
  echo 'BACKGROUND CHILD'
  $sh -c 'script=$1; sleep 0.5 & { sleep 0.2; $script report $!; }' -- $0

  # TODO: I think we need a foreground child too.  It can just be a C program that
  # prints its own PID, and then waits for a byte on stdin before it exits?
}

compare-shells() {
  local do_child=${1:-}

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

    $sh -c 'script=$1; $script report $$' -- $0

    if test -n "$do_child"; then
      do-child $sh
    fi
  done

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
      (bash|bin/osh)
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
