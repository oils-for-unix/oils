#!/usr/bin/env bash
#
# Build oils-for-unix.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)  # tsv-lib.sh uses this
source build/common.sh  # log

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
  $osh -c '(( a = 1 + 2 * 3 )); echo $a'

  $osh -c \
    'echo "hello"x $$ ${$} $((1 + 2 * 3)) {foo,bar}@example.com'

  $osh -c 'for x in 1 2 3; do echo $x; done'
}

soil-run() {
  if test "${container:-}" = podman; then

    # Work around for ASAN not working in podman

    local bin=_bin/cxx-dbg/osh

    log "Using $bin for podman"
    log ''

  else
    local bin=_bin/cxx-asan/osh
  fi

  ninja $bin
  echo

  echo "Built $bin"
  echo

  $bin --version
  echo

  oil-slice-demo $bin
}

"$@"
