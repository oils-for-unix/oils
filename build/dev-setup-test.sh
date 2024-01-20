#!/usr/bin/env bash
#
# Usage:
#   build/dev-setup-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

smoke-test() {
  ### For the fast possible development experience

  # To put python2 WEDGE in $PATH
  source build/dev-shell.sh

  bin/osh -c 'echo HI osh python $OILS_VERSION'
  bin/ysh -c 'echo HI ysh python $OILS_VERSION'

  ninja

  _bin/cxx-asan/osh -c 'echo HI osh C++ $OILS_VERSION'
  _bin/cxx-asan/ysh -c 'echo HI ysh C++ $OILS_VERSION'
}

"$@"
