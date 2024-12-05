#!/usr/bin/env bash
#
# Quick test for a potential rewrite of mycpp.
#
# Usage:
#   pea/TEST.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/no-quotes.sh

source test/common.sh  # run-test-funcs
source devtools/common.sh

source build/dev-shell.sh  # find python3 in /wedge PATH component

readonly MYPY_VENV='_tmp/mypy-venv'

install-latest-mypy() {
  local venv=$MYPY_VENV

  rm -r -f -v $venv

  python3 -m venv $venv

  . $venv/bin/activate

  python3 -m pip install mypy

  # 2022:                   1.5.1 (compiled: yes)
  # 2024-12 Debian desktop: 1.13.0 (compiled: yes)
  # 2024-12 Soil CI image:  1.10.0 
  mypy-version
}

_check-types() {
  python3 -m mypy --version
  time python3 -m mypy --strict pea/pea_main.py
}

check-with-our-mypy() {
  echo PYTHONPATH=$PYTHONPATH
  echo

  _check-types
}

check-with-latest-mypy() {
  # This disables the MyPy wedge< and uses the latest MyPy installed above
  # It'
  export PYTHONPATH=.

  # install-mypy creates this.  May not be present in CI machine.
  local activate=$MYPY_VENV/bin/activate
  if test -f $activate; then
    . $activate
  fi

  _check-types
}


#
# Run Pea
#

pea-main() {
  pea/pea_main.py "$@"
}

parse-one() {
  pea-main parse "$@"
}

translate-cpp() {
  ### Used by mycpp/NINJA-steps.sh

  pea-main cpp "$@"
}

all-files() {
  # Can't run this on Soil because we only have build/py.sh py-source, not
  # 'minimal'

  # Update this file with build/dynamic-deps.sh pea-hack

  cat pea/oils-typecheck.txt

  for path in */*.pyi; do
    echo $path
  done
}

parse-all() {
  #source $MYPY_VENV/bin/activate
  time all-files | xargs --verbose -- $0 pea-main parse
}

# Good illustration of "distributing your overhead"
#
# Total work goes up, while latency goes down.  To a point.  Then it goes back
# up.

# batch size 30
# 
# real    0m0.342s
# user    0m0.735s
# sys     0m0.059s
# 
# batch size 20
# 
# real    0m0.305s
# user    0m0.993s
# sys     0m0.081s
# 
# batch size 15
# 
# real    0m0.299s
# user    0m1.110s
# sys     0m0.123s
# 
# batch size 10
# 
# real    0m0.272s
# user    0m1.362s
# sys     0m0.145s

batch-size() {
  local num_files=$1

  local num_procs
  num_procs=$(nproc)

  # Use (p-1) as a fudge so we don't end up more batches than processors
  local files_per_process=$(( num_files / (num_procs - 1) ))

  echo "$num_procs $files_per_process"
}

demo-par() {
  ### Demo parallelism of Python processes

  local files
  num_files=$(all-files | wc -l)

  # 103 files

  shopt -s lastpipe
  batch-size $num_files | read num_procs optimal

  echo "Parsing $num_files files with $num_procs parallel processes"
  echo "Optimal batch size is $optimal"

  echo

  echo 'All at once:'
  time parse-all > /dev/null 2>&1
  echo

  # 5 is meant to be suboptimal
  for n in 50 30 20 10 5 $optimal; do
    echo "batch size $n"
    time all-files | xargs --verbose -P $num_procs -n $n -- \
      $0 parse-one > /dev/null 2>&1
    echo
  done
}

# - 0.40 secs to parse
# - 0.56 secs pickle, so that's 160 ms
# Then
#
# - 0.39 secs load pickle
#
# That's definitely slower than I want.  It's 6.6 MB of data.
#
# So 
# - parallel parsing can be done in <300 ms
# - parallel pickling
# - serial unpickling (reduce) in 390 ms
#
# So now we're at ~700 ms or so.  Can we type check in 300 ms in pure Python?
#
# What if we compress the generated ASDL?  Those are very repetitive.

# Problem statement:

_serial-pickle() {
  mkdir -p _tmp
  local tmp=_tmp/serial

  time all-files | xargs --verbose -- $0 pea-main dump-pickles > $tmp

  ls -l -h $tmp

  echo 'loading'
  time pea-main load-pickles < $tmp
}

# 1.07 seconds
serial-pickle() { time $0 _serial-pickle; }

pickle-one() {
  pea-main dump-pickles "$@" > _tmp/p/$$
}

_par-pickle() {
  local files
  num_files=$(all-files | wc -l)

  shopt -s lastpipe
  batch-size $num_files | read num_procs optimal

  local dir=_tmp/p
  rm -r -f -v $dir
  mkdir -p $dir

  time all-files | xargs --verbose -P $num_procs -n $optimal -- $0 pickle-one

  ls -l -h $dir

  # This takes 410-430 ms?  Wow that's slow.
  time cat $dir/* | pea-main load-pickles
}

# Can get this down to ~700 ms
#
# Note parsing serially in a single process is 410 ms !!!  So this is NOT a win
# unless we have more work besides parsing to parallelize.
# 
# We can extract constants and forward declarations in parallel I suppose.
#
# BUT immutable string constants have to be de-duplciated!  Though I guess that
# is a natural 'reduce' step.
#
# And we can even do implementation and prototypes in parallel too?
#
# I think the entire algorithm can be OPTIMISTIC without serialized type
# checking?
#
# I think 
#
# a = 5
# b = a  # do not know the type without a global algorithm
#
# Or I guess you can do type checking within a function.  Functions require
# signatures.  So yes let's do that in parallel.
#
# --
#
# The ideal way to do this would be to split Oils up into MODULES, like
#
# _debuild/
# builtin/
# core/
# data_lang/
# frontend/
# osh/
# ysh/
# Smaller: pgen2/ pylib/ tools/
#
# And modules are acyclic, and can compile on their own with dependencies.  If
# you pick random .py files and spit out header files, I think they won't compile.
# The forward declarations and constants will work, but the prototype won't.

par-pickle() { time $0 _par-pickle; }

sum1() {
  awk '{ sum += $1 } END { print sum }'
}

sum-sizes() {
  xargs -I {} -- find {} -printf '%s %p\n' | sum1
}

size-ratio() {
  # all-files
  # echo _tmp/p/*

  # 1.96 MB of source code
  all-files | sum-sizes

  # 7.13 MB of pickle files
  # Weirdly echo _tmp/p/* doesn't work here
  for f in _tmp/p/*; do echo $f; done | sum-sizes
}

# Only 47 ms!
# I want the overhead to be less than 1 second:
#   1. parallel parsing + pickle
#   2. serial unpickle + type check
#   3. starting the process
#
# So unpickling is slow.

osh-overhead() {
  time bin/osh -c 'echo hi'
}


# MyPy dev version takes 10.2 seconds the first time (without their mypyc
# speedups)
#
# 0.150 seconds the second time, WITHOUT code changes
# 0.136 seconds

# 4.1 seconds: whitespace change
# 3.9 seconds: again, and this is on my fast hoover machine

# 5.0 seconds - Invalid type!
# 4.9 seconds - again invalid


mypy-compare() {
  devtools/types.sh check-oils
}

test-translate() {
  translate-cpp bin/oils_for_unix.py
}

test-syntax-error() {
  set +o errexit

  # error in Python syntax
  parse-one pea/testdata/py_err.py
  nq-assert $? -eq 1

  # error in signature
  parse-one pea/testdata/sig_err.py
  nq-assert $? -eq 1

  # error in assignment
  parse-one pea/testdata/assign_err.py
  nq-assert $? -eq 1
}

test-mycpp-integration() {
  # Works
  echo ---
  pea-main mycpp 

  echo ---
  pea-main mycpp mycpp/examples/test_small_str.py
}

run-tests() {
  # Making this separate for soil/worker.sh

  echo 'Running test functions'
  run-test-funcs
}

"$@"
