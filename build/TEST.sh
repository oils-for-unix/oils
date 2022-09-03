#!/usr/bin/env bash
#
# Test some generated code.
#
# Usage:
#   build/TEST.sh all

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh
source cpp/NINJA-steps.sh  # compile_and_link
source test/common.sh

test-optview() {
  local compiler=${1:-cxx}
  local variant=${2:-asan}

  ninja _gen/core/optview.h _gen/frontend/option.asdl.h

  local gen_dir=_gen/core
  local bin_dir=_bin/cxx-asan/core
  mkdir -p $gen_dir $bin_dir

  cat >$gen_dir/optview_test.cc <<'EOF'
#include "_gen/core/optview.h"

int main() {
  printf("OK optview_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/optview_test

  compile_and_link $compiler $variant '' $bin \
    $gen_dir/optview_test.cc

  run-test-bin $bin
}

test-flag-gen() {
  local compiler=${1:-cxx}
  local variant=${2:-asan}

  ninja _gen/frontend/arg_types.{h,cc}

  local gen_dir=_gen/frontend
  local bin_dir=_bin/$compiler-$variant/frontend
  mkdir -p $gen_dir $bin_dir

  cat >$gen_dir/arg_types_test.cc <<'EOF'
#include "_gen/frontend/arg_types.h"

int main() {
  printf("kFlagSpecs %p\n", arg_types::kFlagSpecs);
  printf("OK arg_types_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/arg_types_test

  compile_and_link $compiler $variant '' $bin \
    _gen/frontend/arg_types.cc \
    $gen_dir/arg_types_test.cc

  run-test-bin $bin
}

all() {
  test-optview
  echo

  test-flag-gen
  echo
}

"$@"
