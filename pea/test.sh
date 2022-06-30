#!/usr/bin/env bash
#
# Quick test for a potential rewrite of mycpp.
#
# Usage:
#   test/py3_parse.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source types/common.sh

# not using build/dev-shell.sh for now
readonly PY3=../oil_DEPS/python3

parse-one() {
  # Use PY3 because Python 3.8 and above has type comments
  $PY3 pea/pea_main.py parse "$@"
}

translate-cpp() {
  ### Used by mycpp/NINJA-steps.sh

  $PY3 pea/pea_main.py cpp "$@"
}

test-translate() {
  translate-cpp bin/osh_eval.py
}

all-files() {
  # Can't run this on Soil because we only have build/dev.sh py-source, not
  # 'minimal'
  # build/app-deps.sh osh-eval

  cat pea/osh-eval-typecheck.txt

  for path in */*.pyi; do
    echo $path
  done
}

parse-all() {

  time all-files | xargs --verbose -- $0 parse-one
}

dump-sys-path() {
  ### Dump for debugging
  python3 -c 'import sys; print(sys.path)'
}

pip3-lib-path() {
  ### python3.6 on Ubuntu; python3.7 in debian:buster-slim in the container
  shopt -s failglob
  echo ~/.local/lib/python3.?/site-packages
}

check-types() {
  #mypy_ test/py3_parse.py

  local pip3_lib_path
  pip3_lib_path=$(pip3-lib-path)

  PYTHONPATH=$pip3_lib_path ../oil_DEPS/python3 \
    ~/.local/bin/mypy --strict pea/pea_main.py
}

test-syntax-error() {
  set +o errexit

  # error in Python syntax
  parse-one pea/testdata/py_err.py

  # error in signature
  parse-one pea/testdata/sig_err.py

  # error in assignment
  parse-one pea/testdata/assign_err.py
}

"$@"
