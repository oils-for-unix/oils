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
  sudo apt-get install python3-dev gawk time

  ./spec.sh install-shells
}

pylibc() {
  ./setup.py build

  # Wildcard to match any Python 3 version.
  shopt -s failglob
  local arch=$(uname -m)
  local so=$(echo build/lib.linux-$arch-2.*/libc.so)

  ln -s -f --verbose ../$so core/libc.so
  file core/libc.so
}

# Also done by unit.sh.
test-pylibc() {
  export PYTHONPATH=.
  pylibc
  core/libc_test.py
}

clean() {
  rm -f --verbose core/libc.so
  rm -r -f --verbose build
}

"$@"
