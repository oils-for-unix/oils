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

"$@"
