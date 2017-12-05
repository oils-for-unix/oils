#!/bin/bash
#
# Usage:
#   ./virtual-memory.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh  # log

# TODO: Call this from benchmarks/auto.sh.

vm-baseline() {
  local provenance=$1
  local base_dir=${2:-_tmp/vm-baseline}
  #local base_dir=${2:-../benchmark-data/vm-baseline}

  # Strip everything after the first dot.
  local name=$(basename $provenance)
  local job_id=${name%%.*}

  log "--- Job $job_id ---"

  local host=$(hostname)
  local out_dir="$base_dir/$host.$job_id"
  mkdir -p $out_dir

  # Fourth column is the shell.
  cat $provenance | while read _ _ _ sh_path shell_hash; do
    local sh_name=$(basename $sh_path)

    # There is a race condition on the status but sleep helps.
    local out="$out_dir/${sh_name}-${shell_hash}.txt"
    $sh_path -c 'sleep 0.001; cat /proc/$$/status' > $out
  done

  echo
  echo "$out_dir:"
  ls -l $out_dir
}

csv-demo() {
  local -a job_dirs=(_tmp/vm-baseline/lisa.2017-*)
  benchmarks/virtual_memory.py baseline ${job_dirs[-1]}
}

# Combine CSV files.
baseline-csv() {
  local raw_dir=$1
  local out=_tmp/vm-baseline/stage1
  mkdir -p $out

  # Globs are in lexicographical order, which works for our dates.
  local -a m1=(../benchmark-data/vm-baseline/flanders.*)
  local -a m2=(../benchmark-data/vm-baseline/lisa.*)

  # The last one
  local -a latest=(${m1[-1]} ${m2[-1]})

  benchmarks/virtual_memory.py baseline "${latest[@]}" \
    | tee $out/vm-baseline.csv
}

# Demo of the --dump-proc-status-to flag.
# NOTE: Could also add Python introspection.
parser-dump-demo() {
  local out_dir=_tmp/virtual-memory
  mkdir -p $out_dir

  # VmRSS: 46 MB for abuild, 200 MB for configure!  That is bad.  This
  # benchmark really is necessary.
  local input=benchmarks/testdata/abuild

  bin/osh \
    --parser-mem-dump $out_dir/parser.txt -n --ast-format none \
    $input

  grep '^Vm' $out_dir/parser.txt
}

runtime-dump-demo() {
  # Multiple processes
  #OIL_TIMING=1 bin/osh -c 'echo $(echo hi)'

  local out_dir=_tmp/virtual-memory
  mkdir -p $out_dir
  bin/osh \
    --parser-mem-dump $out_dir/parser.txt \
    --runtime-mem-dump $out_dir/runtime.txt \
    -c 'echo $(echo hi)'

  grep '^Vm' $out_dir/parser.txt $out_dir/runtime.txt
}

"$@"
