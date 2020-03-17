#!/bin/bash
#
# Wrapper for services/toil_web.py.
#
# Usage:
#   services/toil-web.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly REPO_ROOT=$(cd $(dirname $0)/..; pwd)

source $REPO_ROOT/services/common.sh

# On the server
#
# toil-web/
#   bin/
#     toil-web.sh
#   doctools/
#   services/
#   
#
toil-web() {
  PYTHONPATH=$REPO_ROOT $REPO_ROOT/services/toil_web.py "$@"
}

index() {
  toil-web index "$@"
}

rewrite-jobs-index() {
  ### Atomic update of travis-ci.oilshell.org/jobs/
  local dir=${1:-~/travis-ci.oilshell.org/jobs/}

  log "toil-web: Rewriting jobs/index.html"

  local tmp=/tmp/$$.index.html

  ls $dir/*.json | index > $tmp

  mv $tmp $dir/index.html
}

readonly USER='travis_admin'
readonly HOST='travis-ci.oilshell.org'

sync-testdata() {
  rsync --archive --verbose \
    $USER@$HOST:$HOST/jobs/ _tmp/jobs/
}

smoke-test() {
  local dir=${1:-_tmp/jobs}
  local out='_tmp/jobs.html'

  ls $dir/*.json | index > $out
  echo "Wrote $out"
}


"$@"
