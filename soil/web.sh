#!/usr/bin/env bash
#
# Wrapper for soil/web.py.
#
# Usage:
#   soil/web.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly REPO_ROOT=$(cd $(dirname $0)/..; pwd)

source $REPO_ROOT/soil/common.sh

soil-web() {
  PYTHONPATH=$REPO_ROOT $REPO_ROOT/soil/web.py "$@"
}

rewrite-jobs-index() {
  ### Atomic update of travis-ci.oilshell.org/jobs/
  local prefix=$1

  local dir=~/travis-ci.oilshell.org/${prefix}jobs

  log "soil-web: Rewriting ${prefix}jobs/index.html"

  local tmp=/tmp/$$.index.html

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
      ls $dir/*.json | soil-web cleanup | xargs --no-run-if-empty -- rm -v 
      ;;
    true)
      ls $dir/*.json | soil-web cleanup
      ;;
    *)
      log 'Expected true or false for dry_run'
  esac
}


#
# Dev Tools
#

sync-testdata() {
  rsync --archive --verbose \
    $USER@$HOST:$HOST/jobs/ _tmp/jobs/
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
