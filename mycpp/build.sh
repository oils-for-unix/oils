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

all-ninja() {
  mycpp/build_graph.py

  set +o errexit

  # includes non-essential stuff like type checking alone, stripping
  ninja -f mycpp.ninja all
  local status=$?
  set -o errexit

  find-dir-html _ninja

  # Now we want to zip up
  return $status
}

examples() {
  # invoked by soil/worker.sh
  all-ninja
}

run-for-release() {
  # invoked by devtools/release.sh

  all-ninja
}

#
# Utilities
#

config() {
  ./build_graph.py
  cat build.ninja
}

clean() {
  rm --verbose -r -f _ninja
}

"$@"
