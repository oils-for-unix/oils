#!/usr/bin/env bash
#
# Wrapper for soil/web.py.
#
# Usage:
#   soil/web.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

shopt -s nullglob  # for list-json

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

source $REPO_ROOT/soil/common.sh

readonly NUM_JOBS=1000  # jobs to show and keep

soil-web() {
  PYTHONPATH=$REPO_ROOT $REPO_ROOT/soil/web.py "$@"
}

# Bug fix for another race:
# ls *.json has a race: the shell expands files that may no longer exist, and
# then 'ls' fails!
list-json() {
  local dir=$1  # e.g. travis-ci.oilshell.org/github-jobs

  for name in $dir/*/*.json; do
    echo $name
  done
}

rewrite-jobs-index() {
  ### Atomic update of travis-ci.oilshell.org/jobs/
  local prefix=$1
  local run_id=$2   # pass GITHUB_RUN_NUMBER or git-$hash

  local dir=~/travis-ci.oilshell.org/${prefix}jobs

  log "soil-web: Rewriting ${prefix}jobs/index.html"

  # Fix for bug #1169: don't create the temp file on a different file system,
  # which /tmp may be.
  #
  # When the source and target are on different systems, I believe 'mv' falls
  # back to 'cp', which has this race condition:
  #
  # https://unix.stackexchange.com/questions/116280/cannot-create-regular-file-filename-file-exists

  # Limit to last 100 jobs.  Glob is in alphabetical order and jobs look like
  # 2020-03-20__...

  local index_tmp=$dir/$$.index.html  # index of every job in every run
  local run_index_tmp=$dir/$$.runs.html  # only the jobs in this run/commit

  list-json $dir \
    | tail -n -$NUM_JOBS \
    | soil-web ${prefix}index $index_tmp $run_index_tmp $run_id

  echo "rewrite index status = ${PIPESTATUS[@]}"

  mv -v $index_tmp $dir/index.html

  mkdir -v -p $dir/$run_id  # this could be a new commit hash, etc.
  mv -v $run_index_tmp $dir/$run_id/index.html
}

cleanup-jobs-index() {
  local prefix=$1
  local dry_run=${2:-true}

  local dir=~/travis-ci.oilshell.org/${prefix}jobs

  # Pass it all JSON, and then it figures out what files to delete (TSV, etc.)
  case $dry_run in
    false)
      # Bug fix: There's a race here when 2 jobs complete at the same time.
      # Use rm -f to ignore failure if the file was already deleted.

      list-json $dir | soil-web cleanup $NUM_JOBS | xargs --no-run-if-empty -- rm -f -v
      ;;
    true)
      list-json $dir | soil-web cleanup $NUM_JOBS
      ;;
    *)
      log 'Expected true or false for dry_run'
  esac
}

test-cleanup() {
  # the 999 jobs are the oldest

  soil-web cleanup 2 <<EOF
travis-ci.oilshell.org/github-jobs/999/one.json
travis-ci.oilshell.org/github-jobs/999/two.json
travis-ci.oilshell.org/github-jobs/999/three.json
travis-ci.oilshell.org/github-jobs/1000/one.json
travis-ci.oilshell.org/github-jobs/1000/two.json
travis-ci.oilshell.org/github-jobs/1001/one.json
travis-ci.oilshell.org/github-jobs/1001/two.json
travis-ci.oilshell.org/github-jobs/1001/three.json
EOF
}

cleanup-status-api() {
  ### cleanup the files used for maybe-merge

  local dry_run=${1:-true}

  local dir=~/travis-ci.oilshell.org/status-api/github

  pushd $dir
  case $dry_run in
    false)
      # delete all but the last 30
      ls | head -n -30 | xargs --no-run-if-empty -- rm -r -f -v
      ;;
    true)
      ls | head -n -30
      ;;
    *)
      log 'Expected true or false for dry_run'
  esac
  popd
}

event-job-done() {
  ### "Server side" handler

  local prefix=$1  # 'github-' or 'srht-'
  local run_id=$2  # $GITHUB_RUN_NUMBER or git-$hash

  rewrite-jobs-index $prefix $run_id

  # note: we could speed jobs up by doing this separately?
  cleanup-jobs-index $prefix
}

#
# Dev Tools
#

sync-testdata() {

  local dest=_tmp/github-jobs/

  rsync --archive --verbose \
    $SOIL_USER@$SOIL_HOST:$SOIL_HOST/github-jobs/ $dest

  # 2023-04: 3.2 GB of files!  Probably can reduce this

  du --si -s $dest
}

copy-web() {
  ### for relative URLs to work

  cp -r -v web/ _tmp/
}

local-test() {
  ### Used the sync'd testdata
  local dir=${1:-_tmp/github-jobs}

  local index=$dir/index.html

  local run_id=3722
  local run_index=$dir/$run_id/index.html

  list-json $dir | soil-web github-index $index $run_index $run_id

  echo "Wrote $index and $run_index"
}

"$@"
