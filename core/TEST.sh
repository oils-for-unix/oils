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
  for variant in asan ubsan; do
    run-one-test 'core/optview_test' '' $variant
    run-one-test 'core/runtime_asdl_test' '' $variant
  done
}

"$@"
