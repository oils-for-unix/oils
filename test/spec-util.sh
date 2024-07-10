#!/usr/bin/env bash
#
# Usage:
#   test/spec-util.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/spec-common.sh
source devtools/task-five.sh

run-file-with-osh-bash() {
  local spec_name=$1
  shift

  # Note: there's no longer a way to run with 2 shells?  We could do
  # test/sh_spec.py --shells-from-argv foo.test.sh osh bash
  echo TODO
}

_run-file-with-one() {
  local shell=$1
  local spec_name=$2
  shift 2

  # 2023-06: note --timeout 10 seems to make every test hang
  # I guess $SH -i doesn't run well like that
  sh-spec spec/$spec_name.test.sh \
    --oils-bin-dir $PWD/bin \
    -d \
    -t \
    $shell "$@"
}

run-file-with-osh() { _run-file-with-one $REPO_ROOT/bin/osh "$@"; }
run-file-with-bash() { _run-file-with-one bash "$@"; }

task-five "$@"
