#!/bin/bash
#
# Run continuous build tasks.
#
# Usage:
#   ./toil-worker.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

dev-tasks() {
  ### Print tasks for the dev build

  # (name, script)

  cat <<EOF
lint            test/lint.sh
typecheck-slice types/oil-slice.sh
typecheck-other types/run.sh
unit            test/unit.sh
spec            test/spec.sh
EOF
}

time-tsv() {
  benchmarks/time_.py --tsv "$@"
}

run-dev-tasks() {
  local out_dir=_tmp/toil
  mkdir -p $out_dir

  # This data can go on the dashboard index
  local tsv=$out_dir/INDEX.tsv
  rm -f $tsv

  #export TRAVIS_SKIP=1
  dev-tasks | while read task_name script; do
    log "--- task: $task_name ---"

    local log=$out_dir/$task_name.log.txt 
    time-tsv -o $tsv --append --field $task_name --field $script -- \
      $script travis >$log 2>&1

    # show the last line

    echo
    echo $'status\telapsed\ttask\tscript'
    tail -n 1 $tsv
    echo
  done

  log '--- done ---'
  wc -l $out_dir/*
}

"$@"
