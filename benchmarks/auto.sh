#!/usr/bin/env bash
#
# Run all the benchmarks on a given machine.
#
# Usage:
#   benchmarks/auto.sh <function name>
#
# List of benchmarks:
#
# - Single Machine (for now):
#   - mycpp-examples
#   - gc
# - Multiple machines
#   - osh-parser
#   - osh-runtime
#   - vm-baseline
#   - compute
#     - awk-python could be moved here
#     - startup.sh could be moved here, it also has strace counts
#   - ovm-build

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # die
source benchmarks/common.sh  # default value of OSH_OVM

_banner() {
  echo -----
  echo "$@"
  echo -----
}

our-shell-provenance() {
  ### The list of programs we compare

  # empty label
  benchmarks/id.sh shell-provenance '' "${SHELLS[@]}" $OSH_EVAL_BENCHMARK_DATA python2
}

  # New interface for shell-provenance
  # 3 fixed inputs:
  #   maybe_host   - 'lenny' or 'no-host'
  #   job_id       - use $(print-job-timestamp)
  #   out_dir      - location for put shell-id, host-id, but TSV is first
  #                  written to _tmp/provenance.tsv, and later COPIED TO EACH
  #                  $out_dir/$bench_name/$host_job_id/ dir
  # Variable inputs:
  #   list of shells

  # shell-provenance-tsv 'no-host' $(print-job-id) _tmp \
  #   bash dash bin/osh $OSH_EVAL_NINJA_BUILD

  # shell-provenance-tsv 'lenny' $(print-job-id) ../benchmark-data \
  #   bash dash bin/osh $OSH_EVAL_BENCHMARK_DATA
  #
  # - A key problem is that you need to concat the two provenances
  #   - and CHECK that you're comparing the same shells!
  #   - the number of hosts should be 2, and they should have an equal number
  #   of rows
  #   - and there should be exactly 2 of every hash?

measure-shells() {
  local out_dir=../benchmark-data

  # capture the filename
  local provenance
  provenance=$(our-shell-provenance)

  local host
  host=$(hostname)  # Running on multiple machines

  benchmarks/vm-baseline.sh measure \
    $provenance $out_dir/vm-baseline

  # TODO: 'shell-provenance' could just print host and job ID
  local name
  name=$(basename $provenance)
  local host_job_id=${name%.provenance.txt}  # strip suffix
  benchmarks/osh-runtime.sh measure \
    $host_job_id $host $OSH_EVAL_BENCHMARK_DATA $out_dir/osh-runtime

  # SAVE provenance so you know which 2 machines a benchmark ran on
  cp -v $provenance $out_dir/osh-runtime

  benchmarks/osh-parser.sh measure \
    $provenance $out_dir/osh-parser
  benchmarks/compute.sh measure \
    $provenance $out_dir/compute
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
  local do_machine1=${1:-}

  # Notes:
  # - During release, this happens on machine1, but not machine2
  # - Depends on oil-native being built
  if test -n "$do_machine1"; then
    # Only run on one machine
    benchmarks/mycpp.sh soil-run
    benchmarks/gc.sh soil-run

    benchmarks/osh-parser.sh cachegrind-main ''
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

"$@"
