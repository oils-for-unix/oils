#!/usr/bin/env bash
#
# Usage:
#   benchmarks/id-test.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/no-quotes.sh
source $LIB_OSH/task-five.sh

source benchmarks/id.sh
source build/dev-shell.sh  # python2

test-shell-prov() {
  shell-provenance-2 no-host 2022-12-29 _tmp/ \
    bin/osh
}

test-out-param() {
  local mylocal

  out-param mylocal
  nq-assert "$mylocal" = 'returned'

  echo "mylocal=$mylocal"
}

test-compiler-id() {
  dump-compiler-id $(which gcc)

  if test -f $CLANG; then
    dump-compiler-id $CLANG
  fi

  head _tmp/compiler-id/*/version.txt
}

soil-run() {
  devtools/byo.sh test $0
}

task-five "$@"
