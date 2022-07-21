#!/usr/bin/env bash
#
# Dependencies for mycpp.  Invoked by services/worker.sh, and can also be
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
#   May 2022, that's the latest release I've tested against. It also installs
#   typeshed.
#
#   ./deps.sh pip-install
#
#   Installs Python packages that MyPy depends on.
#
# Troubleshooting:
#
#   If you don't have Python 3.6, then build one from a source tarball and then
#   install it.  (NOTE: mypyc tests require the libsqlite3-dev dependency.
#   It's probably not necessary for running mycpp.)

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source $REPO_ROOT/mycpp/common.sh  # MYPY_REPO

git-clone() {
  ### Invoked by services/toil-worker
  local out=$MYPY_REPO
  mkdir -p $out
  git clone --recursive --depth=50 --branch=release-0.730 \
    https://github.com/python/mypy $out
}

create-venv() {
  local dir=$MYCPP_VENV
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
  create-venv

  set +o nounset
  set +o pipefail
  set +o errexit
  source $MYCPP_VENV/bin/activate

  mypy-deps      # install deps in virtual env
}

layer-mycpp() {
  git-clone
  pip-install
}

"$@"
