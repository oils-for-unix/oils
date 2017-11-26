#!/bin/bash
#
# Test the size of file, encoding, and decoding speed.
#
# Usage:
#   ./oheap.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

encode-one() {
  local script=$1
  local oheap_out=$2
  bin/osh -n --ast-format oheap "$script" > $oheap_out
}

task-spec() {
  while read path; do
    echo "$path _tmp/oheap/$(basename $path).oheap"
  done < benchmarks/osh-parser-files.txt 
}

run() {
  mkdir -p _tmp/oheap

  local results=_tmp/oheap/results.csv 
  echo 'status,elapsed_secs' > $results

  task-spec | xargs -n 2 --verbose -- \
    benchmarks/time.py --output $results -- \
    $0 encode-one
}

stats() {
  ls -l -h _tmp/oheap
  echo
  cat _tmp/oheap/results.csv
}

"$@"
