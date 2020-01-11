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

_run-test() {
  local name=$1

  bin/osh -O oil:basic -- $0 $name
  local status=$?
  if test $status -ne 1; then
    die "Expected status 1, got $status"
  fi
}

run-all-with-osh() {
  _run-test regex_literals

  return 0  # success
}

run-for-release() {
  run-other-suite-for-release oil-runtime-errors run-all-with-osh
}

"$@"
