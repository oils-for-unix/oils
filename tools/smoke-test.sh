#!/usr/bin/env bash
#
# Usage:
#   tools/lint-test.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh
source $LIB_OSH/no-quotes.sh

source test/common.sh  # run-test-funcs

test-lint-backticks() {
  local status stdout
  nq-capture status stdout \
    $OSH --tool lint -c 'a=`echo hi`'

  nq-assert $status -eq 0

  # TODO: stdout should contain a message
  echo stdout=$stdout
}

test-deps() {
  local status stdout
  nq-capture status stdout \
    $OSH --tool deps regtest/aports-html.sh

  nq-assert $status -eq 0

  # TODO: print out the assertion

  # This works somewhat!  Prints awk/ssh/wget/unzip, etc.
  # But it probably doesn't follow 'source' ?

  echo "stdout=$stdout"
}

test-fmt() {
  local status stdout

  # Bad indenting
  nq-capture status stdout \
    $OSH --tool fmt -c 'echo 1
  echo 2
echo3'

  nq-assert $status -eq 0

  echo "stdout=$stdout"
}

soil-run() {
  run-test-funcs
}

task-five "$@"
