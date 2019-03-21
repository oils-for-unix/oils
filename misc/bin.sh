#!/usr/bin/env bash
#
# Manage the bin/ directory.
#
# Usage:
#   ./bin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for OIL_SYMLINKS and OPY_SYMLINKS

# For osh-dbg.
ovm-snippet() {
  local name=$1
  echo '#!/bin/sh'
  echo 'exec _bin/oil.ovm-dbg '$name' "$@"'
}

# For running spec tests quickly.
make-osh-dbg() {
  local out=_bin/osh-dbg
  ovm-snippet osh > $out
  chmod +x $out
}

# A snippet that sets PYTHONPATH for bin/oil.py and runs it with the right
# action.
oil-dev-snippet() {
  local name=$1
  echo '#!/bin/sh'
  echo 'REPO_ROOT=$(cd $(dirname $(dirname $0)) && pwd)'
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/bin/oil.py '$name' "$@"'
}

opy-dev-snippet() {
  local name=$1
  echo '#!/bin/sh'
  echo 'REPO_ROOT=$(cd $(dirname $(dirname $0)) && pwd)'
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/bin/opy_.py '$name' "$@"'
}

make-bin-links() {
  # bin/ is for running with the Python interpreter.  _bin/ is for running with
  # OVM app bundles.
  mkdir -p bin _bin

  for link in "${OIL_SYMLINKS[@]}"; do
    # bin/ shell wrapper
    oil-dev-snippet $link > bin/$link
    chmod +x bin/$link
    echo "Wrote bin/$link"

    # _bin/ symlink
    ln -s -f --verbose oil.ovm _bin/$link
  done

  for link in "${OPY_SYMLINKS[@]}"; do
    opy-dev-snippet $link > bin/$link
    chmod +x bin/$link
    echo "Wrote bin/$link"

    # _bin/ symlink
    ln -s -f --verbose opy.ovm _bin/$link
  done

  make-osh-dbg
}

"$@"
