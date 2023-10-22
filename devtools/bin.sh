#!/usr/bin/env bash
#
# Manage the bin/ directory.
#
# Usage:
#   devtools/bin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# New name is ysh!
# TODO:
# - remove the 'oil' everywhere
# - translation should be 'ysh-translate'.  Later 'ysh-format'
readonly OIL_OVM_NAMES=(oil ysh osh tea sh true false readlink)

# TODO: probably delete this
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

sh-prefix() {
  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
EOF
}

make-oils-for-unix() {
  local out=bin/oils-for-unix
  { sh-prefix
    echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/bin/oils_for_unix.py "$@"'
  } > $out
  chmod +x $out
  echo "Wrote $out"
}

#
# Shell Stubs
#

sh-snippet() {
  local wrapped=$1  # e.g. oil.py
  local action=$2  # e.g. osh

  sh-prefix
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/bin/'$wrapped' '$action' "$@"'
}

# A snippet that sets PYTHONPATH for bin/oil.py and runs it with the right
# action.
oil-dev-snippet() {
  local action=$1
  sh-snippet oils_for_unix.py $action
}

opy-dev-snippet() {
  local action=$1
  sh-snippet opy_.py $action
}

make-src-stubs() {
  ### bin/ is for running with the Python interpreter.
  mkdir -p bin

  for link in "${OIL_OVM_NAMES[@]}"; do
    # bin/ shell wrapper
    oil-dev-snippet $link > bin/$link
    chmod +x bin/$link
    echo "Wrote bin/$link"
  done

  make-osh-dbg

  make-oils-for-unix
}

make-ovm-links() {
  ### _bin/ is for running with OVM app bundles.

  mkdir -p _bin

  for link in "${OIL_OVM_NAMES[@]}"; do
    # _bin/ symlink
    ln -s -f --verbose oil.ovm _bin/$link
  done
}

"$@"
