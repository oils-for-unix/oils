#!/usr/bin/env bash

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

source build/common.sh

generate_one() {
  pushd $REPO_ROOT
  local mycpp=_bin/shwrap/mycpp_main
  ninja $mycpp

  local ex=$1
  shift
  $mycpp '.:pyext' _tmp/mycpp-cfg-testdata mycpp/examples/"${ex}.py"

  mkdir -p testdata/control-flow-graph/$ex
  for fact in "$@";
  do
    local fact_file="${fact}.facts"
    cp _tmp/mycpp-facts/$fact_file testdata/control-flow-graph/$ex/$fact_file
  done
  popd
}

generate_all() {
  generate_one control_flow cf_edge
  generate_one scoped_resource cf_edge
  generate_one test_switch cf_edge
  generate_one classes assign define
}

task-five "$@"
