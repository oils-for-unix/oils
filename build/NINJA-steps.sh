#!/usr/bin/env bash
#
# Usage:
#   build/NINJA-steps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

sh-stub-prefix() {
  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd "$(dirname $0)/../.."; pwd)
EOF
}

sh-deps-comment() {
  echo
  echo '# DEPENDS ON:'
  for dep in "$@"; do
    echo "#   $dep"
  done
}

sh-py-stub() {
  local main=$1
  sh-stub-prefix
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/'$main' "$@"'

  # Now write outputs
  shift
  sh-deps-comment "$@"
}

sh-mycpp-stub() {
  sh-stub-prefix

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
  sh-deps-comment "$@"
}

write-stub() {
  ### Create a stub for a Python tool

  # Key point: if the Python code changes, then the C++ code should be
  # regenerated and re-compiled

  local kind=$1
  local stub_out=$2
  shift 2

  case $kind in
    (py)
      sh-py-stub "$@" > $stub_out
      ;;
    (mycpp)
      sh-mycpp-stub "$@" > $stub_out
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
