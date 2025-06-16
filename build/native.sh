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

#
# Slices
#

slices() {
  # Prepare for Windows / Rust?

  # This works, but it imports all of core/shell.py
  local osh_eval=_bin/cxx-asan/bin/osh_eval.mycpp
  ninja $osh_eval

  $osh_eval -c 'echo 1; echo 2'

  # ~400 lines of C++ compile errors - circular dependencies
  #
  # I think we need something like mycpp --to-header?
  # So we can export all the forward declarations ... But maybe we won't use
  # them?  Can we built from the bottom up
  #
  # core/vm.py InitUnsafeArith might be an issue

  local osh_parse=_bin/cxx-asan/bin/osh_parse.mycpp
  ninja $osh_parse
}

count-slice() {
  # osh_parse.py: 35 files
  # 22K lines of output
  #
  # others: 89 files
  wc -l \
    _build/NINJA/bin.osh_parse/translate.txt \
    _build/NINJA/bin.osh_eval/translate.txt \
    _build/NINJA/bin.oils_for_unix/translate.txt 
}

check-slice() {
  # This type checks
  #
  # And we pass a list of files on the mycpp command line.
  #
  # I think we need to generate header files though
  #
  # core/vm.py if TYPE_CHECKING are an issue - they are not bound by
  # dynamic_deps.py
  #
  # But we should understand them
  #
  # Maybe we need to have a pass which computes imports and types:
  #
  # cppgen_pass::Decl::visit_import_from() ?
  #
  # Or just do the same hack as prebuilt/ for all those headers ... hm OK!

  devtools/types.sh check-binary bin.osh_parse
}

"$@"
