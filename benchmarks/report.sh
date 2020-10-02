#!/usr/bin/env bash
#
# Usage:
#   ./report.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # log

# TODO: Move stuff from osh-parser.sh, osh-runtime.sh, etc.
#
# stage1 : concatenate files from different machines
# stage2 : make CSV files with report.R
# stage3 : make HTML files.  Call 'print-report' function.


stage2() {
  local base_dir=$1  # _tmp/{osh-parser,osh-runtime,...}
  local action=$(basename $base_dir)

  local out=$base_dir/stage2
  mkdir -p $out

  R_LIBS_USER=$R_PATH benchmarks/report.R $action $base_dir/stage1 $out

  tree $out
}

stage3() {
  local base_dir=$1  # _tmp/{osh-parser,osh-runtime,...}
  local name=${2:-$(basename $base_dir)}
  local script=benchmarks/$name.sh

  local out=$base_dir/index.html
  mkdir -p $(dirname $out)

  $script print-report $base_dir/stage2 > $out

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

ovm-build() {
  local base_dir=_tmp/ovm-build

  benchmarks/ovm-build.sh stage1 ../benchmark-data/ovm-build
  stage2 $base_dir
  stage3 $base_dir
}

compute() {
  local base_dir=_tmp/compute

  benchmarks/compute.sh stage1 ../benchmark-data/compute
  stage2 $base_dir
  stage3 $base_dir
}

mycpp-examples() {
  # ./run.sh benchmark-all  in the mycpp/ dir produces this
  local base_dir=${1:-_tmp/mycpp-examples}
  mkdir -p $base_dir

  local dir2=$base_dir/stage2
  mkdir -p $dir2

  R_LIBS_USER=$R_PATH benchmarks/report.R mycpp $base_dir/raw $dir2

  stage3 $base_dir mycpp
}

all() {
  osh-parser
  osh-runtime
  vm-baseline
  ovm-build
  compute

  # Only run on one machine
  mycpp-examples
}

# For view
dev-index() {
  local out=_tmp/benchmarks.html
  for name in osh-parser osh-runtime vm-baseline ovm-build; do
    echo "<a href=\"$name/index.html\">$name</a> <br/>"
  done > $out
  log "Wrote $out"
}

"$@"
