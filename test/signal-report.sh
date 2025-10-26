#!/bin/sh
#
# Show signal state in a shell
#
# Copied from:
# https://unix.stackexchange.com/questions/85364/how-can-i-check-what-signals-a-process-is-listening-to
#
# Usage:
#   ./signal-report.sh <function name>

set -o nounset
set -o errexit
#set -o pipefail

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
  local do_trap=${1:-}

  local pid=$$
  echo "PID $pid"

  if test -n "$do_trap"; then
    # trap '' sets SIG_IGN
    trap '' USR2
    #echo '    Ignoring USR2'
    trap 
    echo
  fi


  if false; then
    # raw
    grep '^SigIgn:' "/proc/$pid/status" 
  else
    grep '^Sig...:' "/proc/$pid/status" | while read state hex_mask; do
      printf "%s%s\n" "$state" "$(sigparse "$hex_mask")"
    done
  fi
}

"$@"
