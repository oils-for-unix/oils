#!/usr/bin/env bash
#
# Usage:
#   ./TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh

unit() {
  run-one-test 'frontend/syntax_asdl_test' '' asan
}

"$@"
