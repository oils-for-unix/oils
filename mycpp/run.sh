#!/bin/bash
#
# Translate, compile, and run mycpp examples.
#
# TODO: Extract setup.sh, test.sh, and run.sh from this file.
#
# Usage:
#   ./run.sh <function name>
#
# Setup:
#
#   Clone mypy into $MYPY_REPO, and then:
#
#   Switch to the release-0.730 branch.  As of March 2020, that's the latest
#   release I've tested against.
#
#   Then install typeshed:
#
#   $ git submodule init
#   $ git submodule update
#
# If you don't have Python 3.6, then build one from a source tarball and then
# install it.  (NOTE: mypyc tests require the libsqlite3-dev dependency.  
# It's probably not necessary for running mycpp.)
# 
# Afterwards, these commands should work:
#
#   ./run.sh create-venv
#   source _tmp/mycpp-venv/bin/activate
#   ./run.sh mypy-deps      # install deps in virtual env
#   ./run.sh build-all      # translate and compile all examples
#   ./run.sh test-all       # check for correctness
#   ./run.sh benchmark-all  # compare speed

# To build and run one example:
#
#   ./run.sh example-both loops
#   ./run.sh test-all loops  # test just this one

set -o nounset
set -o pipefail
set -o errexit

source common.sh  # THIS_DIR and REPO_ROOT

source $REPO_ROOT/test/common.sh  # for R_PATH
source $REPO_ROOT/build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR
source examples.sh
source harness.sh

readonly ASAN_FLAGS='-O0 -g -fsanitize=address'
export ASAN_OPTIONS='detect_leaks=0'  # like build/mycpp.sh
# also in build/mycpp.sh
export ASAN_SYMBOLIZER_PATH="$REPO_ROOT/$CLANG_DIR_RELATIVE/bin/llvm-symbolizer"

readonly DBG_FLAGS='-O0 -g'

create-venv() {
  local dir=_tmp/mycpp-venv
  #python3.6 -m venv $dir
  python3 -m venv $dir

  ls -l $dir
  
  echo "Now run . $dir/bin/activate"
}

# Do this inside the virtualenv
# Re-run this when UPGRADING MyPy.  10/2019: Upgraded from 0.670 to 0.730.
mypy-deps() {
  python3 -m pip install -r $MYPY_REPO/test-requirements.txt
}

# MyPy doesn't have a configuration option for this!  It's always an env
# variable.
export MYPYPATH=~/git/oilshell/oil
# for running most examples
export PYTHONPATH=".:$REPO_ROOT/vendor"

# Damn it takes 4.5 seconds to analyze.
translate-osh-parse() {

  #local main=~/git/oilshell/oil/bin/oil.py

  # Have to get rid of strict optional?
  local main=~/git/oilshell/oil/bin/osh_parse.py
  time ./mycpp_main.py $main
}

# for examples/{parse,asdl_generated}
# TODO: Get rid of this?   Every example should be translated the same.
#
# What does it do?
# - passes multiple files in order to mycpp_main.py
# - adds the "snippet" prefix

translate-ordered() {
  local name=$1
  local snippet=$2
  shift 2

  local raw=_gen/${name}_raw.cc
  local out=_gen/${name}.cc

  ( source _tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO MYPYPATH=$REPO_ROOT:$REPO_ROOT/native \
      ./mycpp_main.py "$@" > $raw
  )

  {
    echo "$snippet"
    cpp-skeleton $name $raw 
  } > $out

  wc -l _gen/*
}

# This is the one installed from PIP
#mypy() { ~/.local/bin/mypy "$@"; }

# Use repo in the virtualenv
mypy() {
  ( source _tmp/mycpp-venv/bin/activate
    PYTHONPATH=$MYPY_REPO python3 -m mypy "$@";
  )
}
# -I with ASDL files.
compile-with-asdl() {
  local name=$1
  local variant=$2
  local src=_gen/$name.cc
  shift 2

  local flags
  case $variant in
    (asan)
      flags="$CXXFLAGS $ASAN_FLAGS"
      ;;
    (opt)
      flags="$CXXFLAGS -O2 -g"
      ;;
    (*)
      flags="$CXXFLAGS"
      ;;
  esac

  # .. for asdl/runtime.h
  $CXX -o _bin/$name.$variant $flags \
    -I . -I .. -I ../_devbuild/gen -I ../_build/cpp -I _gen -I ../cpp \
    mylib.cc gc_heap.cc $src "$@" -lstdc++
}

# fib_recursive(35) takes 72 ms without optimization, 20 ms with optimization.
# optimization doesn't do as much for cgi.  1M iterations goes from ~450ms to ~420ms.

# NOTES on timings:

### fib_recursive
# fib_recursive(33) - 1083 ms -> 12 ms.  Biggest speedup!

### cgi
# 1M iterations: 580 ms -> 173 ms
# optimizations:
# - const_pass pulls immutable strings to top level
# - got rid of # function docstring!

### escape
# 200K iterations: 471 ms -> 333 ms

### cartesian
# 200K iterations: 800 ms -> 641 ms

### length
# no timings


# Is this used?
report() {
  R_LIBS_USER=$R_PATH ./examples.R report _tmp "$@"
}


#
# Utilities
#

grepall() {
  mypyc-files | xargs -- grep "$@"
}

count() {
  wc -l *.py | sort -n
  echo
  wc -l *.cc *.h | sort -n
}

cpp-compile() {
  local name=$1
  local variant=$2
  shift 2

  # TODO: my_runtime_test fails with GC_EVERY_ALLOC
  local flags='-D GC_DEBUG -D GC_PROTECT -D GC_EVERY_ALLOC '
  #local flags='-D GC_DEBUG -D GC_PROTECT '

  case $variant in
    (asan)
      flags+="$CXXFLAGS $ASAN_FLAGS"
      ;;
    (dbg)
      flags+="$CXXFLAGS $DBG_FLAGS"
      ;;
    (*)
      flags+="$CXXFLAGS"
      ;;
  esac

  mkdir -p _bin
  $CXX -o _bin/$name.$variant $flags -I . $name.cc "$@" -lstdc++ -std=c++11
}

gen-ctags() {
  ctags -R $MYPY_REPO
}

gc-examples() {
  if true; then
    # these work
    BENCHMARK=1 GC=1 example-both test_switch asan
    BENCHMARK=1 GC=1 example-both cgi asan
    BENCHMARK=1 GC=1 example-both fib_iter asan
    BENCHMARK=1 GC=1 example-both fib_recursive asan

    GC=1 example-both asdl_generated
    GC=1 example-both cartesian
    GC=1 example-both classes
    GC=1 example-both containers
    GC=1 example-both control_flow opt
    GC=1 example-both escape
    GC=1 example-both files
    GC=1 example-both length
    GC=1 example-both modules
    GC=1 example-both scoped_resource
    GC=1 example-both test_conditional
    GC=1 example-both test_hoist
    GC=1 example-both tuple_return_value
  fi
  return

  # GLOBAL List() can't do NewSlab!  Duh.
  GC=1 example-both loops
  return

  BENCHMARK=1 GC=1 example-both cartesian
  #GC=1 example-both cartesian
  return

  # %5d doesn't work in either mylib or my_runtime
  GC=1 example-both strings

  return

  # have print(), ListIter
}

# For getting PYTHONPATH, ASAN_SYMBOLIZER_PATH, etc.
run() {
  "$@"
}

"$@"
