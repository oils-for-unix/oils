#!/bin/bash
#
# Usage:
#   tools/find//run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly REPO_ROOT=$(cd $(dirname $0)/../.. && pwd)

find-demo() {
  echo
  echo --- "$@" ---
  echo

  # Add 'tools' dir to prevent it from walking the whole repo
  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/vendor" \
    $REPO_ROOT/tools/find/find.py tools "$@"
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
