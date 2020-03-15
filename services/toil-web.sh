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

rewrite-jobs-index() {
  ### Atomic update of travis-ci.oilshell.org/jobs/

  local dest=${1:-~/travis-ci.oilshell.org/jobs/index.html}

  local tmp=/tmp/$$.index.html

  # TODO: List the jobs here? and the thing to rewrite?

  toil-web "$@" > $tmp

  mv $tmp $dest
}

test() {
  toil-web "$@"
}

"$@"
