#!/usr/bin/env bash
#
# Usage:
#   core/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh

unit() {
  run-one-test 'core/optview_test' '' asan
  echo

  run-one-test 'core/runtime_asdl_test' '' asan
  echo
}

"$@"
