#!/usr/bin/env bash
#
# Parse signal format in /proc.
#
# Copied from:
# https://unix.stackexchange.com/questions/85364/how-can-i-check-what-signals-a-process-is-listening-to
#
# Usage:
#   devtools/sigparse.sh <function name>

sigparse() {
  local i=0

  # bits="$(printf "16i 2o %X p" "0x$1" | dc)" # variant for busybox

  # hex to binary.  Could also do this with Python.
  bits="$(printf "ibase=16; obase=2; %X\n" "0x$1" | bc)"
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

compare-shells() {
  local -a shells=(bash dash mksh zsh osh)

  # Hm non-interactive shells have consistency.
  # SIGCHLD and SIGINT are caught in bash, dash, zsh, mksh.  mksh catches
  # several more.

  for sh in ${shells[@]}; do
    echo
    echo "---- $sh ----"
    echo

    $sh -c 'script=$1; $script report $$' -- $0
  done

  echo
  echo

  for sh in ${shells[@]}; do
    echo
    echo "---- $sh -i ----"
    echo

    # NOTE: If we don't set --rcfile, somehow this parent shell gets
    # [2]+ Stopped   devtools/sigparse.sh compare-shells
    # Seems related to spec test flakiness.

    local more_flags=''
    case $sh in
      (bash|osh)
        more_flags='--rcfile /dev/null'
        ;;
    esac

    $sh $more_flags -i -c 'script=$1; $script report $$' -- $0
  done
}

"$@"
