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

  bin/osh -c 'echo hi from osh $OILS_VERSION'
  bin/ysh -c 'echo hi from ysh $OILS_VERSION'
}

"$@"
