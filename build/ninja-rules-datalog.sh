#!/usr/bin/env bash
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

readonly DEPS_DIR=$REPO_ROOT/../oil_DEPS

source build/common.sh
source build/dev-shell.sh
source devtools/run-task.sh

compile_souffle() {
  in=$1
  out=$2
  souffle -g - -I mycpp/datalog $in > $out
}

run-task "$@"
