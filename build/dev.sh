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

# TODO: should lex.c be part of the dev build?  It means you need re2c
# installed?  I don't think it makes sense to have 3 builds, so yes I think we
# can put it here for simplicity.
# However one problem is that if the Python lexer definition is changed, then
# you need to run re2c again!  I guess you should just provide a script to
# download it.

pylibc() {
  mkdir -p _devbuild/pylibc
  local arch=$(uname -m)
  build/setup.py build --build-lib _devbuild/pylibc/$arch

  shopt -s failglob
  local libc_so=$(echo _devbuild/pylibc/$arch/libc.so)
  ln -s -f -v $libc_so libc.so

  local lex_so=$(echo _devbuild/pylibc/$arch/lex.so)
  ln -s -f -v $lex_so lex.so

  file libc.so lex.so
}

# Also done by unit.sh.
test-pylibc() {
  export PYTHONPATH=.
  pylibc
  native/libc_test.py
  native/lex_test.py
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
