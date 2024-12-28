#!/usr/bin/env bash
#
# Usage:
#   doc/error-catalog.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh
source test/sh-assert.sh  # _assert-sh-status

test-bool-operator() {
  if false; then
  # Doesn't give an error, because ! is used in Eggex
  _ysh-error-X 2 '
    if (!a || b && c) {
      echo no
    }
    '
  fi

  _ysh-error-X 2 '
    if (a || b && c) {
      echo no
    }
    '

  # Hm 'not' is a not a command - this is the 'boolstatus' problem
  _ysh-error-X 0 '
    if not test --dir a or test --dir b and test --dir c {
      echo no
    }
    '
}

#
# Entry Points (copied from test/ysh-parse-errors.sh)
#

soil-run-py() {
  run-test-funcs
}

soil-run-cpp() {
  ninja _bin/cxx-asan/osh
  OSH=_bin/cxx-asan/osh run-test-funcs
}

run-for-release() {
  run-other-suite-for-release error-catalog run-test-funcs
}

filename=$(basename $0)
if test $filename = 'error-catalog.sh'; then
  "$@"
fi

