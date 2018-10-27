#!/bin/bash
#
# Test opyc from the 'outside'.
#
# Usage:
#   ./opyc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

readonly FILE=core/word_compile_test.py  # choose a small one

# NOTE: We don't really use the 'lex' action.
lex() {
  bin/opyc lex $FILE
}

dis() {
  bin/opyc dis $FILE
}

help() {
  # Doesn't work yet.
  bin/opyc --help
}

# This should be tested by opy/test.sh gold
run() {
  bin/opyc run opy/gold/fib_recursive.py
} 

readonly -a PASSING=(
  lex
  dis
  run
)

all-passing() {
  run-all "${PASSING[@]}"
}

run-for-release() {
  run-other-suite-for-release opyc all-passing
}


"$@"
