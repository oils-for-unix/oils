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

  PYTHONPATH='.:vendor' tools/find/find.py "$@"
}

unit-tests() {
  find-demo -true
  find-demo -false -o -true
  find-demo -true -a -false

  find-demo -name '*.py'

  # implicit -a
  find-demo -name '*.py' -print
  find-demo -printf "%P\n" -print

  find-demo -type f
  find-demo -type f ',' -name '*.py'

  # comma operator
#  find-demo -type f -a -print , -type d -a -print

  find-demo -type f -a -name '*.py' -a -print

  find-demo '(' -type f -o -type d ')' -a -name 'py'
  find-demo '(' -type f -o -type d -a -name 'py' ')'

  find-demo -type f -a -exec echo {} ';'

  find-demo -type f -a -fprintf out '%P\n' -a -quit

  find-demo -type f -a -name '*.py'

  find-demo '!' -name '*.py'
}

"$@"
