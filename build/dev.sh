#!/usr/bin/env bash
#
# Set up a development build of Oil on CPython.
# This is in constrast to the release build, which bundles Oil with "OVM" (a
# slight fork of CPython).

# Build Python extension modules.  We use symlinks instead of installing them
# globally (or using virtualenv).
#
# Usage:
#   ./pybuild.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

ubuntu-deps() {
  # python-dev: for pylibc
  # gawk: used by spec-runner.sh for the special match() function.
  # time: used to collect the exit code and timing of a test
  # libreadline-dev: needed for the build/prepare.sh Python build.
  sudo apt-get install python-dev gawk time libreadline-dev

  test/spec.sh install-shells
}

# These produce _devbuild/{osh,oil}_help.py
gen-help() {
  build/doc.sh osh-quick-ref
  build/doc.sh oil-quick-ref
}

pylibc() {
  mkdir -p _devbuild/pylibc
  local arch=$(uname -m)
  build/setup.py build --build-lib _devbuild/pylibc/$arch

  # Wildcard to match any Python 3 version.
  shopt -s failglob
  local so=$(echo _devbuild/pylibc/$arch/libc.so)

  ln -s -f -v $so libc.so
  file libc.so
}

# Also done by unit.sh.
test-pylibc() {
  export PYTHONPATH=.
  pylibc
  native/libc_test.py
}

clean-pylibc() {
  rm -f --verbose libc.so
  rm -r -f --verbose _devbuild/pylibc
}

all() {
  gen-help
  pylibc
  test-pylibc
}

"$@"
