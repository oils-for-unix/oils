#!/bin/bash
#
# Usage:
#   ./bubble_sort.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Fix the lexicographical comparisons!!!
LANG=C

main() {
  mapfile seq

  #echo ${#seq[@]}

  local changed=T
  while test -n "$changed"; do
    changed=''
    for (( i = 0; i < ${#seq[@]} - 1; ++i )); do

      # LANG=C required to make it behave like Python
      #if [[ ${seq[i]} > ${seq[i+1]} ]]; then

      if (( seq[i] > seq[i+1] )); then

        tmp=${seq[i+1]}
        seq[i+1]=${seq[i]}
        seq[i]=$tmp
        changed=T
      fi
    done
  done

  for line in "${seq[@]}"; do
    echo -n "$line"
  done
}

main "$@"
