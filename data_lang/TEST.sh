#!/usr/bin/env bash
#
# Usage:
#   data_lang/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh  # python3 in $PATH
source test/common.sh      # run-one-test

unit() {
  ### Run unit tests

  for variant in asan opt; do
    # This test needs to be faster
    run-one-test 'data_lang/utf8_test' '' $variant
    echo
  done

  for variant in asan ubsan; do
    run-one-test 'data_lang/j8_test' '' $variant
    echo
  done

  for variant in asan ubsan; do
    run-one-test 'data_lang/j8_libc_test' '' $variant
    echo
  done
}

"$@"
