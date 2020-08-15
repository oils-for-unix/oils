#!/bin/bash
#
# Show problems with errexit.
#
# Usage:
#   ./errexit-confusion.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

log() {
  echo "$@" 1>&2
}

die() {
  log "$@"
  exit 1
}

all-passing() {
  bin/osh --parse-and-print-arena foo  # This fails
  echo status=$?  # succeeds
}

# Copied from test/common.sh, to show the bug.

# The bug is that errexit is disabled within if.  Fixes tried:
#
# 1) Putting it on its own line: Then errexit triggers and you don't get the
# failure message.
#
# $func_name 2>&1
#
# 2) Disabling with
#
# set +o errexit
# $func_name 2>&1
# status=$?
# set -o errexit
#
# The problem is that the LAST line of all-passing succeeds.  We want it to
# fail in the middle.

run-other-suite-for-release-OLD() {
  local suite_name=$1
  local func_name=$2

  local out=_tmp/other/${suite_name}.txt
  mkdir -p $(dirname $out)

  echo
  echo "*** Running test suite '$suite_name' ***"
  echo

  if $func_name 2>&1; then
    echo
    log "Test suite '$suite_name' ran without errors.  Wrote $out"
  else
    echo
    die "Test suite '$suite_name' failed (running $func_name)"
  fi
}

# This is an awkward rewrite that works.
#
# Again the argv dispatch pattern saves the day!  You can test if a function
# failed while preserving its own errexit semantics!
#
# This composes!

run-other-suite-for-release-FIXED() {
  local suite_name=$1
  local func_name=$2

  local out=_tmp/other/${suite_name}.txt
  mkdir -p $(dirname $out)

  echo
  echo "*** Running test suite '$suite_name' ***"
  echo

  local status=0

  # Run in a separate SHELL, not just in a separate process.  ( $func_name )
  # doesn't work.
  $0 $func_name 2>&1 | tee $out || status=$?

  if test $status -eq 0; then
    echo
    log "Test suite '$suite_name' ran without errors.  Wrote '$out'"
  else
    echo
    die "Test suite '$suite_name' failed with status $status (running '$func_name', wrote '$out')"
  fi
}

run-for-release-OLD() {
  run-other-suite-for-release-OLD example-failure all-passing
}

run-for-release-FIXED() {
  run-other-suite-for-release-FIXED example-failure all-passing
}

# This could be a blog post:
#
# Conditions for the problem: 
# - using errexit (pipefail)
# - but you want to test if a FUNCTION failed.  If you disable errexit, you are
#   changing the semantics of the function!
#
# Solution:
#
# 1. Use the argv dispatch pattern
# 2. Use $0 $func_name || status=$?

# -----------------------------------------------------------------------------

# Another different that went away with the FIXED: A case where the stricter
# behavior of OSH's errexit was triggered.

# Can't set 'errexit' in a context where it's disabled (if, !, && ||,
# while/until conditions)
#
# Arguably this is exposing a bug?  errexit is already disabled?  May have to
# revisit this.

test-case-that-sets-errexit() {
  set +o errexit
  echo hi
}

osh-stricter() {
  run-other-suite-for-release-OLD osh-stricter test-case-that-sets-errexit
}

"$@"

