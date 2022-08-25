#!/usr/bin/env bash
#
# Usage:
#   build/NINJA-steps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

sh-prefix() {
  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
EOF
}

sh-pystub() {
  local main=$1
  sh-prefix
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/'$main' "$@"'

  # Now write outputs
  shift
  echo
  echo '# depends on:'
  for dep in "$@"; do
    echo "# $dep"
  done
}

make-pystub() {
  ### Create a stub for a Python tool

  # Key point: if the Python code changes, then the C++ code should be
  # regenerated and re-compiled

  # e.g. for _bin/pytools/asdl_tool ?
  local stub_out=$1
  shift

  sh-pystub "$@" > $stub_out
  chmod +x $stub_out
}

# sourced by devtools/bin.sh
if test $(basename $0) = 'NINJA-steps.sh'; then
  "$@"
fi
