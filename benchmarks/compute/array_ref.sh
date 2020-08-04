#!/bin/bash
#
# Shows some slight superlinear behavior in bash ararys?
#
# Usage:
#   ./reverse_sum.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

main() {
  local mode=$1

  mapfile -t array

  local n=${#array[@]}
  local i=$((n-1))
  local sum=0

  case $mode in
    linear)
      while test $i -ge 0; do
        sum=$((sum + array[i]))
        i=$((i - 1))
      done
      ;;

    random)
      while test $i -ge 0; do
        # Super linear
        sum=$((sum + array[array[i]]))
        i=$((i - 1))
      done
      ;;
  esac
  echo sum=$sum


  # This doesn't seem to defeat LASTREF?
  #array+=('X')
  #unset 'array[-1]'

  # neither does this
  #array[i]=$i
}

main "$@"
