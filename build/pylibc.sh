#!/usr/bin/env bash
#
# Build Python extension modules.  We use symlinks instead of installing them
# globally (or using virtualenv).
#
# Usage:
#   ./pybuild.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

build() {
  mkdir -p _build/pylibc
  local arch=$(uname -m)
  build/setup.py build --build-lib _build/pylibc/$arch

  # Wildcard to match any Python 3 version.
  shopt -s failglob
  local so=$(echo _build/pylibc/$arch/libc.so)

  ln -s -f -v $so libc.so
  file libc.so
}

# Also done by unit.sh.
test() {
  export PYTHONPATH=.
  build
  native/libc_test.py
}

clean() {
  rm -f --verbose libc.so
  rm -r -f --verbose _build/pylibc
}

"$@"
