#!/usr/bin/env bash
#
# cachegrind gives instruction counts
#
# Usage:
#   benchmarks/cachegrind.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source benchmarks/common.sh

with-cachegrind() {
  ### Run a command under cachegrind, writing to $out_file
  local out_file=$1
  shift

  valgrind --tool=cachegrind \
    --log-file=$out_file \
    --cachegrind-out-file=/dev/null \
    -- "$@"

  log "Wrote $out_file"
}

file=$(basename $0)
if test $file = 'cachegrind.sh'; then
  "$@"
fi
