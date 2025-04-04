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

      # Extra break statement!  Expensive in OSH!
      if test $j -eq $i; then
        break;
      fi
      continue
    done

    i=$(( i + 1 ))

  done

  echo "    sum=$sum"
}

inner_loop_return() {
  # relies on dynamic scope
  if true; then
    sum=$((sum + 1))

    # test extra return.  This is expensive in OSH!
    return
  fi
}

do_return() {
  local n=$1
  local i=0
  local sum=0

  while test $i -lt $n; do
    local j=0

    while test $j -lt $n; do
      j=$(( j + 1 ))
      inner_loop_return
    done

    i=$(( i + 1 ))

  done

  echo "    sum=$sum"
}

do_none() {
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
