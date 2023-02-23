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

install-kcachegrind() {
  sudo apt-get install kcachegrind
}

"$@"
