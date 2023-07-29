#!/usr/bin/env bash
#
# Usage:
#   test/arena.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # for run-other-suite-for-release
source test/wild-runner.sh  # For MANIFEST, etc.

_compare() {
  local path=$1

  mkdir -p _tmp/arena
  bin/osh --tool arena $path > _tmp/arena/left.txt
  if diff -u $path _tmp/arena/left.txt; then
	  echo "$path"
  else
	  return 1
  fi
}

test-here-doc() {
  _compare test/arena/here-dq.sh
  _compare test/arena/here-sq.sh
  _compare test/arena/here-multiple.sh

  # This is a known exception to the arena invariant.  The leading tabs aren't
  # preserved, because we don't need them for osh2oil translation.
  #_compare test/arena/here-dq-indented.sh
}

test-tilde() {
  _compare test/arena/tilde.sh
}

_compare-wild() {
  local rel_path=$1
  local abs_path=$2

  _compare $abs_path
}

# Run on wild corpus.  I think this never passed?
DISABLED-test-wild() {
  wc -l $MANIFEST
  cat $MANIFEST | xargs -n 2 -- $0 _compare-wild
}

run-for-release() {
  run-other-suite-for-release arena run-test-funcs
}

soil-run() {
  run-test-funcs
}

"$@"
