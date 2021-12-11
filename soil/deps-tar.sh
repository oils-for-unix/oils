#!/usr/bin/env bash
#
# Usage:
#   ./deps-tar.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/.. && pwd)
readonly REPO_ROOT

DEPS_DIR=$REPO_ROOT/../oil_DEPS
readonly DEPS_DIR

download-re2c() {
  # local cache of remote files
  mkdir -p _cache
  wget --no-clobber --directory _cache \
    https://github.com/skvadrik/re2c/releases/download/1.0.3/re2c-1.0.3.tar.gz
}

build-re2c() {
  cd $REPO_ROOT/_cache
  tar -x -z < re2c-1.0.3.tar.gz

  mkdir -p $DEPS_DIR/re2c
  cd $DEPS_DIR/re2c
  $REPO_ROOT/_cache/re2c-1.0.3/configure
  make
}

cpp() {
  download-re2c
  build-re2c
}

ovm-tarball() {
  download-re2c
  build-re2c
}

"$@"
