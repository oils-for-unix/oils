#!/usr/bin/env bash
#
# Run Souffle smoke test.

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

soil-run() {
  ninja _bin/datalog/smoke-test
  pushd $REPO_ROOT/_tmp
  $REPO_ROOT/_bin/datalog/smoke-test
  sort path.tsv | diff -u - $REPO_ROOT/deps/source.medo/souffle/path.expected.tsv
  popd
}

"$@"
