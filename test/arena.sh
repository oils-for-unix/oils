#!/bin/bash
#
# Usage:
#   ./arena.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

compare() {
  local path=$1

  mkdir -p _tmp/arena
  bin/osh --parse-and-print-arena $path > _tmp/arena/left.txt
  diff -u $path _tmp/arena/left.txt
}

here-doc() {
  compare test/arena/here-dq.sh
  compare test/arena/here-sq.sh
  compare test/arena/here-multiple.sh
}

readonly -a PASSING=(
  here-doc
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
