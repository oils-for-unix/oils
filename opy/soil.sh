#!/usr/bin/env bash
#
# CI tasks.
#
# Usage:
#   opy/soil.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. ; pwd)

test-gold() {
  pushd opy
  ./TEST.sh gold
  popd
}

build-oil-repo() {
  pushd opy
  ./build.sh oil-repo 
  popd
}

regtest-compile() {
  pushd opy
  # NOTE: This is sensitive to Python 2.7.12 vs .13 vs .14.  Ideally we would
  # remove that.
  # NOTE: There is no indication if this fails!
  ./regtest.sh compile-all
  popd
}

count-lines() {
  pushd opy
  ./count.sh all
  popd
}

"$@"
