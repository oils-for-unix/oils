#!/usr/bin/env bash
#
# Do a full CPython build out of tree, so we can walk dependencies dynamically.
#
# The 'app-deps' and 'runpy-deps' build steps require this.
#
# Usage:
#   build/prepare.sh <function name>
#
# Example:
#
#   build/prepare.sh configure
#   build/prepare.sh build-python

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/..; pwd)
readonly REPO_ROOT

source build/common.sh

# For uftrace.
cpython-instrumented() {
  configure _devbuild/cpython-instrumented
  build-python _devbuild/cpython-instrumented '-O0 -pg'
}

"$@"
