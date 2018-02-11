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

measure-all() {
  local provenance=$1
  local base_dir=${2:-../benchmark-data}

  benchmarks/vm-baseline.sh measure $provenance $base_dir/vm-baseline
  benchmarks/osh-runtime.sh measure $provenance $base_dir/osh-runtime
  benchmarks/osh-parser.sh measure $provenance $base_dir/osh-parser
}

# Run the whole benchmark from a clean git checkout.
#
# Similar to scripts/release.sh build-and-test.
all() {
  test/spec.sh install-shells

  # Technically we need build-essential too?
  sudo apt install python-dev

  # Ideally I wouldn't need this, but the build process is not great now.
  make clean

  build/dev.sh all

  _banner 'OSH dev build'
  bin/osh -c 'echo OSH dev build'

  build/prepare.sh configure
  build/prepare.sh build-python

  make _bin/oil.ovm
  # This does what 'install' does.
  scripts/run.sh make-bin-links

  _banner 'OSH production build'

  _bin/osh -c 'echo OSH production build'

  local provenance
  provenance=$(benchmarks/id.sh shell-provenance)  # capture the filename

  measure-all $provenance

  # TODO:
  # record-compiler-provenance
  # benchmarks/ovm-build.sh measure $compiler_prov $base_dir/ovm-build
  # Note this has to happen AFTER a tarball is built.
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
