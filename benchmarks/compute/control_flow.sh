#!/usr/bin/env bash
#
# Usage:
#   benchmarks/compute/control_flow.sh <function name>

# Each of these 3 functions is a double loop that computes roughly n^2.

do_continue() {
  local n=$1
  local i=0
  local sum=0

  while test $i -lt $n; do
    local j=0

    while test $j -lt $n; do
      j=$(( j + 1 ))
      sum=$((sum + 1))

      # This NO-OP continue penalizes OSH!  It's almost as fast as bash without
      # it, but them becomes twice as slow.

      continue
    done

    i=$(( i + 1 ))

  done

  echo "    sum=$sum"
}

do_break() {
  local n=$1
  local i=0
  local sum=0

  while test $i -lt $n; do
    local j=0

    while test $j -lt $n; do
      j=$(( j + 1 ))
      sum=$((sum + 1))

      # Extra break statement!
      if test $j -eq $i; then
        break;
      fi
      continue
    done

    i=$(( i + 1 ))

  done

  echo "    sum=$sum"
}



do_neither() {
  local n=$1
  local i=0
  local sum=0

  while test $i -lt $n; do
    local j=0

    while test $j -lt $n; do
      j=$(( j + 1 ))
      sum=$((sum + 1))
    done

    i=$(( i + 1 ))

  done

  echo "    sum=$sum"
}

"$@"
