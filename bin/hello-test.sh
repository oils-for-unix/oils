#!/usr/bin/env bash
#
# Test bin/hello 
#
# (Extracted from build/native.sh, xshar-test embed it, and we don't want extra
# deps now)
#
# Usage:
#   bin/hello-test.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/task-five.sh
source $LIB_OSH/no-quotes.sh

test-hello() {
  local hello=_bin/cxx-asan/bin/hello.mycpp

  ninja $hello

  echo "*** Testing $hello"

  local status stdout
  nq-capture status stdout \
    $hello a b c d
  nq-assert 5 = $status
}

soil-run() {
  ### soil/worker.sh call this

  devtools/byo.sh test $0
}

task-five "$@"
