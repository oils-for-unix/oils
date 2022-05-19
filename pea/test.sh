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

all-files() {
  # Files that are reported as part of the source code.
  metrics/source-code.sh osh-files
  metrics/source-code.sh oil-lang-files

  # Files that are type checked.  This includes transitive deps.
  # TODO: Remove duplicates!  Unlike the ones above, these start with '.'
  #
  # This file is created by types/oil-slice.sh deps
  osh-eval-manifest
  # more-oil-manifest
}

parse-one() {
  # Use PY3 because Python 3.8 and above has type comments
  $PY3 pea/pea_main.py "$@"
}

parse-all() {
  # qsn_/qsn.py has some kind of unicode excapes, probably easy to fix
  # .pyi files need to be parsed too
  all-files | egrep '\.py$|\.pyi$' | xargs --verbose -- $0 parse-one
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

  PYTHONPATH=$pip3_lib_path ../oil_DEPS/python3 ~/.local/bin/mypy pea/pea_main.py
}

"$@"
