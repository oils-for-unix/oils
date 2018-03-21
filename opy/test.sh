#!/bin/bash
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly OPYC=$THIS_DIR/../bin/opyc


osh-opy() {
  _tmp/oil-opy/bin/osh "$@"
}

oil-opy() {
  _tmp/oil-opy/bin/oil "$@"
}

osh-help() {
  osh-opy --help
}

# TODO: Add compiled with "OPy".
# How will it know?  You can have a special function bin/oil.py:
# def __GetCompilerName__():
#   return "CPython"
#
# If the function name is opy stub, then Opy ret
#
# Or __COMPILER_NAME__ = "CPython"
# The OPy compiler can rewrite this to "OPy".

osh-version() {
  osh-opy --version
}

# TODO:
# - Run with oil.ovm{,-dbg}

# 3/2018 byterun results:
#
# Ran 28 tests, 4 failures
# asdl/arith_parse_test.pyc core/glob_test.pyc core/lexer_gen_test.pyc osh/lex_test.pyc
#

oil-unit() {
  local dir=${1:-_tmp/oil-opy}
  local vm=${2:-cpython}  # byterun or cpython

  pushd $dir

  #$OPYC run core/cmd_exec_test.pyc

  local n=0
  local -a failures=()

  #for t in {build,test,native,asdl,core,osh,test,tools}/*_test.py; do
  for t in {asdl,core,osh}/*_test.pyc; do

    echo $t
    if test $vm = byterun; then

      set +o errexit
      set +o nounset  # for empty array!

      # Note: adding PYTHONPATH screws things up, I guess because it's the HOST
      # interpreter pythonpath.
      $OPYC run $t
      status=$?

      if test $status -ne 0; then
        failures=("${failures[@]}" $t)
      fi
      (( n++ ))

    elif test $vm = cpython; then
      PYTHONPATH=. python $t
      #(( n++ ))

    else
      die "Invalid VM $vm"
    fi
  done
  popd

  if test $vm = byterun; then
    echo "Ran $n tests, ${#failures[@]} failures"
    echo "${failures[@]}"
  fi
}

oil-unit-byterun() {
  oil-unit '' byterun
}

readonly -a FAILED=(
  #asdl/arith_parse_test.pyc  # IndexError
  # I believe this is due to:
  # 'TODO: handle generator exception state' in pyvm2.py.  Open bug in
  # byterun.  asdl/tdop.py uses a generator Tokenize() with StopIteration

  # Any bytecode can raise an exception internally.


  core/glob_test.pyc  # unbound method append()
  core/lexer_gen_test.pyc  # ditto
  osh/lex_test.pyc  # ditto
)

oil-byterun-failed() {
  #set +o errexit

  for t in "${FAILED[@]}"; do

    echo
    echo ---
    echo --- $t
    echo ---

    pushd _tmp/oil-opy
    $OPYC run $t
    popd
  done
}

# TODO: byterun/run.sh has this too
byterun-unit() {
  pushd byterun
  for t in test_*.py; do
    echo
    echo "*** $t"
    echo
    PYTHONPATH=. ./$t
  done
}


unit() {
  PYTHONPATH=. "$@"
}

# NOTE: I checked with set -x that it's being run.  It might be nicer to be
# sure with --verison.

export OSH_PYTHON=opy/_tmp/oil-opy/bin/osh

# NOTE: Failures in 'var-num' and 'special-vars' due to $0.  That proves
# we're running the right binary!
spec() {
  local action=${1:-smoke}
  shift

  pushd ..
  # Could also export OSH_OVM
  test/spec.sh $action "$@"
  popd
}

"$@"
