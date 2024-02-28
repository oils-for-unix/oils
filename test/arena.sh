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
  local osh=${2:-bin/osh}

  mkdir -p _tmp/arena
  $osh --tool arena $path > _tmp/arena/left.txt
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

test-big() {
  local num_files=0
  local num_passed=0

  local osh=bin/osh

  if false; then
    local osh_cpp=_bin/cxx-asan/osh
    ninja $osh_cpp
    osh=$osh_cpp
  fi

  for file in benchmarks/testdata/*; do
    echo "--- $file"
    echo
    set +o errexit
    time _compare $file $osh
    local status=$?
    set -o errexit

    if test $status = 0; then
      num_passed=$((num_passed+1))
    fi
    num_files=$((num_files+1))
  done

  # How do we handle this in tools/ysh_ify.py ?

  # 8 of 10 passed!
  echo
  echo "$num_passed of $num_files files respect the arena invariant"
  echo 'TODO: here docs broken!'
}

run-for-release() {
  run-other-suite-for-release arena run-test-funcs
}

soil-run() {
  run-test-funcs
}

"$@"
