#!/usr/bin/env bash
#
# Usage:
#   benchmarks/compute/word_split.sh <function name>

count_argv() {
  echo "COUNT = $#"
}

default_ifs() {
  local filename=$1

  count_argv $(cat $filename)
}

other_ifs() {
  local filename=$1

  # whitespace and non-whitespace
  export IFS=',: '
  count_argv $(cat $filename)
}

"$@"
