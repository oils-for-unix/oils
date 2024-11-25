#!/usr/bin/env bash
#
# Usage:
#   benchmarks/callgrind.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build-and-run() {
  local sh=$1
  shift
  ninja $sh
  valgrind --tool=callgrind $sh "$@"
}

osh-run() {
  build-and-run _bin/cxx-dbg/osh "$@"
}

ysh-run() {
  build-and-run _bin/cxx-dbg/ysh "$@"
}

fib() {
  osh-run benchmarks/compute/fib.sh 10 44
}

pretty() {
  # takes 44 seconds to collect 1.6 MB of data
  # benchmarks/testdata/functions

  # Measure one of our own scripts
  # Takes 3 seconds
  time osh-run -n --ast-format text install
}

parse-cpython-configure() {
  # Goal: eliminate string slicing in this workload!  It should just be
  # creating fixed size Tokens, syntax.asdl nodes, and List<T>

  ysh-run -n --ast-format none Python-2.7.13/configure
}

json() {
  # 50 lines
  ysh-run test/bug-2123.ysh 50
}

with-callgrind() {
  local out_file=$1  # Ignored for now, same interface as with-cachegrind
  shift

  valgrind --tool=callgrind \
    "$@"
}

install-kcachegrind() {
  sudo apt-get install kcachegrind
}

file=$(basename $0)
if test $file = 'callgrind.sh'; then
  "$@"
fi
