#!/usr/bin/env bash
#
# Usage:
#   benchmarks/callgrind.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build-and-run() {
  # Hm dbg build seems to give more exact info
  local osh=_bin/cxx-dbg/osh
  #local osh=_bin/cxx-opt/osh

  ninja $osh

  valgrind --tool=callgrind \
    $osh "$@"
}

fib() {
  build-and-run benchmarks/compute/fib.sh 10 44
}

parse-cpython-configure() {
  build-and-run -n --ast-format none Python-2.7.13/configure
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
