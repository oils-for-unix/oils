#!/usr/bin/env bash
#
# Test opyc from the 'outside'.
#
# Usage:
#   test/opyc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

readonly FILE=osh/word_compile_test.py  # choose a small one

# NOTE: We don't really use the 'lex' action.
test-lex() {
  bin/opyc lex $FILE
}

test-ast() {
  bin/opyc ast $FILE
}

test-symbols() {
  bin/opyc symbols $FILE
}

test-cfg() {
  bin/opyc cfg $FILE
}

# This should be tested by opy/TEST.sh gold
test-run() {
  bin/opyc run opy/gold/fib_recursive.py
} 

test-dis() {
  bin/opyc dis $FILE
}

test-parse() {
  bin/opyc parse $FILE
}

test-compile() {
  bin/opyc compile $FILE _tmp/opyc-compile-1
  bin/opyc compile --emit-docstring=0 $FILE _tmp/opyc-compile-2
  ls -l _tmp/opyc-compile-*
}

test-parse-with() {
  local -a exprs

  readonly TESTDATA=pgen2/testdata

  exprs=(
    # second alternative
    'a'
    'a = 3'
    'unsigned int a'
    'unsigned unsigned int a'
    'unsigned unsigned b c'
    # It correctly detects these as parse errors
    #'unsigned unsigned b'
    #'a = b'
  )

  for e in "${exprs[@]}"; do
    echo
    echo "$e"
    bin/opyc parse-with $TESTDATA/ll-star.grammar paper_input "$e"
  done

  exprs=(
    # second alternative
    'unsigned foo(arg);'
    'unsigned foo(arg) { body }'
    # It correctly detects these as parse errors
    #'unsigned foo(arg)'
  )
  for e in "${exprs[@]}"; do
    echo
    echo "$e"
    bin/opyc parse-with $TESTDATA/ll-star.grammar method_input "$e"
  done

  exprs=(
    '1 + 2'
    'a - 42'
    'if a - 42'
  )
  for e in "${exprs[@]}"; do
    echo
    echo "$e"
    bin/opyc parse-with $TESTDATA/minimal.grammar eval_input "$e"
  done

  echo
  echo 'DONE'
}

FAIL-test-help() {
  # Doesn't work yet.
  bin/opyc --help
}

run-for-release() {
  run-other-suite-for-release opyc run-test-funcs
}

soil-run() {
  make _build/opy/py27.grammar.marshal

  run-test-funcs
}

"$@"
