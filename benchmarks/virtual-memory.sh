#!/bin/bash
#
# Usage:
#   ./virtual-memory.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: What format should this be recorded in?
# I think a Python script can parse it to CSV / TSV2.
# Use benchmark/id.sh too

baseline() {
  local host=$(hostname)
  local job_id="$host.$(date +%Y-%m-%d__%H-%M-%S)"
  local out_dir="../benchmark-data/vm-baseline/$job_id"
  mkdir -p $out_dir

  local tmp_dir
  tmp_dir=_tmp/host-id/$host
  benchmarks/id.sh dump-host-id $tmp_dir

  local host_hash=$(benchmarks/id.sh publish-host-id $tmp_dir)
  echo $host $host_hash

  local shell_hash

  # NOTE: for some reason zsh when printing /proc/$$/status gets a cat process,
  # not a zsh process?  Check out /proc/$$/maps too.  Omitting it for now.

  for sh_path in bash dash mksh bin/osh _bin/osh; do
    echo "--- $sh_path"

    local sh_name=$(basename $sh_path)

    tmp_dir=_tmp/shell-id/$sh_name
    benchmarks/id.sh dump-shell-id $sh_path $tmp_dir

    shell_hash=$(benchmarks/id.sh publish-shell-id $tmp_dir)

    # There is a race condition on the status but sleep helps.
    local out="$out_dir/${sh_name}-${shell_hash}.txt"
    $sh_path -c 'sleep 0.001; cat /proc/$$/status' > $out

    echo "Wrote $out"
    echo 
  done
}

# TODO: parse 10 osh-parser files, measure virtual memory at the end.  However
# this only applies to OSH, because you need a hook to dump the /proc/$$/status
# file.

demo() {
  local out=_tmp/virtual-memory
  mkdir -p $out

  # VmRSS: 46 MB for abuild, 200 MB for configure!  That is bad.  This
  # benchmark really is necessary.

  local input=benchmarks/testdata/abuild
  #local input=benchmarks/testdata/configure

  bin/osh \
    --dump-proc-status-to $out/demo.txt \
    $input

  cat $out/demo.txt
}

"$@"
