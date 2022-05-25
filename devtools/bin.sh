#!/usr/bin/env bash
#
# Manage the bin/ directory.
#
# Usage:
#   devtools/bin.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Used by devtools/bin.sh and opy/build.sh
readonly OIL_SYMLINKS=(oil oilc osh oshc tea sh true false readlink)
readonly OPY_SYMLINKS=(opy opyc)

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

make-osh-eval() {
  local out=bin/osh_eval
  { sh-prefix
    echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/bin/osh_eval.py "$@"'
  } > $out
  chmod +x $out
  echo "Wrote $out"
}

sh-prefix() {
  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd $(dirname $(dirname $0)) && pwd)
EOF
}

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
  sh-snippet oil.py $action
}

opy-dev-snippet() {
  local action=$1
  sh-snippet opy_.py $action
}

make-bin-stubs() {
  ### bin/ is for running with the Python interpreter.
  mkdir -p bin

  for link in "${OIL_SYMLINKS[@]}"; do
    # bin/ shell wrapper
    oil-dev-snippet $link > bin/$link
    chmod +x bin/$link
    echo "Wrote bin/$link"
  done

  for link in "${OPY_SYMLINKS[@]}"; do
    opy-dev-snippet $link > bin/$link
    chmod +x bin/$link
    echo "Wrote bin/$link"
  done

  make-osh-dbg

  make-osh-eval
}

make-bin-links() {
  ### _bin/ is for running with OVM app bundles.

  mkdir -p _bin

  for link in "${OIL_SYMLINKS[@]}"; do
    # _bin/ symlink
    ln -s -f --verbose oil.ovm _bin/$link
  done

  for link in "${OPY_SYMLINKS[@]}"; do
    # _bin/ symlink
    ln -s -f --verbose opy.ovm _bin/$link
  done
}

"$@"
