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

# User can set CXX=, like they can set CC= for oil.ovm
if test -z "${CXX:-}"; then
  if test -f $CLANGXX; then
    # note: Clang doesn't inline MatchOshToken!
    CXX=$CLANGXX
  else
    # equivalent of 'cc' for C++ langauge
    # https://stackoverflow.com/questions/172587/what-is-the-difference-between-g-and-gcc
    CXX='c++'
  fi
fi

CPPFLAGS="$CXXFLAGS -g -fsanitize=address"  # for debugging tests
export ASAN_OPTIONS='detect_leaks=0'  # like build/mycpp.sh

export PYTHONPATH='.:vendor/'

gen-mypy-asdl() {
  local name=$1
  shift
  local out=_devbuild/gen/${name}_asdl.py
  asdl/tool.py mypy asdl/${name}.asdl "$@" > $out
  wc -l $out
}

gen-typed-demo-asdl() {
  gen-mypy-asdl demo_lib  # dependency
  gen-mypy-asdl typed_demo
}
gen-shared-variant-asdl() { gen-mypy-asdl shared_variant; }
gen-typed-arith-asdl() {
  gen-mypy-asdl typed_arith 'asdl.typed_arith_abbrev'
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

a4() {
  local data=_tmp/a4.bin
  asdl-arith-encode 'array[99]' $data
  gdb-trace _tmp/typed_arith_demo $data

  asdl-arith-encode 'array[5:10] * 5' $data
  gdb-trace _tmp/typed_arith_demo $data
}

# http://stackoverflow.com/questions/22769246/disassemble-one-function-using-objdump
# It would be nice to disassemble a single function.

disassemble() {
  local opt_flag=${1:-'-O0'}
  local out=_tmp/typed_arith_demo$opt_flag.S 
  $CLANGXX -std='c++11' $opt_flag -I _tmp -o $out -S \
    -mllvm --x86-asm-syntax=intel asdl/typed_arith_demo.cc
  #cat $out
}

llvm() {
  local opt_flag=${1:-'-O0'}
  local out=_tmp/typed_arith_demo$opt_flag.ll 
  $CLANGXX -std='c++11' $opt_flag -I _tmp -o $out -S \
    -emit-llvm asdl/typed_arith_demo.cc
  #cat $out
}

# With -O0, you can see all the functions.  With -O2, they ARE inlined.
objdump-arith() {
  # NOTE: This doesn't take into account different optimization levels
  objdump -d _tmp/typed_arith_demo | grep '^0'
}
# https://sourceware.org/ml/binutils/2010-04/msg00447.html
# http://stackoverflow.com/questions/4274804/query-on-ffunction-section-fdata-sections-options-of-gcc
# Hm you can force a function.  Write it inline with typed_arith_demo.cc then.

# TODO: Is there a pattern we can grep for to test if ANY accessor was NOT
# inlined?  Demangle names I guess.
nm-arith() {
  nm _tmp/typed_arith_demo
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

gen-cpp-errors() {

  # This doesn't produce an error, even though 'int?' isn't representable in C++
  cat >_tmp/bad.asdl <<EOF
module bad {
  foo = (int? x, int y)
}
EOF

  asdl/tool.py cpp _tmp/bad.asdl _tmp/asdl_bad

  ls -l _tmp/asdl_bad*
}

gen-cpp-test() {
  local prefix=_tmp/typed_arith_asdl
  asdl/tool.py cpp asdl/typed_arith.asdl $prefix

  local prefix2=_tmp/demo_lib_asdl
  asdl/tool.py cpp asdl/demo_lib.asdl $prefix2

  local prefix3=_tmp/typed_demo_asdl
  asdl/tool.py cpp asdl/typed_demo.asdl $prefix3

  # Hack the enables a literal in asdl/gen_cpp_test
  local orig=_tmp/typed_demo_asdl.h
  local tmp=_tmp/tt
  sed 's/SetToArg_(S/constexpr SetToArg_(S/g' $orig > $tmp
  diff -u $orig $tmp || true
  cp -v $tmp $orig

  wc -l $prefix* $prefix2*

  local bin=_tmp/gen_cpp_test

  # BUG: This doesn't link without the translation of asdl/runtime.py.

  # uses typed_arith_asdl.h, runtime.h, hnode_asdl.h, asdl_runtime.h
  $CXX $CPPFLAGS \
    -I _tmp -I mycpp -I _build/cpp -I cpp \
    -o $bin \
    asdl/gen_cpp_test.cc \
    asdl/runtime.cc \
    mycpp/mylib.cc \
    _build/cpp/hnode_asdl.cc \
    _tmp/typed_arith_asdl.cc \
    _tmp/typed_demo_asdl.cc 

  #gdb -batch -ex run -ex bt --args $bin "$@"
  $bin "$@"
}

"$@"
