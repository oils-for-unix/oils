#!/usr/bin/env bash
#
# Usage:
#   deps/from-py.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # may use different python3

dev-minimal() {
  # System Python 2 packages for linting linting Python 2 code.
  #pip install --user flake8 typing

  # Python 3 packages

  # pexpect is for spec/stateful
  install-pexpect

  # Last official release that supported Python 2 was 0.971 in July 2022
  # https://mypy-lang.blogspot.com/2022/07/mypy-0971-released.html
  #python3 -m pip install --user 'mypy<=0.971'
  #python3 -m pip install 'mypy<=0.971'

  # 2023-07: needed to add python3-dev in the base image
  pip3 install 'mypy<=0.971'

  # System Python 3?
  #pip3 install --user 'mypy<=0.971'
}

pea() {
  echo 'Not used by Dockerfile.pea'
  # pip3 install --user mypy
}

# TODO:
# - We don't really need MyPy for C++ tasks, since mycpp checks types
# - pexpect might go in a new image for spec/stateful

install-pexpect() {
  ### done in spec-cpp, but also need it in dev-minimal
  python3 -m pip install pexpect
}

do-we-need() {
  # Do the C++ tasks need MyPy?
  python3 -m pip install 'mypy<=0.971'
}

"$@"
