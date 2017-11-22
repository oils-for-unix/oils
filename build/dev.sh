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

# TODO: should fastlex.c be part of the dev build?  It means you need re2c
# installed?  I don't think it makes sense to have 3 builds, so yes I think we
# can put it here for simplicity.
# However one problem is that if the Python lexer definition is changed, then
# you need to run re2c again!  I guess you should just provide a script to
# download it.

py-ext() {
  local name=$1
  local setup_script=$2

  mkdir -p _devbuild/py-ext
  local arch=$(uname -m)
  $setup_script build --build-lib _devbuild/py-ext/$arch

  shopt -s failglob
  local so=$(echo _devbuild/py-ext/$arch/$name.so)
  ln -s -f -v $so $name.so

  file $name.so
}

pylibc() {
  py-ext libc build/setup.py
}

fastlex() {
  py-ext fastlex build/setup_fastlex.py
  PYTHONPATH=. native/fastlex_test.py
}

# Also done by unit.sh.
test-pylibc() {
  export PYTHONPATH=.
  pylibc
  native/libc_test.py
}

clean() {
  rm -f --verbose libc.so fastlex.so
  rm -r -f --verbose _devbuild/py-ext
}

all() {
  gen-help
  pylibc
  test-pylibc
}

"$@"
