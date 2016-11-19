#!/bin/bash
#
# Usage:
#   ./regtest.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

banner() {
  echo ---
  echo "$@"
  echo ---
}

parse-one() {
  bin/osh --print-ast --no-exec "$@"
}

# TODO: Could do this in parallel
parse-files() {
  for f in "$@"; do
    banner $f
    parse-one $f
  done

  # 2961 lines
  wc -l "$@" | sort -n
  echo "DONE: Parsed ${#@} files"
}

oil-tests() {
  local num_failed=0
  for t in tests/*.test.sh; do
    banner $t
    if ! parse-one $t; then
      echo $t FAILED
      num_failed=$((num_failed + 1))
      if test $num_failed -ge 3; then
        echo "Quit after $num_failed failures"
        break
      fi
    fi
  done
}

# TODO: Move to blog/run.sh eventually.
oil-scripts() {
  local files=( *.sh {awk,demo,make,misc,regex,tools}/*.sh )
  parse-files "${files[@]}"
}

"$@"
