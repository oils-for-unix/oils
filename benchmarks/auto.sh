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

osh-parser-quick() {
  ### Quick evaluation of the parser
  # Follow the instructions at the top of benchmarks/osh-parser.sh to use this

  local base_dir=${1:-../benchmark-data}

  local c_prov prov
  c_prov=$(benchmarks/id.sh shell-provenance no-host \
    "${OTHER_SHELLS[@]}" $OIL_NATIVE python2)
  prov=$(benchmarks/id.sh shell-provenance '' "${SHELLS[@]}" $OIL_NATIVE)

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

measure-shells() {
  local base_dir=../benchmark-data

  # capture the filename
  local provenance
  provenance=$(our-shell-provenance)

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
  local do_machine1=${1:-}

  # Notes:
  # - During release, this happens on machine1, but not machine2
  # - Depends on oil-native being built
  if test -n "$do_machine1"; then
    # Only run on one machine
    benchmarks/mycpp.sh soil-run
    benchmarks/gc.sh soil-run

    benchmarks/osh-parser.sh cachegrind-main '' $OIL_NATIVE
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
