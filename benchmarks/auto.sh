#!/usr/bin/env bash
#
# Run all the benchmarks on a given machine.
#
# Usage:
#   benchmarks/auto.sh <function name>
#
# List of benchmarks:
#
# - osh-parser
# - virtual-memory.sh -- vm-baseline, or mem-baseline
# - osh-runtime (now called runtime.sh, or wild-run)
# - oheap.sh?  For size, it doesn't need to be run on every machine.
# - startup.sh -- needs CSV
#   - this has many different snippets
#   - and it has strace

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # die
source benchmarks/common.sh  # default value of OSH_OVM
source services/common.sh  # find-dir-html

_banner() {
  echo -----
  echo "$@"
  echo -----
}

# Check that the code is correct before measuring performance!
prereq() {
  test/unit.sh all
  test/spec.sh all
}

osh-parser-quick() {
  ### Quick evaluation of the parser
  # Follow the instructions at the top of benchmarks/osh-parser.sh to use this

  local base_dir=${1:-../benchmark-data}

  # NOTE: This has to match benchmarks/osh-parser.sh print-tasks, which calls
  # filter-provenance on OSH_EVAL_BENCHMARK_DATA
  local osh_eval=$OSH_EVAL_BENCHMARK_DATA

  local c_prov prov
  c_prov=$(benchmarks/id.sh shell-provenance no-host \
    "${OTHER_SHELLS[@]}" $osh_eval python)
  prov=$(benchmarks/id.sh shell-provenance '' "${SHELLS[@]}" $osh_eval)

  # normally done on one machine
  benchmarks/osh-parser.sh measure $prov $base_dir/osh-parser

  # normally done on 2 machines
  benchmarks/osh-parser.sh measure-cachegrind $c_prov $base_dir/osh-parser
}

osh-parser-dup-testdata() {
  ### Quickly duplicate lenny testdata to flanders, for quick testing

  local raw_dir=../benchmark-data/osh-parser

  local -a a=($raw_dir/lenny.*.times.csv)
  local latest=${a[-1]}
  latest=${latest//.times.csv/}

  for name in $latest.*; do 
    local dest=${name//lenny/flanders}
    cp -r -v $name $dest
    if test -f $dest; then
      sed -i 's/lenny/flanders/g' $dest
    fi
  done
}

cachegrind-shells() {
  local base_dir=${1:-../benchmark-data}
  local osh_eval=${2:-$OSH_EVAL_BENCHMARK_DATA}

  # Python is considered a shell for benchmarks/compute
  local provenance
  provenance=$(benchmarks/id.sh shell-provenance no-host \
    "${OTHER_SHELLS[@]}" $osh_eval python)

  benchmarks/osh-parser.sh measure-cachegrind \
    $provenance $base_dir/osh-parser $osh_eval

}

cachegrind-builds() {
  echo TODO
}

benchmark-shell-provenance() {
  # empty label
  benchmarks/id.sh shell-provenance '' "${SHELLS[@]}" $OSH_EVAL_BENCHMARK_DATA python
}

measure-shells() {
  local base_dir=../benchmark-data

  # capture the filename
  local provenance
  provenance=$(benchmark-shell-provenance)

  benchmarks/vm-baseline.sh measure \
    $provenance $base_dir/vm-baseline
  benchmarks/osh-runtime.sh measure \
    $provenance $base_dir/osh-runtime
  benchmarks/osh-parser.sh measure \
    $provenance $base_dir/osh-parser
  benchmarks/compute.sh measure \
    $provenance $base_dir/compute
}

measure-builds() {
  local base_dir=../benchmark-data

  local provenance
  provenance=$(benchmarks/id.sh compiler-provenance)  # capture the filename

  benchmarks/ovm-build.sh measure $provenance $base_dir/ovm-build
}

# Run the whole benchmark from a clean git checkout.
# Before this, run devtools/release.sh benchmark-build.

all() {
  local do_cachegrind=${1:-}

  # Notes:
  # - During release, this happens on machine1, but not machine2
  # - Depends on oil-native being built
  if test -n "$do_cachegrind"; then
    cachegrind-shells '' $OSH_EVAL_BENCHMARK_DATA
    cachegrind-builds '' $OSH_EVAL_BENCHMARK_DATA
  fi

  measure-shells
  measure-builds
}

#
# Other
#

demo-tasks() {
  local provenance=$1

  # Strip everything after the first dot.
  local name=$(basename $provenance)
  local job_id=${name%.provenance.txt}

  echo "JOB ID: $job_id"

  # This is the pattern for iterating over shells.
  cat $provenance | while read _ _ _ sh_path _; do
    for i in 1 2 3; do
      echo $i $sh_path
    done
  done
}

travis() {
  local base_dir=_tmp/benchmark-data
  mkdir -p $base_dir

  cachegrind-shells $base_dir $OSH_EVAL_IN_TREE

  find-dir-html $base_dir
}

"$@"
