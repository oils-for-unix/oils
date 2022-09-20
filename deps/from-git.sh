#!/usr/bin/env bash
#
# Dependencies for mycpp.  Invoked by soil/worker.sh, and can also be invoked
# manually.
#
# Usage:
#   deps/from-git.sh <function name>
#
# Prerequisites:
#
#   Run deps/from-tar.sh layer-py3 first.
#
# Example:
#
#   deps/from-git.sh layer-mycpp

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source $REPO_ROOT/mycpp/common.sh  # MYPY_REPO, maybe-our-python3

mypy-git-clone() {
  ### Clone mypy at a specific branch

  local out=$MYPY_REPO
  mkdir -p $out
  git clone --recursive --depth=50 --branch=release-0.780 \
    https://github.com/python/mypy $out
}

create-venv() {
  local dir=$MYCPP_VENV

  maybe-our-python3 -m venv $dir

  ls -l $dir
  
  echo "Now run . $dir/bin/activate"
}

ensure-pip() {
  ### Special module to add pip to hermetic build

  # Weird that it's a bunch of wheels

  maybe-our-python3 -m ensurepip
}

# Do this inside the virtualenv
# Re-run this when UPGRADING MyPy.  10/2019: Upgraded from 0.670 to 0.730.
mypy-deps() {
  maybe-our-python3 -m pip install -r $MYPY_REPO/test-requirements.txt
}

mypy-pip-install() {
  ensure-pip
  create-venv

  set +o nounset
  set +o pipefail
  set +o errexit
  source $MYCPP_VENV/bin/activate

  mypy-deps      # install deps in virtual env
}

layer-mycpp() {
  mypy-git-clone
  mypy-pip-install
}

"$@"
