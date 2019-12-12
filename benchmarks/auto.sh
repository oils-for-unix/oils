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

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

# Notes:
# - $OSH_OVM is set by devtools/release.sh to the RELATIVE path of the
#   tar-built one.  Instead of the default of $PWD/_bin/osh.
# - These are NOT the versions of bash/dash/etc. in _tmp/spec-bin!  I
#   guess we should test distro-provided binaries.

readonly SHELLS=( bash dash mksh zsh bin/osh $OSH_OVM )

measure-shells() {
  local base_dir=${1:-../benchmark-data}

  local provenance
  # capture the filename
  provenance=$(benchmarks/id.sh shell-provenance "${SHELLS[@]}")

  benchmarks/vm-baseline.sh measure $provenance $base_dir/vm-baseline
  benchmarks/osh-runtime.sh measure $provenance $base_dir/osh-runtime

  # Note: we could also use _tmp/native-tar-test/*/_bin/osh_parse...
  local root=$PWD/../benchmark-data/src/oil-native-$OIL_VERSION
  local osh_parse=$root/_bin/osh_parse.opt.stripped

  local prov2
  prov2=$(benchmarks/id.sh shell-provenance "${SHELLS[@]}" $osh_parse)

  benchmarks/osh-parser.sh measure $prov2 $base_dir/osh-parser
}

# Quick evaluation of the parser
osh-parser-quick() {
  local base_dir=${1:-../benchmark-data}

  # REPO VERSION
  local osh_parse=_bin/osh_parse.opt.stripped

  local prov2
  prov2=$(benchmarks/id.sh shell-provenance bash dash mksh yash $osh_parse)

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
  # NOTE: Depends on oil-native being built
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
