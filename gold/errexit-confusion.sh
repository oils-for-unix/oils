#!/bin/bash
#
# Usage:
#   ./if.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

all-passing() {
  bin/osh --parse-and-print-arena foo
  echo $?
}

run-for-release() {
  run-other-suite-for-release example-failure all-passing
}

"$@"
