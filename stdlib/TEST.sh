#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   stdlib/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

soil-run() {
  SH=bin/ysh
  test/byo-client.sh run-tests $SH stdlib/stream.ysh 

  test/byo-client.sh run-tests $SH stdlib/table.ysh 

  # I guess this needs tests, with an assertion library for stdout?

  # test/byo-client.sh run-tests $SH stdlib/two.sh 
}

"$@"
