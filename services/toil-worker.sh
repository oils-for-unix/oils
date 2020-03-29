#!/bin/bash
#
# Run continuous build tasks.
#
# Usage:
#   ./toil-worker.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source services/common.sh

time-tsv() {
  benchmarks/time_.py --tsv "$@"
}

dump-timezone() {

  # On Travis:
  #  /usr/share/zoneinfo/UTC
  # On my machine
  #  /usr/share/zoneinfo/America/Los_Angeles

  read md5 _ <<< $(md5sum /etc/localtime)
  log "md5 = $md5"
  find /usr/share/zoneinfo -type f | xargs md5sum | grep $md5
}

dummy-tasks() {
  ### Print tasks that execute quickly

  # (task_name, script, action, result_html)
  cat <<EOF
dump-env      services/toil-worker.sh dump-env      -
dump-timezone services/toil-worker.sh dump-timezone -
EOF
}

run-dummy() {
  dummy-tasks | run-tasks
}

dev-minimal-tasks() {
  ### Print tasks for the 'dev-minimal' build

  # (task_name, script, action, result_html)
  cat <<EOF
build-minimal   build/dev.sh minimal        -
lint            test/lint.sh travis         -
typecheck-slice types/oil-slice.sh travis   -
typecheck-other types/run.sh travis         -
unit            test/unit.sh travis         -
oil-spec        test/spec.sh oil-all-serial _tmp/spec/oil.html
osh-minimal     test/spec.sh osh-minimal    _tmp/spec/osh-minimal.html
EOF
}

dev-all-nix-tasks() {
  ### Print tasks for the 'dev-all' build

  # (task_name, script, action, result_html)
  cat <<EOF
build-all       build/dev.sh all            -
oil-spec        test/spec.sh oil-all-serial _tmp/spec/oil.html
osh-spec        test/spec.sh osh-travis     _tmp/spec/osh.html
EOF
}


# https://github.com/oilshell/oil/wiki/Contributing

ovm-tarball-tasks() {
  ### Print tasks for the 'ovm-tarball' build

  # note: dev-all needed to crawl dependencies to make tarball.

  # (task_name, script, action, result_html)
  cat <<EOF
tarball-deps      devtools/release.sh tarball-build-deps -
spec-deps         test/spec-bin.sh all-steps             -
dev-all           build/dev.sh all                       -
yajl              build/dev.sh yajl-release              -
syscall-by-code   test/syscall.sh by-code                _tmp/syscall/by-code.txt
syscall-by-input  test/syscall.sh by-input               _tmp/syscall/by-input.txt
osh-spec          test/spec.sh osh-travis                _tmp/spec/osh.html
make-tarball      devtools/release.sh quick-oil-tarball  -
build-tarball     build/test.sh oil-tar                  -
EOF
}

run-tasks() {
  ### Run the tasks on stdin and write _tmp/toil/INDEX.tsv.

  local out_dir=_tmp/toil
  mkdir -p $out_dir

  # For the later deploy step to pick up
  date +%s > $out_dir/task-run-start-time.txt

  # This data can go on the dashboard index
  local tsv=$out_dir/INDEX.tsv
  rm -f $tsv

  local max_status=0

  while read task_name script action result_html; do
    log "--- task: $task_name ---"

    local log_path=$out_dir/$task_name.log.txt 

    set +o errexit
    time-tsv -o $tsv --append --time-fmt '%.2f' \
      --field $task_name --field $script --field $action \
      --field $result_html -- \
      $script $action >$log_path 2>&1
    status=$?
    set -o errexit

    if test $status -gt $max_status; then
      max_status=$status
    fi

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
    ' $tsv
  fi

  # So the deploy step can fail later
  echo $max_status > $out_dir/exit-status.txt
}

run-dev-minimal() {
  ### Travis job dev-minimal

  #export TRAVIS_SKIP=1
  dev-minimal-tasks | run-tasks
}

allow-job-failure() {
  # Note: toil_web.py will still count failures in INDEX.tsv.  This just
  # prevents Travis from failing.

  local out='_tmp/toil/exit-status.txt '
  log "*** ALLOWING JOB FAILURE by overwriting $out ***"
  echo 0 > $out
}

_run-dev-all-nix() {
  dev-all-nix-tasks | run-tasks

  allow-job-failure

  return

  # --- DEBUGGING THROUGH STDOUT ---

  # makes _tmp
  build/dev.sh all

  # So we have something to deploy
  dummy-tasks | run-tasks

  if false; then
    test/spec.sh check-shells-exist
    # this hangs because nix bash doesn't have 'compgen' apparently
    test/spec.sh builtin-completion -v -t
  fi

  test/spec.sh osh-travis

}

run-ovm-tarball() {
  ovm-tarball-tasks | run-tasks
}

run-dev-all-nix() {
  ### Travis job dev-all-nix

  # Run tasks the nix environment
  nix-shell \
    --argstr dev "none" \
    --argstr test "none" \
    --argstr cleanup "none" \
    --run "$0 _run-dev-all-nix"
}

"$@"
