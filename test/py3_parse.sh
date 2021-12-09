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
  test/py3_parse.py "$@"
}

parse-all() {
  # qsn_/qsn.py has some kind of unicode excapes, probably easy to fix
  # .pyi files need to be parsed too
  all-files | egrep '\.py$|\.pyi$' | xargs --verbose -- $0 parse-one
}

"$@"
