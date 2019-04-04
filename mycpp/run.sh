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
translate-path() {
  local path=$1
  local name=$(basename $path .py)

  local raw=_gen/${name}_raw.cc
  local out=_gen/${name}.cc

  time ./mycpp.py $path > $raw

  filter-cpp $raw > $out

  wc -l _gen/*
}

translate-typed-arith() {
  translate-path $PWD/../asdl/typed_arith_parse.py
}

translate-tdop() {
  translate-path $PWD/../asdl/tdop.py
}

filter-cpp() {
  awk '
    BEGIN      { print "#include \"runtime.h\"\n" }

    /int fib/        { printing = 1 }  /* for fib.py */
    /^Str/           { printing = 1 }  /* for cgi.py */
    /^List/          { printing = 1 }  /* for escape.py */
    /__name__/       { printing = 0 }

               { if (printing) print }
  ' "$@"
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

  filter-cpp $raw > $out

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

# fib_recursive(35) takes 72 ms without optimization, 20 ms with optimization.
# optimization doesn't do as much for cgi.  1M iterations goes from ~450ms to ~420ms.

# -O3 is faster than -O2 for fib, but let's use -O2 since it's "standard"?

CPPFLAGS='-O2 -std=c++11 '

compile() { 
  local name=${1:-fib}
  # need -lstd++ for operator new

  #local flags='-O0 -g'  # to debug crashes
  mkdir -p _bin
  cc -o _bin/$name $CPPFLAGS -I . \
    runtime.cc _gen/$name.cc main.cc -lstdc++
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

# fib_recursive(33) - 1083 ms -> 12 ms.  Biggest speedup!
benchmark-fib() { benchmark fib; }

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
    translate $name
    compile $name
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
