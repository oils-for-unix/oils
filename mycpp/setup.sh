#!/bin/bash
#
# Toil build steps.
#
# TODO: Rename to toil-tasks.sh?
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

write-results() {
  find _ninja -type f | sort > _ninja/index.txt
  echo 'Wrote _ninja/index.txt'

  # Note: no HTML escaping.  Would be nice for Oil.
  find _ninja -type f | sort | gawk '
  match($0, "_ninja/(.*)", m) {
    url = m[1]
    printf("<a href=\"%s\">%s</a> <br/>\n", url, url)
  }
  ' > _ninja/index.html

  echo 'Wrote _ninja/index.html'
}

all-ninja() {
  # mycpp_main.py needs to find it
  export MYPY_REPO
  # Don't use clang for benchmarks.
  export CXX=c++

  cd $THIS_DIR
  ./build_graph.py

  set +o errexit

  # includes non-essential stuff like type checking alone, stripping
  ninja all
  local status=$?
  set -o errexit

  write-results

  # Now we want to zip up
  return $status
}

travis() {
  # invoked by services/toil-worker.sh
  all-ninja
}

run-for-release() {
  # invoked by devtools/release.sh

  rm --verbose -r -f _ninja
  all-ninja

  # Note: harness.sh benchmark-all creates ../_tmp/mycpp-examples/raw/times.tsv
  # It compares C++ and Python.
  #
  # We have _ninja/benchmark-table.tsv instead
}

"$@"
