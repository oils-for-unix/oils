#!/bin/bash
#
# Automation for ASDL.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Run unit tests.
unit() {
  asdl/arith_ast_test.py
  asdl/py_meta_test.py
  asdl/encode_test.py
  return
  for t in asdl/*_test.py; do
    echo -----
    echo $t
    echo -----

    $t
  done
}

asdl-arith-encode() {
  local expr="$1"
  local out=${2:-_tmp/arith.bin}
  asdl/asdl_demo.py arith-encode "$expr" $out
  ls -l $out
  hexdump $out
}

asdl-py() {
  local schema=$1
  asdl/asdl_demo.py py $schema
}

asdl-cpp() {
  local schema=${1:-asdl/arith.asdl}
  local src=${2:-_tmp/arith.asdl.h}
  asdl/gen_cpp.py cpp $schema > $src
  ls -l $src
  wc -l $src
}

py-cpp() {
  local schema=${1:-asdl/arith.asdl}
  asdl-py $schema
  asdl-cpp $schema _tmp/$(basename $schema).h
}

#
# Test specific schemas
#

arith-both() {
  py-cpp asdl/arith.asdl
}

osh-both() {
  py-cpp asdl/osh.asdl
}

#
# Native Code
#

readonly CLANG=~/install/clang+llvm-3.8.0-x86_64-linux-gnu-ubuntu-14.04/bin/clang++

cxx() {
  #local CXX=c++ 
  local CXX=$CLANG
  local opt_flag='-O2'
  local opt_flag='-O0'

  # -Winline
  # http://stackoverflow.com/questions/10631283/how-will-i-know-whether-inline-function-is-actually-replaced-at-the-place-where

  $CXX -Winline $opt_flag -std=c++11 "$@"
}

# http://www.commandlinefu.com/commands/view/6004/print-stack-trace-of-a-core-file-without-needing-to-enter-gdb-interactively
# http://stackoverflow.com/questions/4521015/how-to-pass-arguments-and-redirect-stdin-from-a-file-to-program-run-in-gdb
gdb-trace() {
  # -args goes before the executable
  gdb -batch -ex "run" -ex "bt" -args "$@" 2>&1 
}

build-demo() {
  local name=$1

  local schema=asdl/${name}.asdl

  # Generate C++ code
  asdl-cpp $schema _tmp/${name}.asdl.h

  local bin=_tmp/${name}_demo 
  cxx -I _tmp -o $bin asdl/${name}_demo.cc

  chmod +x $bin
}

arith-demo() {
  local name=arith
  local data=_tmp/${name}.bin

  # Write a binary
  asdl-arith-encode '7 + 9' $data

  local bin=_tmp/${name}_demo 

  build-demo $name $bin

  set -x
  gdb-trace $bin $data
  #$bin $data 
}

osh-demo() {
  build-demo osh
}

a2() {
  local data=_tmp/a2.bin
  asdl-arith-encode 'foo + 99 - f(1,2,3+4) * 123' $data
  _tmp/arith_demo $data
}

a3() {
  local data=_tmp/a3.bin
  asdl-arith-encode 'g(x,2)' $data
  gdb-trace _tmp/arith_demo $data
}

a4() {
  local data=_tmp/a4.bin
  asdl-arith-encode 'array[99]' $data
  gdb-trace _tmp/arith_demo $data

  asdl-arith-encode 'array[5:10] * 5' $data
  gdb-trace _tmp/arith_demo $data
}

# http://stackoverflow.com/questions/22769246/disassemble-one-function-using-objdump
# It would be nice to disassemble a single function.

disassemble() {
  local opt_flag=${1:-'-O0'}
  local out=_tmp/arith_demo$opt_flag.S 
  $CLANG -std='c++11' $opt_flag -I _tmp -o $out -S \
    -mllvm --x86-asm-syntax=intel asdl/arith_demo.cc
  #cat $out
}

llvm() {
  local opt_flag=${1:-'-O0'}
  local out=_tmp/arith_demo$opt_flag.ll 
  $CLANG -std='c++11' $opt_flag -I _tmp -o $out -S \
    -emit-llvm asdl/arith_demo.cc
  #cat $out
}

# With -O0, you can see all the functions.  With -O2, they ARE inlined.
objdump-arith() {
  # NOTE: This doesn't take into account different optimization levels
  objdump -d _tmp/arith_demo | grep '^0'
}
# https://sourceware.org/ml/binutils/2010-04/msg00447.html
# http://stackoverflow.com/questions/4274804/query-on-ffunction-section-fdata-sections-options-of-gcc
# Hm you can force a function.  Write it inline with arith_demo.cc then.

# TODO: Is there a pattern we can grep for to test if ANY accessor was NOT
# inlined?  Demangle names I guess.
nm-arith() {
  nm _tmp/arith_demo
}

opt-stats() {
  wc -l _tmp/*.S
  echo
  wc -l _tmp/*.ll
  echo
  md5sum _tmp/*.S
  echo
  md5sum _tmp/*.ll
}

compare-opts() {
  # http://stackoverflow.com/questions/15548023/clang-optimization-levels
  # Says -Os is identical to -O2?  But not according to my test!

  for opt in -Os -O0 -O1 -O2 -O3 -O4; do
    echo $opt
    disassemble $opt
    llvm $opt
  done
  opt-stats
}

count() {
  wc -l asdl/{asdl,py_meta,gen_cpp,encode}.py 
  echo

  wc -l asdl/{py_meta,encode}_test.py
  echo

  wc -l asdl/arith_parse*.py asdl/tdop.py asdl/arith_ast.py asdl/asdl_demo.py
  echo

  wc -l asdl/*.cc 
  echo

  wc -l asdl/*.asdl
  echo
}

"$@"
