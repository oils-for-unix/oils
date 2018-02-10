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

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
assert-deps() {
  bin/oilc deps | diff -u /dev/fd/3 - || fail
}

usage() {
	set +o errexit

  # missing required subcommand
  bin/oilc
  test $? -eq 2 || fail

  bin/oilc invalid
  test $? -eq 2 || fail

	# Syntax error
  echo '<' | bin/oilc deps 
  test $? -eq 2 || fail

	# File not found
  bin/oilc deps nonexistent.txt
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

	# Have to go inside a condition
	assert-deps <<EOF 3<<DEPS
if { grep foo bar; } then
	cat hi
fi
EOF
grep
cat
DEPS

	# g is used textually before defined, but that's OK
	assert-deps <<EOF 3<<DEPS
f() {
	g
}
g() {
	echo G
}
f
grep foo bar
EOF
grep
DEPS

	# g is used before defined, NOT OK
	assert-deps <<EOF 3<<DEPS
g
g() {
	echo G
}
grep foo bar
EOF
g
grep
DEPS
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
