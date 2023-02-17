#!/usr/bin/env bash
#
# Usage:
#   benchmarks/callgrind.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

fib() {
  ninja _bin/cxx-dbg/osh

  valgrind --tool=callgrind \
    _bin/cxx-dbg/osh benchmarks/compute/fib.sh
}

install-kcachegrind() {
  sudo apt-get install kcachegrind
}

"$@"
