#!/bin/bash
#
# Usage:
#   ./opy.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

usage() {
  set +o errexit

  bin/opy_.py
  test $? -eq 2 || fail

  bin/opy_.py --version
  test $? -eq 0 || fail

  #bin/opy
  #test $? -eq 2 || fail

  bin/opyc
  test $? -eq 2 || fail

  bin/opyc invalid
  test $? -eq 2 || fail

  # TODO: --help, --version everywhere.

  #bin/opy_.py --help
  #test $? -eq 0 || fail

  #bin/opy --help
  #test $? -eq 0 || fail

  #bin/opy --version
  #test $? -eq 0 || fail

  bin/opyc --help
  test $? -eq 0 || fail

  #bin/opyc --version
  #test $? -eq 0 || fail
}

readonly -a PASSING=(
  usage
)

# TODO: Consolidate this

all-passing() {
  for t in "${PASSING[@]}"; do
    # fail calls 'exit 1'
    $t
    echo "OK  $t"
  done

  echo
  echo "All $0 tests passed."
}


"$@"
