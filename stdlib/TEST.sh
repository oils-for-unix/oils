#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   stdlib/TEST.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh

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

  devtools/byo.sh test $YSH stdlib/ysh/def-test.ysh
  #return
  devtools/byo.sh test $YSH stdlib/ysh/args-test.ysh
  devtools/byo.sh test $YSH stdlib/ysh/list-test.ysh
  devtools/byo.sh test $YSH stdlib/ysh/math-test.ysh

  devtools/byo.sh test $YSH stdlib/ysh/yblocks-test.ysh 
  devtools/byo.sh test $YSH stdlib/ysh/stream.ysh 
  devtools/byo.sh test $YSH stdlib/ysh/table.ysh 

  # Run shebang, bash
  devtools/byo.sh test stdlib/osh/two-test.sh 
  devtools/byo.sh test stdlib/osh/no-quotes-test.sh 
  devtools/byo.sh test stdlib/osh/byo-server-test.sh 

  # Run with osh
  devtools/byo.sh test bin/osh stdlib/osh/two-test.sh 

}

"$@"
