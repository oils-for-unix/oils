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
source benchmarks/id.sh

_banner() {
  echo -----
  echo "$@"
  echo -----
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
  local host_name=$1
  local host_job_id=$2

  # TODO:

  # capture the filename
  local provenance
  # pass empty label, so it writes to ../benchmark-data/{shell,host}-id
  provenance=$(benchmarks/id.sh shell-provenance '' \
    "${SHELLS[@]}" $OSH_EVAL_BENCHMARK_DATA python2
  )

  local out_dir=../benchmark-data

  #local name
  #name=$(basename $provenance)
  #local host_job_id=${name%.provenance.txt}  # strip suffix

  benchmarks/vm-baseline.sh measure \
    $provenance $host_job_id $out_dir/vm-baseline

  benchmarks/osh-runtime.sh measure \
    $host_name $host_job_id $OSH_EVAL_BENCHMARK_DATA $out_dir/osh-runtime

  # TODO: Either
  # (OLD) cp -v _tmp/provenance.txt $out_dir/osh-runtime/$host.$job_id.provenance.txt
  # (NEW) cp -v _tmp/provenance.tsv $out_dir/osh-runtime/raw.$host.$job_id/
  #
  # Eliminate $job_id calculation from shell-provenance altogether
  # All soil-shell-provenance callers should just pass $job_id and $maybe_host

  # SAVE provenance so you know which 2 machines a benchmark ran on
  cp -v $provenance $out_dir/osh-runtime

  benchmarks/osh-parser.sh measure \
    $provenance $host_job_id $out_dir/osh-parser
  benchmarks/compute.sh measure \
    $provenance $host_job_id $out_dir/compute
}

measure-builds() {
  local base_dir=../benchmark-data

  local provenance
  provenance=$(benchmarks/id.sh compiler-provenance)  # capture the filename

  benchmarks/ovm-build.sh measure $provenance $base_dir/ovm-build
}

# Run all benchmarks from a clean git checkout.
# Before this, run devtools/release.sh benchmark-build.

all() {
  local do_machine1=${1:-}

  local host_name
  host_name=$(hostname)  # Running on multiple machines

  # TODO: Pass this to shell-provenance-2, and to all 'measure' functions
  local job_id
  job_id=$(print-job-id)

  local host_job_id="$host_name.$job_id"

  # Notes:
  # - During release, this happens on machine1, but not machine2
  # - Depends on oil-native being built
  if test -n "$do_machine1"; then
    # Only run on one machine
    benchmarks/mycpp.sh soil-run
    benchmarks/gc.sh soil-run

    benchmarks/osh-parser.sh cachegrind-main $host_job_id ''
  fi

  measure-shells $host_name $host_job_id
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
