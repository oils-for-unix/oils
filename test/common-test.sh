#!/usr/bin/env bash
#
# Usage:
#   test/common-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

test-run-task-with-status() {
  run-task-with-status _tmp/status.txt sh -c 'sleep 0.1; exit 1' || true
  cat _tmp/status.txt
  test "$(wc -l < _tmp/status.txt)" = '1' || die "Expected only one line"
}

all() {
  run-test-funcs
}

"$@"
