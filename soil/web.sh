#!/usr/bin/env bash
#
# Wrapper for soil/web.py.
#
# Usage:
#   soil/web.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

source $REPO_ROOT/soil/common.sh

soil-web() {
  PYTHONPATH=$REPO_ROOT $REPO_ROOT/soil/web.py "$@"
}

rewrite-jobs-index() {
  ### Atomic update of travis-ci.oilshell.org/jobs/
  local prefix=$1

  local dir=~/travis-ci.oilshell.org/${prefix}jobs

  log "soil-web: Rewriting ${prefix}jobs/index.html"

  # Fix for bug #1169: don't create the temp file on a different file system,
  # which /tmp may be.
  #
  # When the source and target are on different systems, I believe 'mv' falls
  # back to 'cp', which has this race condition:
  #
  # https://unix.stackexchange.com/questions/116280/cannot-create-regular-file-filename-file-exists

  local tmp=$$.index.html

  # Limit to last 100 jobs.  Glob is in alphabetical order and jobs look like
  # 2020-03-20__...

  # suppress SIGPIPE failure
  { ls $dir/*.json || true; } | tail -n -100 | soil-web ${prefix}index > $tmp
  echo status=${PIPESTATUS[@]}

  mv -v $tmp $dir/index.html
}

cleanup-jobs-index() {
  local prefix=$1
  local dry_run=${2:-true}

  local dir=~/travis-ci.oilshell.org/${prefix}jobs

  # Pass it all JSON, and then it figures out what files to delete (TSV, etc.)
  case $dry_run in
    false)
      # Bug fix: there is a race here when 2 jobs complete at the same time.
      # So use rm -f to ignore failure if the file was already deleted.
      ls $dir/*.json | soil-web cleanup | xargs --no-run-if-empty -- rm -f -v
      ;;
    true)
      ls $dir/*.json | soil-web cleanup
      ;;
    *)
      log 'Expected true or false for dry_run'
  esac
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


#
# Dev Tools
#

sync-testdata() {
  rsync --archive --verbose \
    $SOIL_USER@$SOIL_HOST:$SOIL_HOST/jobs/ _tmp/jobs/
}

local-test() {
  ### Used the sync'd testdata
  local dir=${1:-_tmp/jobs}
  local out='_tmp/jobs.html'

  ls $dir/*.json | index > $out
  echo "Wrote $out"
}

smoke-test() {
  ### Run on remote machine
  local dir=${1:-_tmp/jobs}
  ls $dir/*.json | soil-web srht-index 
}

"$@"
