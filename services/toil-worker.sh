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

dev-minimal-tasks() {
  ### Print tasks for the dev build

  # (task_name, script, action, result_html)
  cat <<EOF
build-minimal   build/dev.sh minimal        -
lint            test/lint.sh travis         -
typecheck-slice types/oil-slice.sh travis   -
typecheck-other types/run.sh travis         -
unit            test/unit.sh travis         -
oil-spec        test/spec.sh oil-all-serial _tmp/spec/oil.html
osh-spec        test/spec.sh osh-travis     _tmp/spec/osh.html
EOF
}

time-tsv() {
  benchmarks/time_.py --tsv "$@"
}

run-dev-minimal() {
  local out_dir=_tmp/toil
  mkdir -p $out_dir

  # This data can go on the dashboard index
  local tsv=$out_dir/INDEX.tsv
  rm -f $tsv

  #export TRAVIS_SKIP=1
  dev-minimal-tasks | while read task_name script action result_html; do
    log "--- task: $task_name ---"

    local log_path=$out_dir/$task_name.log.txt 

    set +o errexit
    time-tsv -o $tsv --append --field $task_name --field $script --field $action --field $result_html -- \
      $script $action >$log_path 2>&1
    set -o errexit

    # show the last line

    echo
    echo $'status\telapsed\ttask\tscript\taction\tresult_html'
    tail -n 1 $tsv
    echo
  done

  log '--- done ---'
  wc -l $out_dir/*

  # This suppressed the deployment of logs, which we don't want.  So all our
  # Travis builds succeed?  But then we can't use their failure notifications
  # (which might be OK).
  if false; then
    # exit with the maximum exit code.
    awk '
    BEGIN { max = 0 }
          { if ($1 > max) { max = $1 } }
    END   { exit(max) }
    ' _tmp/toil/INDEX.tsv
  fi
}

"$@"
