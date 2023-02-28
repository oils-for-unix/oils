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
