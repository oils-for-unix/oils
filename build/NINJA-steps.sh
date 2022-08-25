#!/usr/bin/env bash
#
# Usage:
#   build/NINJA-steps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

shwrap-prefix() {
  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd "$(dirname $0)/../.."; pwd)
EOF
}

shwrap-deps-comment() {
  echo
  echo '# DEPENDS ON:'
  for dep in "$@"; do
    echo "#   $dep"
  done
}

shwrap-py() {
  local main=$1
  shwrap-prefix
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/'$main' "$@"'

  # Now write outputs
  shift
  shwrap-deps-comment "$@"
}

shwrap-mycpp() {
  shwrap-prefix

  #source mycpp/common.sh  # MYCPP_VENV

  cat <<'EOF'
MYCPP_VENV=$1  # usually ../oil_DEPS/mycpp-venv
MYPY_REPO=$2   # usually ../oil_DEPS/mypy
MYPYPATH=$3    # e.g. $REPO_ROOT/mycpp
shift 3

. $MYCPP_VENV/bin/activate
PYTHONPATH="$REPO_ROOT:$MYPY_REPO" MYPYPATH="$MYPYPATH" \
  exec ../oil_DEPS/python3 mycpp/mycpp_main.py "$@"
EOF

  shift
  shwrap-deps-comment "$@"
}

write-shwrap() {
  ### Create a shell wrapper for a Python tool

  # Key point: if the Python code changes, then the C++ code should be
  # regenerated and re-compiled

  local kind=$1
  local stub_out=$2
  shift 2

  case $kind in
    (py)
      shwrap-py "$@" > $stub_out
      ;;
    (mycpp)
      shwrap-mycpp "$@" > $stub_out
      ;;
    (*)
      die "Invalid kind '$kind'"
      ;;
  esac

  chmod +x $stub_out
}

# sourced by devtools/bin.sh
if test $(basename $0) = 'NINJA-steps.sh'; then
  "$@"
fi
