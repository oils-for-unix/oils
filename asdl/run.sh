#!/usr/bin/env bash
#
# Automation for ASDL.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for clang

export PYTHONPATH='.:vendor/'

gen-mypy-asdl() {
  local name=$1
  shift
  local out=_devbuild/gen/${name}_asdl.py
  asdl/tool.py mypy asdl/${name}.asdl "$@" > $out
  wc -l $out
}

gen-typed-demo-asdl() { gen-mypy-asdl typed_demo; }
gen-shared-variant-asdl() { gen-mypy-asdl shared_variant; }
gen-typed-arith-asdl() {
  gen-mypy-asdl typed_arith 'asdl.typed_arith_abbrev'
}

unit() {
  # This test is for the code dynamically generated with py_meta.py.
  #test/unit.sh unit asdl/arith_ast_test.py

  # This test is for the metadata
  PYTHONPATH=. asdl/arith_generated_test.py "$@"
}

#
# Test specific schemas
#

arith-both() { py-cpp asdl/arith.asdl; }
osh-both() { py-cpp osh/osh.asdl; }

#
# Native Code
#

cxx() {
  #local CXX=c++ 
  local CXX=$CLANGXX
  local opt_flag='-O2'
  #local opt_flag='-O0'

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
  local schema=$1

  local name=$(basename $schema .asdl)

  # Generate C++ code
  asdl-cpp $schema _tmp/${name}.asdl.h

  local bin=_tmp/${name}_demo 
  cxx -I _tmp -o $bin asdl/${name}_demo.cc

  chmod +x $bin
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
  $CLANGXX -std='c++11' $opt_flag -I _tmp -o $out -S \
    -mllvm --x86-asm-syntax=intel asdl/arith_demo.cc
  #cat $out
}

llvm() {
  local opt_flag=${1:-'-O0'}
  local out=_tmp/arith_demo$opt_flag.ll 
  $CLANGXX -std='c++11' $opt_flag -I _tmp -o $out -S \
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

regress() {
  bin/osh -n configure > _tmp/configure-tree-abbrev.txt
  bin/osh --ast-format text -n configure > _tmp/configure-tree-full.txt
  { wc -l _tmp/configure*.txt
    md5sum _tmp/configure*.txt
  } #| tee _tmp/gold.txt
}

# To check if the lines go over 100 characters.
line-length-hist() {
  for f in _tmp/configure*.txt; do
    echo $f
    awk '{ print length($0) } ' $f | sort -n | uniq -c | tail 
  done
}

gen-cpp-demo() {
  local out=_tmp/typed_arith.asdl.h
  asdl/tool.py cpp asdl/typed_arith.asdl > $out

  local out2=_tmp/typed_demo.asdl.h
  asdl/tool.py cpp asdl/typed_demo.asdl > $out2

  wc -l $out $out2

  local bin=_tmp/typed_arith_demo 
  # uses typed_arith_asdl.h, runtime.h, hnode_asdl.h
  $CLANGXX -Wall -std=c++11 -I _tmp -I mycpp -I _devbuild/gen-cpp \
    -o $bin asdl/typed_arith_demo.cc
  $bin
}

"$@"
