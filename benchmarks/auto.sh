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

# Run the whole benchmark from a clean git checkout.
#
# Similar to scripts/release.sh build-and-test.
all() {
  test/spec.sh install-shells

  # Technically we need build-essential too?
  sudo apt install python-dev

  build/dev.sh all
  build/codegen.sh lexer

  _banner 'OSH dev build'
  bin/osh -c 'echo OSH dev build'

  build/prepare.sh configure
  build/prepare.sh build-python

  make _bin/oil.ovm
  # This does what 'install' does.
  scripts/run.sh make-bin-links

  _banner 'OSH production build'

  _bin/osh -c 'echo OSH production build'

  # Make observations.
  # TODO: Factor shell-id / host-id here.  Every benchmark will use that.

  # Just write a task file, like _tmp/benchmark-tasks.txt?
  # And then have a function to execute the tasks.
  # It has to make the write CSV files?

  benchmarks/osh-parser.sh run

  # Now osh-parser.sh report is run on a single machine.
}

# Writes a table of host and shells to stdout.  Writes text files and
# calculates IDs for them as a side effect.
#
# The table can be passed to other benchmarks to ensure that their provenance
# is recorded.
#
# TODO: Move to id.sh/provenance.sh?

record-provenance() {
  local job_id=$1

  local host
  host=$(hostname)

  # Write Header of the CSV file that is appended to.
  #echo 'host_name,host_hash,shell_name,shell_hash'

  local tmp_dir=_tmp/host-id/$host
  benchmarks/id.sh dump-host-id $tmp_dir

  local host_hash
  host_hash=$(benchmarks/id.sh publish-host-id $tmp_dir)
  #echo $host $host_hash

  local shell_hash

  #for sh_path in bash dash mksh zsh; do
  for sh_path in bash dash mksh zsh bin/osh _bin/osh; do
    # There will be two different OSH
    local name=$(basename $sh_path)

    tmp_dir=_tmp/shell-id/$name
    benchmarks/id.sh dump-shell-id $sh_path $tmp_dir

    shell_hash=$(benchmarks/id.sh publish-shell-id $tmp_dir)

    #echo "$sh_path ID: $shell_hash"

    echo "$job_id $host $host_hash $sh_path $shell_hash"
  done
}

write-provenance-txt() {
  local job_id
  job_id="$(date +%Y-%m-%d__%H-%M-%S)"

  local host
  host=$(hostname)

  # NOTE: This could be a TSV file?

  local out=_tmp/${host}.${job_id}.provenance.txt

  # Job ID should be here
  record-provenance $job_id > $out

  echo "Wrote $out"
}

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
