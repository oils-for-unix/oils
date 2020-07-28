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

  if test "$1" = 'int'; then
    # Sort by integer value
    local changed=T
    while test -n "$changed"; do
      changed=''
      for (( i = 0; i < ${#seq[@]} - 1; ++i )); do
        if (( seq[i] > seq[i+1] )); then
          tmp=${seq[i+1]}
          seq[i+1]=${seq[i]}
          seq[i]=$tmp
          changed=T
        fi
      done
    done

  else
    # Sort by bytes
    local changed=T
    while test -n "$changed"; do
      changed=''
      for (( i = 0; i < ${#seq[@]} - 1; ++i )); do
        # LANG=C required here
        if [[ ${seq[i]} > ${seq[i+1]} ]]; then
          tmp=${seq[i+1]}
          seq[i+1]=${seq[i]}
          seq[i]=$tmp
          changed=T
        fi
      done
    done
  fi

  for line in "${seq[@]}"; do
    echo -n "$line"
  done
}

main "$@"
