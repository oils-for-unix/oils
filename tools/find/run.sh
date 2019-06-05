#!/bin/bash
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

find-demo() {
  echo
  echo --- "$@" ---
  echo

  PYTHONPATH=. tools/find/parse.py "$@"
}

unit-tests() {
  find-demo -type f

  find-demo -true

  # implicit -a
  find-demo -type f -print

  # comma operator
  find-demo -type f -a -print , -type d -a -print

  find-demo -name 'f'
  find-demo -type f -a -name 'py' 
  find-demo -type f -a -name 'py' -a -print

  find-demo '(' -type f -o -type d ')' -a -name 'py' 

  find-demo -type f -a -exec echo {} ';'

  find-demo -type f -a -fprintf out '%P\n' -a -quit

  #find-demo -type f -a -name '*.py' 
}

"$@"
