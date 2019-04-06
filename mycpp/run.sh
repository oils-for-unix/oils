#!/bin/bash
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

readonly MYPY_REPO=~/git/languages/mypy

banner() {
  echo -----
  echo "$@"
  echo -----
}

create-venv() {
  local dir=_tmp/mycpp-venv
  /usr/local/bin/python3.6 -m venv $dir

  ls -l $dir
  
  echo "Now run . $dir/bin/activate"
}

# Do this inside the virtualenv
mypy-deps() {
  python3 -m pip install -r $MYPY_REPO/test-requirements.txt
}

# MyPy doesn't have a configuration option for this!  It's always an env
# variable.
export MYPYPATH=~/git/oilshell/oil
export PYTHONPATH=".:$MYPY_REPO"

# Damn it takes 4.5 seconds to analyze.
translate-osh-parse() {

  #local main=~/git/oilshell/oil/bin/oil.py

  # Have to get rid of strict optional?
  local main=~/git/oilshell/oil/bin/osh_parse.py
  time ./mycpp.py $main
}

# 1.5 seconds.  Still more than I would have liked!
translate-many() {
  local name=$1
  shift

  local raw=_gen/${name}_raw.cc
  local out=_gen/${name}.cc

  time ./mycpp.py "$@" > $raw

  # TODO: include tdop.h too?
  {
    echo '#include "typed_arith.asdl.h"'
    filter-cpp $name $raw 
  } > $out

  wc -l _gen/*
}

translate-typed-arith() {
  # tdop.py is a dependency.  How do we determine order?
  #
  # I guess we should put them in arbitrary order.  All .h first, and then all
  # .cc first.

  # NOTE: tdop.py doesn't translate because of the RE module!

  local srcs=( $PWD/../asdl/tdop.py $PWD/../asdl/typed_arith_parse.py )

  local name=typed_arith_parse
  translate-many $name "${srcs[@]}"

  cc -o _bin/$name $CPPFLAGS \
    -I . -I ../_tmp \
    _gen/$name.cc runtime.cc \
    -lstdc++
}

filter-cpp() {
  local main_module=${1:-fib_iter}
  shift

  cat <<EOF
#include "runtime.h"

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

# 1.1 seconds
translate() {
  local name=${1:-fib}
  local main="examples/$name.py"

  mkdir -p _gen

  local raw=_gen/${name}_raw.cc
  local out=_gen/${name}.cc

  time ./mycpp.py $main > $raw
  wc -l $raw

  local main_module=$(basename $main .py)
  filter-cpp $main_module $raw > $out

  wc -l _gen/*

  echo
  cat $out
}

EXAMPLES=( $(cd examples && echo *.py) )
EXAMPLES=( "${EXAMPLES[@]//.py/}" )

translate-fib_iter() { translate fib_iter; }
translate-fib_recursive() { translate fib_recursive; }
translate-cgi() { translate cgi; }
translate-escape() { translate escape; }
translate-length() { translate length; }
translate-cartesian() { translate cartesian; }
translate-parse() { translate parse; }  # classes!
translate-containers() { translate containers; }
translate-control_flow() { translate control_flow; }


readonly PREPARE_DIR=$PWD/../_devbuild/cpython-full

# NOT USED
modules-deps() {
  local main_module=modules
  local prefix=_tmp/modules

  # This is very hacky but works.  We want the full list of files.
  local pythonpath="$PWD:$PWD/examples:$(cd $PWD/../vendor && pwd)"

  pushd examples
  mkdir -p _tmp
  ln -s -f -v ../../../build/app_deps.py _tmp

  PYTHONPATH=$pythonpath \
    $PREPARE_DIR/python -S _tmp/app_deps.py both $main_module $prefix

  popd

  egrep '/mycpp/.*\.py$' examples/_tmp/modules-cpython.txt \
    | egrep -v '__init__.py|runtime.py' \
    | awk '{print $1}' > _tmp/manifest.txt

  local raw=_gen/modules_raw.cc
  local out=_gen/modules.cc

  cat _tmp/manifest.txt | xargs ./mycpp.py > $raw

  filter-cpp modules $raw > $out
  wc -l $raw $out
}

translate-modules() {
  local raw=_gen/modules_raw.cc
  local out=_gen/modules.cc
  ./mycpp.py testpkg/module1.py testpkg/module2.py examples/modules.py > $raw
  filter-cpp modules $raw > $out
  wc -l $raw $out
}

compile-modules() {
  compile modules
}

# fib_recursive(35) takes 72 ms without optimization, 20 ms with optimization.
# optimization doesn't do as much for cgi.  1M iterations goes from ~450ms to ~420ms.

# -O3 is faster than -O2 for fib, but let's use -O2 since it's "standard"?

CPPFLAGS='-O2 -std=c++11 '

compile() { 
  local name=${1:-fib} #  name of output, and maybe input
  local src=${2:-_gen/$name.cc}

  # need -lstdc++ for operator new

  #local flags='-O0 -g'  # to debug crashes
  mkdir -p _bin
  cc -o _bin/$name $CPPFLAGS -I . \
    runtime.cc $src -lstdc++
}

compile-fib_iter() { compile fib_recursive; }
compile-fib_recursive() { compile fib_recursive; }
compile-cgi() { compile cgi; }
compile-escape() { compile escape; }
compile-length() { compile length; }
compile-cartesian() { compile cartesian; }
compile-parse() { compile parse; }
compile-containers() { compile containers; }
compile-control_flow() { compile control_flow; }

run-example() {
  local name=$1
  translate $name
  compile $name

  echo
  echo $'\t[ C++ ]'
  time _bin/$name

  echo
  echo $'\t[ Python ]'
  time examples/${name}.py
}

benchmark() {
  export BENCHMARK=1
  run-example "$@"
}

benchmark-fib_iter() { benchmark fib_iter; }

# fib_recursive(33) - 1083 ms -> 12 ms.  Biggest speedup!
benchmark-fib_recursive() { benchmark fib_recursive; }

# 1M iterations: 580 ms -> 173 ms
# optimizations:
# - const_pass pulls immutable strings to top level
# - got rid of # function docstring!
benchmark-cgi() { benchmark cgi; }

# 200K iterations: 471 ms -> 333 ms
benchmark-escape() { benchmark escape; }

# 200K iterations: 800 ms -> 641 ms
benchmark-cartesian() { benchmark cartesian; }

# no timings
benchmark-length() { benchmark length; }

benchmark-parse() { benchmark parse; }

benchmark-containers() { benchmark containers; }

benchmark-control_flow() { benchmark control_flow; }


build-all() {
  for name in "${EXAMPLES[@]}"; do
    case $name in
      modules)
        translate-modules
        compile-modules
        ;;
      *)
        translate $name
        compile $name
        ;;
    esac
  done
}

test-all() {
  #build-all

  mkdir -p _tmp

  # TODO: Compare output for golden!
  time for name in "${EXAMPLES[@]}"; do
    banner $name

    examples/${name}.py > _tmp/$name.python.txt 2>&1
    _bin/$name > _tmp/$name.cpp.txt 2>&1
    diff -u _tmp/$name.{python,cpp}.txt
  done
}

benchmark-all() {
  #build-all

  # Compare the two
  export BENCHMARK=1
  for name in "${EXAMPLES[@]}"; do
    banner $name

    echo
    echo $'\t[ C++ ]'
    time _bin/$name

    echo
    echo $'\t[ Python ]'
    time examples/${name}.py
  done
}

#
# Utilities
#

grepall() {
  mypyc-files | xargs -- grep "$@"
}

count() {
  wc -l {mycpp,debug,cppgen,fib}.py
  echo
  wc -l *.cc *.h
}

cpp-compile-run() {
  local name=$1

  mkdir -p _bin
  cc -o _bin/$name $CPPFLAGS -I . $name.cc -lstdc++
  _bin/$name
}

target-lang() {
  cpp-compile-run target_lang
}

heap() {
  cpp-compile-run heap
}

runtime-test() {
  cpp-compile-run runtime_test
}

gen-ctags() {
  ctags -R $MYPY_REPO
}

"$@"
