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

measure-shells() {
  local host_name=$1
  local job_id=$2

  local out_dir=../benchmark-data
  benchmarks/id.sh shell-provenance-2 \
    $host_name $job_id $out_dir \
    "${SHELLS[@]}" $OSH_EVAL_BENCHMARK_DATA python2
  )

  local host_job_id="$host_name.$job_id"
  local raw_out_dir="$out_dir/raw.$host_job_id"

  # New Style doesn't need provenance -- it's joined later
  benchmarks/osh-runtime.sh measure \
    $host_name $raw_out_dir $OSH_EVAL_BENCHMARK_DATA $out_dir/osh-runtime

  # Old style needs provenance
  local provenance=_tmp/provenance.txt

  benchmarks/vm-baseline.sh measure \
    $provenance $host_job_id $out_dir/vm-baseline

  benchmarks/osh-parser.sh measure \
    $provenance $host_job_id $out_dir/osh-parser

  benchmarks/compute.sh measure \
    $provenance $host_job_id $out_dir/compute
}

measure-builds() {
  # TODO: Use new provenance style, like measure-shells
  #local host_name=$1
  #local job_id=$2

  local out_dir=../benchmark-data

  local provenance
  provenance=$(benchmarks/id.sh compiler-provenance)  # capture the filename

  benchmarks/ovm-build.sh measure $provenance $out_dir/ovm-build
}

# Run all benchmarks from a clean git checkout.
# Before this, run devtools/release.sh benchmark-build.

all() {
  local do_machine1=${1:-}

  local host_name
  host_name=$(hostname)  # Running on multiple machines

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

  measure-shells $host_name $job_id
  measure-builds # $host_name $job_id
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
