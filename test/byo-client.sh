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

source stdlib/osh/two.sh

detect() {
  if test $# -eq 0; then
    die "Expected argv to run"
  fi

  local out

  local status=0
  set +o errexit
  out=$(BYO_COMMAND=detect "$@" < /dev/null)
  status=$?
  set -o errexit

  if test $status -ne 66; then
    die "$(printf '%q ' "$@") doesn't implement BYO: expected status 66, got $status"
  fi

  # Verbose
  if false; then
    echo
    echo "BYO commands detected in $(printf '%q ' "$@"):"
    echo "$out"
  fi
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

  detect "$@"

  log '---'
  log "byo run-tests: $@"
  log


  # TODO:
  # --no-chdir       Change directory by default, but this option disables it
  # --no-stdout-log  stdout is not redirected to its own, named file
  # --max-jobs       Parallelism
  #
  # And how do we run test binaries that are just one big process?
  # - Python - inside a file, we probably don't have any tests to run in parallel
  # - C++    - ditto
  # - R      - we have a few unit tests
  #
  # So maybe we need BYO_LIST_TEST_BIN - list the test binaries?
  # Or mycpp/TEST.sh etc. should list them.   Yes that is true!
  # We can also list things to build.
  #
  # BYO_LIST_NINJA=1

  mkdir -p _tmp
  local tmp=_tmp/byo-list.txt

  # First list the tests
  BYO_COMMAND=list-tests "$@" > $tmp

  local i=0
  local status

  while read -r test_name; do

    echo "${TAB}${test_name}"

    set +o errexit
    BYO_COMMAND=run-test BYO_ARG="$test_name" "$@"
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
