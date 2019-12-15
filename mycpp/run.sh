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
#   Switch to the release-0.670 branch.  As of April 2019, that's the latest
#   release, and what I tested against.
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

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly REPO_ROOT=$(cd $THIS_DIR/.. && pwd)

readonly MYPY_REPO=~/git/languages/mypy

source $REPO_ROOT/test/common.sh  # for R_PATH
source $REPO_ROOT/build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR
source examples.sh
source harness.sh

readonly CXX=$REPO_ROOT/$CLANG_DIR_RELATIVE/bin/clang++
# system compiler
#readonly CXX='c++'

time-tsv() {
  $REPO_ROOT/benchmarks/time.py --tsv "$@"
}

create-venv() {
  local dir=_tmp/mycpp-venv
  /usr/local/bin/python3.6 -m venv $dir

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
    filter-cpp $name $raw 
  } > $out

  wc -l _gen/*
}

filter-cpp() {
  local main_module=${1:-fib_iter}
  shift

  cat <<EOF
#include "mylib.h"

EOF

  cat "$@"

  cat <<EOF

int main(int argc, char **argv) {
  if (getenv("BENCHMARK")) {
    $main_module::run_benchmarks();
  } else {
    $main_module::run_tests();
  }
}
EOF
}

asdl-gen() {
  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/vendor" $REPO_ROOT/asdl/tool.py "$@"
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
  local src=_gen/$name.cc
  shift

  # TODO: Remove _gen dir

  local more_flags='-O0 -g'  # to debug crashes
  #local more_flags=''
  $CXX -o _bin/$name $CPPFLAGS $more_flags \
    -I . -I ../_devbuild/gen -I ../_build/cpp -I _gen -I ../cpp \
    mylib.cc $src "$@" -lstdc++
}

# fib_recursive(35) takes 72 ms without optimization, 20 ms with optimization.
# optimization doesn't do as much for cgi.  1M iterations goes from ~450ms to ~420ms.

# -O3 is faster than -O2 for fib, but let's use -O2 since it's "standard"?

CPPFLAGS='-Wall -O0 -g -std=c++11 -ferror-limit=1000'

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

cpp-compile-run() {
  local name=$1
  shift

  mkdir -p _bin
  $CXX -o _bin/$name $CPPFLAGS -I . $name.cc "$@" -lstdc++
  _bin/$name
}

target-lang() {
  cpp-compile-run target_lang ../cpp/dumb_alloc.cc -I ../cpp
}

heap() {
  cpp-compile-run heap
}

mylib-test() {
  cpp-compile-run mylib_test mylib.cc
}

gen-ctags() {
  ctags -R $MYPY_REPO
}

"$@"
