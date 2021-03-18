#!/usr/bin/env bash
#
# Dependencies for mycpp.  Invoked by services/toil-worker.sh, and can also be
# invoked manually.
#
# Usage:
#   ./deps.sh <function name>
#
# Setup:
#
#   ./deps.sh git-clone
#
#   This clones the MyPy repo and switches to the release-0.730 branch.  As of
#   March 2021, that's the latest release I've tested against. It also installs
#   typeshed.
#
#   If you don't have Python 3.6, then build one from a source tarball and then
#   install it.  (NOTE: mypyc tests require the libsqlite3-dev dependency.
#   It's probably not necessary for running mycpp.)
# 
#   ./deps.sh pip-install
#
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

readonly THIS_DIR=$(dirname $(readlink -f $0))
readonly REPO_ROOT=$THIS_DIR/..

source $THIS_DIR/common.sh  # MYPY_REPO

git-clone() {
  ### Invoked by services/toil-worker
  local out=$MYPY_REPO
  mkdir -p $out
  git clone --recursive --depth=50 --branch=release-0.730 \
    https://github.com/python/mypy $out
}

create-venv() {
  local dir=_tmp/mycpp-venv
  python3 -m venv $dir

  ls -l $dir
  
  echo "Now run . $dir/bin/activate"
}

# Do this inside the virtualenv
# Re-run this when UPGRADING MyPy.  10/2019: Upgraded from 0.670 to 0.730.
mypy-deps() {
  python3 -m pip install -r $MYPY_REPO/test-requirements.txt
}

pip-install() {
  ### Invoked by services/toil-worker

  export MYPY_REPO  # mypy-deps function uses this

  pushd $THIS_DIR

  create-venv

  set +o nounset
  set +o pipefail
  set +o errexit
  source _tmp/mycpp-venv/bin/activate

  mypy-deps      # install deps in virtual env

  popd
}

"$@"
