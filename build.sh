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

install-deps() {
  # python-dev: for pylibc
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  sudo apt-get install python-dev gawk time libreadline-dev

  ./spec.sh install-shells
}

pylibc() {
  mkdir -p _pybuild
  local arch=$(uname -m)
  ./setup.py build --build-lib _pybuild/$arch

  # Wildcard to match any Python 3 version.
  shopt -s failglob
  local so=$(echo _pybuild/$arch/libc.so)

  ln -s -f --verbose $so libc.so
  file libc.so
}

# Also done by unit.sh.
test-pylibc() {
  export PYTHONPATH=.
  pylibc
  native/libc_test.py
}

clean() {
  rm -f --verbose libc.so
  rm -r -f --verbose _pybuild
}

"$@"
