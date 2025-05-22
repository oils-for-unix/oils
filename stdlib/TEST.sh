#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   stdlib/TEST.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh

# TODO: byo-server.sh uses $BYO_COMMAND and $BYO_ARG
# I guess we need a YSH version then?  We could hack it with
# $(sh -c 'echo $BYO_COMMAND')

YSH='bin/ysh +o no_exported'

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

ysh-test() {
  local name=$1
  devtools/byo.sh test $YSH stdlib/ysh/$name-test.ysh
}

soil-run() {
  test-byo-protocol

  for name in def args list math quote yblocks; do
    ysh-test $name
  done

  devtools/byo.sh test $YSH stdlib/ysh/stream.ysh 
  devtools/byo.sh test $YSH stdlib/ysh/table.ysh 

  # special demo
  devtools/byo.sh test $YSH demo/rich-history.ysh

  # Run shebang, bash
  devtools/byo.sh test stdlib/osh/two-test.sh 
  devtools/byo.sh test stdlib/osh/no-quotes-test.sh 
  devtools/byo.sh test stdlib/osh/byo-server-test.sh 

  # Run with osh
  devtools/byo.sh test bin/osh stdlib/osh/two-test.sh 

}

"$@"
