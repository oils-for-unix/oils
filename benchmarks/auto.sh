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

make-prov() {
  ### Make a list of all runtimes we want to test

  local in_tree=${1:-}  # pass T to get the one in tree
  local osh_eval

  # Test the one in the repo
  if test -n "$in_tree"; then
    osh_eval=_bin/osh_eval.opt.stripped
  else
    osh_eval=$OSH_EVAL_BENCHMARK_DATA
  fi

  # Python is considered a shell for benchmarks/compute
  benchmarks/id.sh shell-provenance "${SHELLS[@]}" $osh_eval python
}

measure-shells() {
  local do_cachegrind=${1:-}
  local base_dir=../benchmark-data

  # capture the filename
  local provenance
  provenance=$(make-prov)

  benchmarks/vm-baseline.sh measure $provenance $base_dir/vm-baseline
  benchmarks/osh-runtime.sh measure $provenance $base_dir/osh-runtime
  benchmarks/osh-parser.sh measure $provenance $base_dir/osh-parser
  benchmarks/compute.sh measure $provenance $base_dir/compute
}

osh-parser-quick() {
  ### Quick evaluation of the parser
  local base_dir=${1:-../benchmark-data}

  # REPO VERSION
  local osh_eval=_bin/osh_eval.opt.stripped

  local prov2
  prov2=$(benchmarks/id.sh shell-provenance "${SHELLS[@]}" $osh_eval)

  benchmarks/osh-parser.sh measure $prov2 $base_dir/osh-parser
}

osh-parser-dup-testdata() {
  ### Quickly duplicate lisa testdata to flanders, for quick testing

  local raw_dir=../benchmark-data/osh-parser

  local -a a=($raw_dir/lisa.*.times.csv)
  local latest=${a[-1]}
  latest=${latest//.times.csv/}

  for name in $latest.*; do 
    local dest=${name//lisa/flanders}
    cp -r -v $name $dest
    sed -i 's/lisa/flanders/g' $dest
  done
}

measure-builds() {
  local do_cachegrind=${1:-}
  local base_dir=../benchmark-data

  local provenance
  provenance=$(benchmarks/id.sh compiler-provenance)  # capture the filename

  benchmarks/ovm-build.sh measure $provenance $base_dir/ovm-build
}

# Run the whole benchmark from a clean git checkout.
# Before this, run devtools/release.sh benchmark-build.

all() {
  local do_cachegrind=${1:-}

  # NOTE: Depends on oil-native being built
  measure-shells "$do_cachegrind"
  measure-builds "$do_cachegrind"
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
