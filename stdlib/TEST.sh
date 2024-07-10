#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   stdlib/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

YSH=bin/ysh

test-byo-protocol() {
  return

  # Usually the "BYO" command does this
  BYO_COMMAND=detect $YSH stdlib/table.ysh

  # TODO: need assertions here
  # assert status

  # assert-ok 'echo hi'
  # assert-stdout 'echo hi'
  # assert-fail 2 '(exit 2)'

  # I think we usually don't need this
  # assert-fail-stdout 2 '(exit 2)'

  BYO_COMMAND=z $YSH stdlib/table.ysh

  # missing
  BYO_COMMAND=run-test $YSH stdlib/table.ysh

  # TODO: test file with no tests
}

soil-run() {
  test-byo-protocol

  test/byo-client.sh run-tests $YSH stdlib/stream.ysh 

  test/byo-client.sh run-tests $YSH stdlib/table.ysh 

  # Run shebang, bash
  test/byo-client.sh run-tests stdlib/osh/two-test.sh 

  # Run with osh
  test/byo-client.sh run-tests bin/osh stdlib/osh/two-test.sh 
}

"$@"
