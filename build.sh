#!/bin/bash
#
# Build Python extension modules.  We use symlinks instead of installing them
# globally (or using virtualenv).
#
# Usage:
#   ./pybuild.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

pylibc() {
  ./setup.py build

  # Wildcard to match any Python 3 version.
  shopt -s failglob
  local so=$(echo build/lib.linux-x86_64-3.*/libc.cpython-3*.so)

  ln -s -f --verbose ../$so core/libc.so
}

# Also done by unit.sh.
test-pylibc() {
  export PYTHONPATH=.
  libc
  core/libc_test.py
}

clean() {
  rm -f --verbose core/libc.so
  rm -r -f --verbose build
}

"$@"
