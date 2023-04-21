#!/usr/bin/env bash
#
# Build oils-for-unix.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Demo for the oils-for-unix tarball.
# Notes:
# - Does not rely on Ninja, which is for the dev build
# - It shouldn't require 'objcopy'
# - TODO: do this in the Soil 'cpp' task

tarball-demo() {
  mkdir -p _bin

  ./configure

  time _build/oils.sh '' '' SKIP_REBUILD

  local bin=_bin/cxx-opt-sh/oils-for-unix.stripped

  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace

  # TODO: Use symlink
  $bin osh -n -c 'echo "hello $name"'
}

measure-build-times() {
  local variant=${1:-opt}

  mkdir -p _bin

  ./configure

  local out_tsv=_tmp/time-tarball-$variant.tsv

  # Header for functions in build/ninja-rules-cpp.sh
  benchmarks/time_.py --tsv --out $out_tsv --rusage --print-header --field verb --field out

  time TIME_TSV_OUT=$out_tsv _build/oils.sh '' $variant

  echo
  cat $out_tsv
}

#
# Ninja Wrappers
#

soil-run() {
  ### Invoked by soil/worker.sh

  ./NINJA-config.sh

  # Keep the Cheney build compiling
  ninja _bin/cxx-dbg/oils-for-unix \
        _bin/cxx-asan/oils-for-unix \
        _bin/cxx-opt/oils-for-unix.stripped \
        _bin/cxx-opt+cheney/oils-for-unix
}

oil-slice-demo() {
  export PYTHONPATH='.:vendor/'

  echo 'echo hi' | bin/osh_parse.py
  bin/osh_parse.py -c 'ls -l'

  local osh=${1:-bin/osh}

  # Same functionality in bin/oils-for-unix
  echo 'echo hi' | $osh
  $osh -n -c 'ls -l'
  echo ---
  # ast format is none
  $osh --ast-format none -n -c 'ls -l'

  echo '-----'

  # Now test some more exotic stuff
  $osh -c '(( a = 1 + 2 * 3 ))'

  $osh -c \
    'echo "hello"x $$ ${$} $((1 + 2 * 3)) {foo,bar}@example.com'

  $osh -c 'for x in 1 2 3; do echo $x; done'
}

oils-cpp-smoke() {
  local bin=_bin/cxx-dbg/osh
  ninja $bin
  oil-slice-demo $bin
}

"$@"
