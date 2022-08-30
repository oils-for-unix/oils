#!/usr/bin/env bash
#
# For textual code generation.
#
# Usage:
#   build/TEST.sh all
#
# We want a single step build from the git tree, but we also want the generated
# code to be distributed in the release tarball.
#
# For ASDL code generation, re2c, etc.

# NOTE: This is similar to the generation of osh_help.py.

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh
source cpp/NINJA-steps.sh  # compile_and_link

test-optview() {
  ninja _gen/core/optview.h _build/cpp/option_asdl.h

  local tmp_dir=_test/gen-cpp/core
  local bin_dir=_bin/cxx-asan/core
  mkdir -p $tmp_dir $bin_dir

  cat >$tmp_dir/optview_test.cc <<'EOF'
#include "_gen/core/optview.h"

int main() {
  printf("OK optview_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/optview_test

  compile_and_link cxx asan '' $bin \
    $tmp_dir/optview_test.cc

  log "RUN $bin"
  $bin
}

test-flag-gen() {
  ninja _gen/frontend/arg_types.{h,cc}

  local tmp_dir=_test/gen-cpp/core
  local bin_dir=_bin/cxx-asan/core
  mkdir -p $tmp_dir $bin_dir

  cat >$tmp_dir/arg_types_test.cc <<'EOF'
#include "_gen/frontend/arg_types.h"

int main() {
  printf("kFlagSpecs %p\n", arg_types::kFlagSpecs);
  printf("OK arg_types_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/arg_types_test

  compile_and_link cxx asan '' $bin \
    _gen/frontend/arg_types.cc \
    $tmp_dir/arg_types_test.cc

  log "RUN $bin"
  $bin
}

all() {
  test-optview
  echo

  test-flag-gen
  echo
}

"$@"
