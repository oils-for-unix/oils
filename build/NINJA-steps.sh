#!/usr/bin/env bash
#
# Usage:
#   build/NINJA-steps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

shwrap-py() {
  local main=$1
  echo 'PYTHONPATH=$REPO_ROOT:$REPO_ROOT/vendor exec $REPO_ROOT/'$main' "$@"'
}

shwrap-mycpp() {
  cat <<'EOF'
MYPYPATH=$1    # e.g. $REPO_ROOT/mycpp
out=$2
shift 2

. $REPO_ROOT/mycpp/common-vars.sh  # for $MYCPP_VENV $MYPY_REPO

. $MYCPP_VENV/bin/activate  # so MyPy can import

tmp=$out.tmp  # avoid creating partial files

PYTHONPATH="$REPO_ROOT:$MYPY_REPO" MYPYPATH="$MYPYPATH" \
  ../oil_DEPS/python3 mycpp/mycpp_main.py --cc-out $tmp "$@"
status=$?

mv $tmp $out
exit $status
EOF
}

shwrap-pea() {

  cat <<'EOF'
MYPYPATH=$1    # e.g. $REPO_ROOT/mycpp
out=$2
shift 2

tmp=$out.tmp  # avoid creating partial files

PYTHONPATH="$REPO_ROOT:$MYPY_REPO" MYPYPATH="$MYPYPATH" \
  ../oil_DEPS/python3 pea/pea_main.py cpp "$@" > $tmp
status=$?

mv $tmp $out
exit $status
EOF
}

print-shwrap() {
  local template=$1
  local unused=$2
  shift 2

  cat << 'EOF'
#!/bin/sh
REPO_ROOT=$(cd "$(dirname $0)/../.."; pwd)
EOF

  case $template in
    (py)
      local main=$1  # additional arg
      shift
      shwrap-py $main
      ;;
    (mycpp)
      shwrap-mycpp
      ;;
    (pea)
      shwrap-pea
      ;;
    (*)
      die "Invalid template '$template'"
      ;;
  esac

  echo
  echo '# DEPENDS ON:'
  for dep in "$@"; do
    echo "#   $dep"
  done
}

write-shwrap() {
  ### Create a shell wrapper for a Python tool

  # Key point: if the Python code changes, then the C++ code should be
  # regenerated and re-compiled

  local unused=$1
  local stub_out=$2

  print-shwrap "$@" > $stub_out
  chmod +x $stub_out
}

# sourced by devtools/bin.sh
if test $(basename $0) = 'NINJA-steps.sh'; then
  "$@"
fi
