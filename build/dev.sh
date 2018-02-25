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

# Produces _devbuild/gen/osh_help.py
gen-help() {
  build/doc.sh osh-quick-ref
}

gen-types-asdl() {
  local out=_devbuild/gen/types_asdl.py
  local import='from osh.meta import TYPES_TYPE_LOOKUP as TYPE_LOOKUP'
  PYTHONPATH=. asdl/gen_python.py osh/types.asdl "$import" > $out
  echo "Wrote $out"
}

gen-osh-asdl() {
  local out=_devbuild/gen/osh_asdl.py
  local import='from osh.meta import OSH_TYPE_LOOKUP as TYPE_LOOKUP'
  PYTHONPATH=. asdl/gen_python.py osh/osh.asdl "$import" > $out
  echo "Wrote $out"
}

gen-runtime-asdl() {
  local out=_devbuild/gen/runtime_asdl.py
  local import='from osh.meta import RUNTIME_TYPE_LOOKUP as TYPE_LOOKUP'
  PYTHONPATH=. asdl/gen_python.py core/runtime.asdl "$import" > $out
  echo "Wrote $out"
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
  PYTHONPATH=. native/libc_test.py
}

fastlex() {
  build/codegen.sh ast-id-lex

  # Why do we need this?  It gets stail otherwise.
  rm -f _devbuild/py-ext/x86_64/fastlex.so

  py-ext fastlex build/setup_fastlex.py
  PYTHONPATH=. native/fastlex_test.py
}

clean() {
  rm -f --verbose libc.so fastlex.so
  rm -r -f --verbose _devbuild/py-ext
}

# No fastlex, because we don't want to require re2c installation.
minimal() {
  mkdir -p _devbuild/gen
  # so osh_help.py and osh_asdl.py are importable
  touch _devbuild/__init__.py  _devbuild/gen/__init__.py

  gen-help
  gen-types-asdl
  gen-osh-asdl
  gen-runtime-asdl
  pylibc
}

# Prerequisites: build/codegen.sh {download,install}-re2c
all() {
  minimal
  build/codegen.sh
  fastlex
}

"$@"
