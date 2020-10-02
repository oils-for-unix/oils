#!/usr/bin/env bash
#
# Show superlinear behavior in bash arrays.  Need pretty high N to start seeing
# it.
#
# Usage:
#   ./array_ref.sh MODE

set -o nounset
set -o pipefail
set -o errexit

main() {
  local mode=$1

  mapfile -t array

  local n=${#array[@]}
  local sum=0

  case $mode in
    linear)
      for (( i = 0; i < n; ++i )); do
        sum=$((sum + array[i]))
      done
      ;;

    random)
      for (( i = 0; i < n; ++i )); do
        # Super linear
        sum=$((sum + array[array[i]]))
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
