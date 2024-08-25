#!/usr/bin/env bash
#
# For things we don't want to compile.
#
# Usage:
#   deps/from-binary.sh <function name>
#
# Example:
#   deps/from-binary.sh download-clang
#   deps/from-binary.sh extract-clang

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh

readonly DEPS_DIR=$REPO_ROOT/../oil_DEPS

# TODO: Make Clang into a wedge?

if false; then
  # This version if 7.6 GB, ugh
  LLVM_VERSION=18.1.8
  CLANG_URL='https://github.com/llvm/llvm-project/releases/download/llvmorg-18.1.8/clang+llvm-18.1.8-x86_64-linux-gnu-ubuntu-18.04.tar.xz'
else
  # This version was 4.7 GB
  LLVM_VERSION=14.0.0
  CLANG_URL='https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz'
fi

download-clang() {

  # download into $DEPS_DIR and not _cache because Dockerfile.clang stores the
  # compressed version

  wget --no-clobber --directory _cache $CLANG_URL
}

extract-clang() {
  ### For developers

  # TODO: retire ../oil_DEPS dir in favor of wedge
  mkdir -p $DEPS_DIR
  pushd $DEPS_DIR
  time tar -x --xz < ../oil/_cache/clang+llvm-$LLVM_VERSION*.tar.xz
  popd
}

extract-clang-in-container() {
  ### For Dockerfile.clang

  pushd $DEPS_DIR
  time tar -x --xz < clang+llvm-$LLVM_VERSION*.tar.xz
  popd
}

test-clang() {
  $CLANGXX --version
}

"$@"
