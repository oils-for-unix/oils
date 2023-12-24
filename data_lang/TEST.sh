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

  run-one-test 'data_lang/utf8_test' '' asan
  echo

  run-one-test 'data_lang/utf8_test' '' opt
  echo
}

"$@"
