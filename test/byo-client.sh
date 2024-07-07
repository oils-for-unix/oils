#!/usr/bin/env bash
#
# Run test executables that obey the BYO protocol.
#
# TODO: doc/byo.md
#
# Usage:
#   test/byo-client.sh run-tests ARGS...
#
# The ARGS... are run with an environment variable, e.g.
#
#   ./myscript.py
#   python3 ./myscript.py
#   ./myscript.sh
#   dash ./myscript.sh
#   osh ./myscript.sh
#
# The client creates a clean process state and directory state for each tests.

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

readonly TAB=$'\t'

log() {
  echo "$0: $@" >&2
}

die() {
  log "$@"
  exit 1
}

run-tests() {
  # argv is the command to run, like bash foo.sh
  #
  # It's an array rather than a single command, so you can run the same scripts
  # under multiple shells:
  #
  #   bash myscript.sh
  #   osh myscript.sh

  if test $# -eq 0; then
    die "Expected argv to run"
  fi

  # TODO:
  # - change directories
  # - provide option to redirect stdout

  mkdir -p _tmp
  local tmp=_tmp/byo-list.txt

  # First list the tests
  BYO_LIST_TESTS=1 "$@" > $tmp

  local i=0
  local status

  while read -r test_name; do

    echo "${TAB}${test_name}"

    set +o errexit
    BYO_RUN_TEST="$test_name" "$@"
    status=$?
    set -o errexit

    if test $status -eq 0; then
       echo "${TAB}OK"
    else
      echo "${TAB}FAIL with status $status"
      exit 1
    fi

    i=$(( i + 1 ))
  done < $tmp

  echo
  echo "$0: $i tests passed."
}

# TODO:
# BYO_PROBE=1
#
# must print capabilities
#
# - testing - success/fail
# - benchmarks - output TSV file I think?  Or a directory of TSV files?
#   - BYO_RESULTS
# - shell auto-completion

"$@"
