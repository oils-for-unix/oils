#!/usr/bin/env bash
#
# Quick test for a potential rewrite of mycpp.
#
# Usage:
#   pea/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # run-test-funcs
source devtools/common.sh
source build/dev-shell.sh  # find python3 in /wedge PATH component

parse-one() {
  # Use PY3 because Python 3.8 and above has type comments
  PYTHONPATH=. python3 pea/pea_main.py parse "$@"
}

translate-cpp() {
  ### Used by mycpp/NINJA-steps.sh

  PYTHONPATH=. python3 pea/pea_main.py cpp "$@"
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
  time all-files | xargs --verbose -- $0 parse-one
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

parallel-test() {
  ### Test out parallelism of Python processes

  local files
  num_files=$(all-files | wc -l)

  # 103 files

  # try different batch sizes.  
  local p=$(( $(nproc) ))

  echo "Parsing $num_files files with $p parallel processes"
  echo

  # 12 files at a time does well compared to the fastest
  local optimal=$(( num_files / (p - 1) ))
  echo "Optimal batch size is $optimal"
  echo

  echo 'All at once:'
  time parse-all > /dev/null 2>&1
  echo

  # 5 is meant to be very suboptimal
  for n in 50 30 20 10 5 $optimal; do
    echo "batch size $n"
    time all-files | xargs --verbose -P $p -n $n -- $0 parse-one > /dev/null 2>&1
    echo
  done
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



# TODO: Fix INTERNAL ERROR with MyPy 0.782
# We're using that for Python 2 support, but this is Python 3
check-types() {
  #mypy_ test/py3_parse.py

  # Note: not using mycpp/common.sh maybe-our-python3

  #local py3=../oil_DEPS/python3

  python3 -m mypy --strict pea/pea_main.py
}

test-translate() {
  translate-cpp bin/oils_for_unix.py
}

test-syntax-error() {
  set +o errexit

  # error in Python syntax
  parse-one pea/testdata/py_err.py
  assert $? -eq 1

  # error in signature
  parse-one pea/testdata/sig_err.py
  assert $? -eq 1

  # error in assignment
  parse-one pea/testdata/assign_err.py
  assert $? -eq 1
}

run-tests() {
  # Making this separate for soil/worker.sh

  echo 'Running test functions'
  run-test-funcs
}

"$@"
