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

  # TODO: Limit to 50 jobs?
  ls $dir/*.json | index > $tmp

  mv $tmp $dir/index.html
}

#
# Release
#

readonly USER='travis_admin'
readonly HOST='travis-ci.oilshell.org'

toil-web-manifest() {
  PYTHONPATH=. /usr/bin/env python2 \
    build/app_deps.py py-manifest services.toil_web \
  | grep oilshell/oil  # only stuff in the repo

  # Add a shell script
  echo $PWD/services/toil-web.sh services/toil-web.sh
  echo $PWD/services/common.sh services/common.sh
}

# Also used in test/wild.sh
multi() { ~/hg/tree-tools/bin/multi "$@"; }

deploy() {
  toil-web-manifest | multi cp _tmp/toil-web
  tree _tmp/toil-web
  rsync --archive --verbose _tmp/toil-web/ $USER@$HOST:toil-web/
}

remote-test() {
  ssh $USER@$HOST \
    toil-web/services/toil-web.sh smoke-test '~/travis-ci.oilshell.org/jobs'
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
  ls $dir/*.json | index 
}

"$@"
