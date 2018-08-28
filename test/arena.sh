#!/bin/bash
#
# Usage:
#   ./arena.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: Need include guard in test/common.sh!  I ran into this before.
#source test/common.sh  # for all-passing, etc.
source test/wild-runner.sh  # For MANIFEST, etc.

_compare() {
  local path=$1

  mkdir -p _tmp/arena
  bin/osh --parse-and-print-arena $path > _tmp/arena/left.txt
  if diff -u $path _tmp/arena/left.txt; then
	  echo "$path"
  else
	  return 1
  fi
}

here-doc() {
  _compare test/arena/here-dq.sh
  _compare test/arena/here-sq.sh
  _compare test/arena/here-multiple.sh
  _compare test/arena/here-dq-indented.sh
}

tilde() {
  _compare test/arena/tilde.sh
}

_compare-wild() {
  local rel_path=$1
  local abs_path=$2

  _compare $abs_path
}

# Run on wild corpus
wild() {
  wc -l $MANIFEST
  cat $MANIFEST | xargs -n 2 -- $0 _compare-wild
}

readonly -a PASSING=(
  here-doc
  tilde
)

all-passing() {
  run-all "${PASSING[@]}"
}

run-for-release() {
  local out_dir=_tmp/arena
  mkdir -p $out_dir

  all-passing | tee $out_dir/log.txt

  echo "Wrote $out_dir/log.txt"
}

"$@"
