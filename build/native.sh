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
source build/dev-shell.sh  # python2

# Demo for the oils-for-unix tarball.
# Notes:
# - Does not rely on Ninja, which is for the dev build
# - It shouldn't require 'objcopy'
# - TODO: do this in the Soil 'cpp' task

tarball-demo() {
  translator=${1:-mycpp}
  mkdir -p _bin

  ./configure

  time _build/oils.sh --translator "$translator" --skip-rebuild

  local bin
  case $translator in
    mycpp)
      bin=_bin/cxx-opt-sh/oils-for-unix.stripped
      ;;
    *)
      bin=_bin/cxx-opt-sh/$translator/oils-for-unix.stripped
      ;;
  esac

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

  time TIME_TSV_OUT=$out_tsv _build/oils.sh --variant "$variant"

  echo
  cat $out_tsv
}

#
# Ninja Wrappers
#

oils-demo() {
  local osh=${1:-bin/osh}

  export PYTHONPATH='.:vendor/'

  echo 'echo hi' | bin/osh_parse.py
  bin/osh_parse.py -c 'ls -l'

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
  local osh=_bin/cxx-asan+gcalways/osh
  local ysh=_bin/cxx-asan+gcalways/ysh

  ninja $osh $ysh
  echo

  $osh --version
  echo

  oils-demo $osh

  # Regression for pnode::PNode* rooting bug in spec/ysh-bugs, which only
  # manifests with _bin/cxx-asan+gcalways/ysh
  $ysh -c 'var x = 42; echo $x'
}

"$@"
