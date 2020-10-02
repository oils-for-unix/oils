#!/usr/bin/env bash
#
# Usage:
#   ./setup.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(dirname $(readlink -f $0))
readonly REPO_ROOT=$THIS_DIR/..
readonly MYPY_REPO=$REPO_ROOT/_clone/mypy

clone() {
  local out=$MYPY_REPO
  mkdir -p $out
  git clone --recursive --depth=50 --branch=release-0.730 \
    https://github.com/python/mypy $out
}

# From run.sh
deps() {
  export MYPY_REPO  # mypy-deps function uses this

  pushd $THIS_DIR

  ./run.sh create-venv

  set +o nounset
  set +o pipefail
  set +o errexit
  source _tmp/mycpp-venv/bin/activate

  ./run.sh mypy-deps      # install deps in virtual env

  popd
}

build() {
  export MYPY_REPO  # build/mycpp.sh uses this

  build/dev.sh oil-cpp
}

#
# Hooks needs because mycpp/run.sh needs to be in the mycpp/ dir.
#

build-examples() {
  ### Build all mycpp/examples

  export MYPY_REPO

  cd $THIS_DIR
  ./run.sh build-all
}

test-examples() {
  ### Test all mycpp/examples

  cd $THIS_DIR
  ./run.sh test-all
}

benchmark-examples() {
  ### Benchmark all mycpp/examples

  cd $THIS_DIR
  ./run.sh benchmark-all
}

"$@"
