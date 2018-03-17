#!/bin/bash
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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
oil-unit() {
  local dir=${1:-_tmp/oil-opy}
  local vm=${2:-cpython}  # byterun or cpython

  pushd $dir
  mkdir -p _tmp
  #for t in {build,test,native,asdl,core,osh,test,tools}/*_test.py; do
  for t in {asdl,core,osh}/*_test.pyc; do

    echo $t
    if test $vm = byterun; then
      PYTHONPATH=. opy_ run $t
    elif test $vm = cpython; then
      PYTHONPATH=. python $t
    else
      die "Invalid VM $vm"
    fi
  done
  popd
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
