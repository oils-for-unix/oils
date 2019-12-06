#!/bin/bash
#
# Usage:
#   ./oil-runtime-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh

regex_literals() {

  var sq = / 'foo'+ /

  var dq = / "foo"+ /

  var literal = 'foo'
  var svs = / $literal+ /
  var bvs = / ${literal}+ /

  # All of these fail individually.
  # NOTE: They are fatal failures so we can't catch them?  It would be nicer to
  # catch them.

  #echo $sq
  #echo $dq
  #echo $svs
  echo $bvs
}

_run_test() {
  local t=$1

  echo -- "--------"
  echo -- "    CASE: $t"
  # Run in subshell so the whole thing doesn't exit
  ( $t )
  echo -- "    STATUS: $?"
  echo
}

all() {
  _run_test regex_literals
}

run-all-with-osh() {
  bin/osh -O oil:basic -- $0 all
}

run-for-release() {
  run-other-suite-for-release oil-runtime-errors run-all-with-osh
}

"$@"
