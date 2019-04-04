#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

export PYTHONPATH=.

# OHeap V1 no longer works, but I'm saving the code for reference.
asdl-oheap-cpp() {
  local schema=${1:-asdl/typed_arith.asdl}
  local src=${2:-_tmp/typed_arith.asdl.h}
  misc/old/gen_oheap_cpp.py cpp $schema > $src
  ls -l $src
  wc -l $src
}

#
# UNTESTED
#

smoke-test() {
  local arith_expr=${1:-"2 + 3 * 4"}
  # Print Schema (asdl_.py, py_meta.py)
  asdl-py asdl/arith.asdl

  # Parse real values and pretty print (format.py)
  asdl-arith-format "$arith_expr"

  # encode.py
  asdl-arith-oheap "$arith_expr"
}

asdl-arith-oheap() {
  local arith_expr=${1:-"1 + 2 * 3"}
  local name=arith
  local data=_tmp/${name}.bin

  # Write a binary
  asdl-arith-encode "$arith_expr" $data

  local bin=_tmp/${name}_demo 

  build-demo asdl/arith.asdl

  set -x
  #gdb-trace $bin $data
  $bin $data 
}

# TODO: How big is oheap vs. the virtual memory size?

osh-demo() {
  local name=osh
  local data=_tmp/${name}.bin

  local code='echo hi; echo bye  # comment' 
  local code='declare -r -x foo'  # for testing repeated array
  local code='echo x && echo y && echo z || die'  # for && || chains
  #local code='echo $(( 2 + 3 ))'
  #local code='echo $(( -2 * -3 ))'  # test negative integers
  bin/osh -n --ast-format oheap -c "$code" > $data

  ls -l $data

  core/id_kind_gen.py cpp > _tmp/id_kind.h
  build-demo osh/osh.asdl

  local bin=_tmp/${name}_demo 
  $bin $data
}

"$@"
