#!/bin/bash
#
# Usage:
#   ./report.sh <function name>

set -o nounset
set -o pipefail
set -o errexit


# TODO: Move stuff from osh-parser.sh, osh-runtime.sh, etc.
#
# stage1 : concatenate files from different machines
# stage2 : make CSV files with report.R
# stage3 : make HTML files.  Call the 'print-report function here.


stage2() {
  local base_dir=$1  # _tmp/{osh-parser,osh-runtime,...}
  local action=$(basename $base_dir)

  local out=$base_dir/stage2
  mkdir -p $out

  benchmarks/report.R $action $base_dir/stage1 $out

  tree $out
}

stage3() {
  local base_dir=$1  # _tmp/{osh-parser,osh-runtime,...}
  local name=$(basename $base_dir)
  local script=benchmarks/$name.sh

  local out=$base_dir/index.html
  mkdir -p $(dirname $out)

  $script print-report $base_dir/stage2 > $out

  cp -v benchmarks/benchmarks.css $base_dir
  echo "Wrote $out"
}

osh-parser() {
  local base_dir=_tmp/osh-parser

  benchmarks/osh-parser.sh stage1 ../benchmark-data/osh-parser
  stage2 $base_dir
  stage3 $base_dir
}

osh-runtime() {
  local base_dir=_tmp/osh-runtime

  benchmarks/osh-runtime.sh stage1 ../benchmark-data/osh-runtime
  stage2 $base_dir
  stage3 $base_dir
}

# NOTE: This is just processing
vm-baseline() {
  local base_dir=_tmp/vm-baseline

  benchmarks/vm-baseline.sh stage1 ../benchmark-data/vm-baseline
  stage2 $base_dir
  stage3 $base_dir
}

# This is one is specific to a particular machine.
oheap() {
  local base_dir=_tmp/oheap

  benchmarks/oheap.sh stage1 
  stage2 $base_dir
  stage3 $base_dir
}

"$@"
