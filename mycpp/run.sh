#!/usr/bin/env bash
#
# Misc automation.
#
# Usage:
#   ./run.sh <function name>
#
# Setup:
#
#   Clone mypy into $MYPY_REPO, and then:
#
#   Switch to the release-0.730 branch.  As of March 2021, that's the latest
#   release I've tested against.
#
#   Then install typeshed:
#
#   $ git submodule init
#   $ git submodule update
#
# If you don't have Python 3.6, then build one from a source tarball and then
# install it.  (NOTE: mypyc tests require the libsqlite3-dev dependency.  
# It's probably not necessary for running mycpp.)
# 
# Afterwards, these commands should work:
#
#   ./run.sh create-venv
#   source _tmp/mycpp-venv/bin/activate
#   ./run.sh mypy-deps      # install deps in virtual env

# To build and run tests and benchmarks:
#
#   ./build_graph.py
#   ninja logs-equal       # compare logs
#   ninja benchmark-table  # make at able of time/memory usage
#
# To build and run one example:
#
#   ninja _ninja/tasks/test/fib_iter.py.task.txt
#
# To list targets:
#
#   ninja -t targets

set -o nounset
set -o pipefail
set -o errexit

source common.sh  # THIS_DIR, REPO_ROOT, MYPY_REPO

create-venv() {
  local dir=_tmp/mycpp-venv
  #python3.6 -m venv $dir
  python3 -m venv $dir

  ls -l $dir
  
  echo "Now run . $dir/bin/activate"
}

# Do this inside the virtualenv
# Re-run this when UPGRADING MyPy.  10/2019: Upgraded from 0.670 to 0.730.
mypy-deps() {
  python3 -m pip install -r $MYPY_REPO/test-requirements.txt
}

gen-ctags() {
  ctags -R $MYPY_REPO
}

"$@"
