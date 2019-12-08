#!/bin/bash
#
# Run all the benchmarks on a given machine.
#
# Usage:
#   ./auto.sh <function name>
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

measure-shells() {
  local base_dir=${1:-../benchmark-data}

  if true; then  # to skip to parsing
    local provenance
    provenance=$(benchmarks/id.sh shell-provenance)  # capture the filename

    benchmarks/vm-baseline.sh measure $provenance $base_dir/vm-baseline
    benchmarks/osh-runtime.sh measure $provenance $base_dir/osh-runtime
  fi

  # Note: we could also use _tmp/native-tar-test/*/_bin/osh_parse...
  local osh_parse=_bin/osh_parse.opt.stripped

  local prov2
  prov2=$(benchmarks/id.sh shell-provenance $osh_parse)

  benchmarks/osh-parser.sh measure $prov2 $base_dir/osh-parser
}

measure-builds() {
  local base_dir=${1:-../benchmark-data}

  local provenance
  provenance=$(benchmarks/id.sh compiler-provenance)  # capture the filename

  benchmarks/ovm-build.sh measure $provenance $base_dir/ovm-build
}

# Run the whole benchmark from a clean git checkout.
# Before this, run scripts/release.sh benchmark-build.

all() {
  # prequisite
  build/mycpp.sh compile-osh-parse-opt

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
