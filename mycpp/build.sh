#!/usr/bin/env bash
#
# Entry points for soil/worker.sh, and wrappers around Ninja.
#
# Usage:
#   ./build.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source $REPO_ROOT/mycpp/common.sh  # MYPY_REPO
source $REPO_ROOT/soil/common.sh  # find-dir-html

soil-run() {
  ./NINJA_config.py

  set +o errexit

  # includes non-essential stuff like type checking alone, stripping
  ninja mycpp-all
  local status=$?
  set -o errexit

  find-dir-html _test

  # Now we want to zip up
  return $status
}

run-for-release() {
  # invoked by devtools/release.sh

  ./NINJA_config.py
  ninja mycpp-all
}

#
# Utilities
#

clean() {
  rm --verbose -r -f _test
}

"$@"
