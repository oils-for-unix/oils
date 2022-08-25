#!/usr/bin/env bash
#
# Junk drawer for ASDL.
#
# Usage:
#   asdl/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

source build/common.sh

export PYTHONPATH='.:vendor/'

#
# Native Code
#

# http://www.commandlinefu.com/commands/view/6004/print-stack-trace-of-a-core-file-without-needing-to-enter-gdb-interactively
# http://stackoverflow.com/questions/4521015/how-to-pass-arguments-and-redirect-stdin-from-a-file-to-program-run-in-gdb
gdb-trace() {
  # -args goes before the executable
  gdb -batch -ex "run" -ex "bt" -args "$@" 2>&1 
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

  asdl/asdl_main.py cpp _tmp/bad.asdl _tmp/asdl_bad

  ls -l _tmp/asdl_bad*
}

"$@"
