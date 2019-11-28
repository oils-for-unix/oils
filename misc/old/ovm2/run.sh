#!/bin/bash
#
# Demo of new OVM.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANGXX, etc

readonly FIB_I='opy/gold/fib_iterative.py'
readonly FIB_R='opy/gold/fib_recursive.py'

fib-dis() {
  local py=${1:-opy/gold/fib_iterative.py}
  bin/opyc dis $py
}

# TODO: Show graph output
fib-cfg() {
  bin/opyc cfg $FIB_I
}

gen-opcodes() {
  local out=_tmp/opcode.h
  PYTHONPATH=opy opy/lib/opcode_gen.py > $out
  echo "Wrote $out"
}

# Helper function.
run-ovm() {
  local bin=_tmp/ovm2

  #local SANITIZER_FLAGS='-fsanitize=address -g'
  local SANITIZER_FLAGS='-fsanitize=undefined -g'

  $CLANGXX -std=c++11 -Wall -I _tmp $SANITIZER_FLAGS -o $bin ovm2/main.cc
  set -x
  $bin "$@"
}

# TODO: Make this a test.  This tickled a memory error.
bad-oheap() {
  run-ovm opy/gold/hello_py3.py
}

# Python VM.
fib-byterun() {
  local bytecode=_tmp/fib_iterative.pyc
  bin/opyc compile $FIB_I $bytecode
  BYTERUN_SUMMARY=1 bin/opyc run $bytecode
}

# A stripped down Python version.
fib-ovm-prototype() {
  VM_SUMMARY=1 bin/opyc run-ovm $FIB_I
}

compile-iterative() {
  local out=_tmp/fib_iterative.ovm2
  bin/opyc compile-ovm $FIB_I $out
  ls -l $out
}

compile-recursive() {
  local out=_tmp/fib_recursive.ovm2
  bin/opyc compile $FIB_R _tmp/fib_recursive.pyc

  bin/opyc compile-ovm $FIB_R $out
  ls -l $out
}

# Run ovm2/main.cc
ovm2-main() {
  local py=${1:-$FIB_I}
  local bytecode=_tmp/$(basename $py '.py').ovm2
  bin/opyc compile-ovm $py $bytecode
  run-ovm $bytecode
}

# This works
hello-py3() {
  ovm2-main opy/gold/hello_py3.py
}

# This tickled a couple bugs
continue_() {
  ovm2-main opy/gold/continue_.py
}

# This works
fib-iterative() {
  ovm2-main $FIB_I
}

compare-compiler() {
  local py=$FIB_I
  bin/opyc compile $py _tmp/c2.pyc
  bin/opyc compile-ovm $py _tmp/ovm.pyc
  ls -l _tmp/{c2,ovm}.pyc

  # NOTE: The OVM versions fail because it's not valid bytecode.
  bin/opyc dis-md5 _tmp/c2.pyc
  bin/opyc dis-md5 _tmp/ovm.pyc

  bin/opyc dis _tmp/c2.pyc > _tmp/c2.txt
  bin/opyc dis _tmp/ovm.pyc > _tmp/ovm.txt
  diff -u _tmp/{c2,ovm}.txt
}

# NOTE: Iterative one isn't hooked up.
fib-recursive-callgraph() {
  PYTHONPATH=. CALLGRAPH=1 opy/gold/fib_recursive.py
}

"$@"
