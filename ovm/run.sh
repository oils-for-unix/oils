#!/bin/bash
#
# Demo of new OVM.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly FIB_I=opy/gold/fib_iterative.py 

fib-dis() {
  local py=${1:-opy/gold/fib_iterative.py}
  bin/opyc dis $py
}

# TODO: Show graph output
fib-cfg() {
  bin/opyc cfg $FIB_I
}

# Helper function.
run-ovm() {
  local bin=_tmp/ovm_main

  # generate code
  PYTHONPATH=opy opy/lib/opcode_gen.py > _tmp/opcode.h

  cc -I _tmp -o $bin ovm/ovm_main.cc
  #cc -I ../Python-2.7.13/Include -o $bin ../ovm/ovm_main.cc
  set -x
  $bin "$@"
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

# Run ovm_main.cc
fib-ovm-native() {
  local bytecode=_tmp/fib_iterative.bytecode
  bin/opyc compile-ovm $FIB_I $bytecode
  run-ovm $bytecode
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
