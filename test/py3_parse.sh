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
  # Main files

  metrics/source-code.sh osh-files
  metrics/source-code.sh oil-lang-files

  # Duplicate files

  osh-eval-manifest
  # more-oil-manifest
}

parse-one() {
  test/py3_parse.py "$@"
}

parse-all() {
  # qsn_/qsn.py has some kind of unicode excapes, probably easy to fix
  all-files | egrep '\.py$' | xargs --verbose -- $0 parse-one
}

"$@"
