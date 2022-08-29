#!/usr/bin/env bash
#
# Build oil-native.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Demo for the oil-native tarball.
# Notes:
# - Does not rely on Ninja, which is for the dev build
# - It shouldn't require 'objcopy'
# - TODO: do this in the Soil 'cpp' task

tarball-demo() {
  mkdir -p _bin

  time _build/oil-native.sh '' '' SKIP_REBUILD

  local bin=_bin/cxx-opt-sh/osh_eval.stripped

  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace
  $bin -n -c 'echo "hello $name"'
}

#
# Ninja Wrappers
#

soil-run() {
  ### Invoked by soil/worker.sh

  ./NINJA-config.sh

  ninja _bin/cxx-dbg/osh_eval \
        _bin/cxx-asan/osh_eval \
        _bin/cxx-opt/osh_eval.stripped
}

oil-slice-demo() {
  export PYTHONPATH='.:vendor/'

  echo 'echo hi' | bin/osh_parse.py
  bin/osh_parse.py -c 'ls -l'

  local osh_eval=${1:-bin/osh_eval.py}

  # Same functionality in bin/osh_eval
  echo 'echo hi' | $osh_eval
  $osh_eval -n -c 'ls -l'
  echo ---
  # ast format is none
  $osh_eval --ast-format none -n -c 'ls -l'

  echo '-----'

  # Now test some more exotic stuff
  $osh_eval -c '(( a = 1 + 2 * 3 ))'

  $osh_eval -c \
    'echo "hello"x $$ ${$} $((1 + 2 * 3)) {foo,bar}@example.com'

  $osh_eval -c 'for x in 1 2 3; do echo $x; done'
}

osh-eval-smoke() {
  local bin=_bin/cxx-dbg/osh_eval
  ninja $bin
  oil-slice-demo $bin
}

"$@"
