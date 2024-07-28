#!/usr/bin/env bash

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

readonly DEPS_DIR=$REPO_ROOT/../oil_DEPS

source build/common.sh
source build/dev-shell.sh

compile_one() {
  in=$1
  local base=$(basename -s .dl $in)
  local out="prebuilt/datalog/${base}.cc"

  souffle -g - -I $REPO_ROOT/mycpp/datalog $in > $out
}

compile_all() {
  compile_one mycpp/datalog/call-graph.dl
  compile_one deps/source.medo/souffle/smoke-test.dl
}

task-five "$@"
