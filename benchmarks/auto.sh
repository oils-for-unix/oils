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

measure-shells() {
  local host_name=$1
  local job_id=$2
  local out_dir=$3

  local host_job_id="$host_name.$job_id"

  local raw_out_dir

  raw_out_dir="$out_dir/osh-runtime/raw.$host_job_id"
  benchmarks/osh-runtime.sh measure \
    $host_name $raw_out_dir $OSH_CPP_BENCHMARK_DATA

  # Old style uses provenance.txt.  TODO: use raw_out_dir everywhere
  local provenance=_tmp/provenance.txt

  raw_out_dir="$out_dir/vm-baseline/raw.$host_job_id"
  benchmarks/vm-baseline.sh measure \
    $provenance $host_job_id $out_dir/vm-baseline

  raw_out_dir="$out_dir/vm-baseline/raw.$host_job_id"
  benchmarks/osh-parser.sh measure \
    $provenance $host_job_id $out_dir/osh-parser

  raw_out_dir="$out_dir/compute/raw.$host_job_id"
  benchmarks/compute.sh measure \
    $provenance $host_job_id $out_dir/compute
}

# Run all benchmarks from a clean git checkout.
# Before this, run devtools/release.sh benchmark-build.

all() {
  local do_machine1=${1:-}
  local resume1=${2:-}  # skip past measure-shells

  local host_name
  host_name=$(hostname)  # Running on multiple machines

  local job_id
  job_id=$(print-job-id)

  local host_job_id="$host_name.$job_id"
  local out_dir='../benchmark-data'

  benchmarks/id.sh shell-provenance-2 \
    $host_name $job_id $out_dir \
    "${SHELLS[@]}" $OSH_CPP_BENCHMARK_DATA python2

  # Notes:
  # - During release, this happens on machine1, but not machine2
  if test -n "$do_machine1"; then
    # Only run on one machine
    benchmarks/uftrace.sh soil-run
    benchmarks/mycpp.sh soil-run
    benchmarks/gc.sh run-for-release
    benchmarks/gc-cachegrind.sh soil-run

    benchmarks/osh-parser.sh measure-cachegrind \
      _tmp/provenance.txt $host_job_id $out_dir/osh-parser $OSH_CPP_BENCHMARK_DATA
  fi

  if test -z "${resume1:-}"; then
    measure-shells $host_name $job_id $out_dir
  fi

  compiler-provenance-2 \
    $host_name $job_id $out_dir

  local raw_out_dir
  raw_out_dir="$out_dir/ovm-build/raw.$host_job_id"

  local build_prov=_tmp/compiler-provenance.txt
  benchmarks/ovm-build.sh measure $build_prov $raw_out_dir
}

"$@"
