#!/usr/bin/env bash
#
# Usage:
#   benchmarks/callgrind.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

fib() {
  # Hm dbg build seems to give more exact info
  local osh=_bin/cxx-dbg/osh
  #local osh=_bin/cxx-opt/osh

  ninja $osh

  valgrind --tool=callgrind \
    $osh benchmarks/compute/fib.sh 10 44
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
