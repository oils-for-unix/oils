#!/usr/bin/env bash
#
# For things we don't want to compile.
#
# Usage:
#   soil/deps-binary.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. ; pwd)

source build/common.sh

# Used in build/common.sh
download-clang() {
  wget --no-clobber --directory _cache \
    https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz
}

extract-clang() {
  pushd ../oil_DEPS
  time tar -x --xz < ../oil/_cache/clang+llvm-14.0.0*.tar.xz
  popd
}

test-clang() {
  $CLANGXX --version
}

"$@"
