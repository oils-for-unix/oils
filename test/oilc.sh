#!/bin/bash
#
# Usage:
#   ./oilc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: We need a common test framework for command-line syntax of bin/*.  The
# spec tests are doing that now with $SH.
# osh2oil should be oilc translate.

fail() {
  echo 'TEST FAILED'
  exit 1
}

usage() {
	set +o errexit

  # missing required subcommand
  bin/oilc
  test $? -eq 2 || fail

  bin/oilc invalid
  test $? -eq 2 || fail

  bin/oilc bin-deps
  test $? -eq 2 || fail

	return

	# Doesn't work yet
	echo --
  bin/oilc --help
  test $? -eq 0 || fail

	set -o errexit
}

deps() {
  bin/oilc deps $0
  test $? -eq 0 || fail
}

readonly -a PASSING=(
  usage
  deps
)

all-passing() {
  for t in "${PASSING[@]}"; do
    # fail calls 'exit 1'
    $t
    echo "OK  $t"
  done

  echo
  echo "All osh2oil tests passed."
}


"$@"
