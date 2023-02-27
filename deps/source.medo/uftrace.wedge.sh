#!/usr/bin/env bash
#
# Wedge definition for uftrace.
#
# Loaded by deps/wedge.sh.

set -o nounset
set -o pipefail
set -o errexit

WEDGE_NAME='uftrace'
WEDGE_VERSION='0.13'

# 17 seconds
wedge-build() {
  local src_dir=$1
  local build_dir=$2
  local install_dir=$3

  pushd $build_dir

  $src_dir/configure --help || true
  echo

  time $src_dir/configure --prefix=$install_dir
  echo

  time make

  popd
}

wedge-install() {
  local build_dir=$1

  pushd $build_dir

  # install-strip is a GNU thing!  It discards symbols.

  # TODO: copy them from the original binary in $BUILD_DIR
  # objcopy --add-debug-link, etc.

  # Does not have 'install-strip' target

  time make install

  popd
}

wedge-smoke-test() {
  local install_dir=$1

  # Hm it says it has Python 3 support?
  $install_dir/bin/uftrace --version
}
