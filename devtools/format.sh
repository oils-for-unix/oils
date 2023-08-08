#!/usr/bin/env bash
#
# Run yapf formatter; it's installed in ~/wedge/ by build/deps.sh
#
# Usage:
#   test/format.sh <function name>

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

. build/dev-shell.sh  # python3 in $PATH

# Hack to prevent interference.  TODO: Make a separate wedge for yapf.
unset PYTHONPATH

. build/common.sh  # $CLANG_DIR

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

#
# Python
#

readonly YAPF_VENV='_tmp/yapf-venv'

install-yapf() {
  local venv=$YAPF_VENV

  rm -r -f -v $venv

  python3 -m venv $venv

  . $venv/bin/activate

  # 0.40.1 is the 2023-06-20 release
  #
  # Pin the version so formatting is stable!

  python3 -m pip install 'yapf == 0.40.1'

  yapf-version
}

yapf-version() {
  . $YAPF_VENV/bin/activate
  python3 -m yapf --version
}

# For now, run yapf on specific files.  TODO: could query git for the files
# that are are different from master branch, and run it on those.
yapf-files() {
  . $YAPF_VENV/bin/activate
  python3 -m yapf -i "$@"
}

#
# C++
#

clang-format() {
  # See //.clang-format for the style config.
  $CLANG_DIR/bin/clang-format --style=file "$@"
}

readonly -a CPP_FILES=(
  {asdl,core}/*.cc
  benchmarks/*.c
  cpp/*.{c,cc,h}
  mycpp/*.{cc,h} 
  mycpp/demo/*.{cc,h}
  demo/*.c

  # Could add pyext, but they have sort of a Python style
  # pyext/fanos.c
)

cpp-files() {
  shopt -s nullglob
  for file in "${CPP_FILES[@]}"; do

    echo $file
  done
}

all-cpp() {
  # see build/common.sh
  if test -n "$CLANG_IS_MISSING"; then
    log ''
    log "  *** $0: Did not find $CLANG_DIR_1"
    log "  *** Run deps/from-binary.sh to get it"
    log ''
    return 1
  fi

  cpp-files | egrep -v 'greatest.h' | xargs -- $0 clang-format -i 
  git diff
}

test-asdl-format() {
  ### Test how clang-format would like our generated code

  local file=${1:-_gen/asdl/hnode.asdl.h}

  local tmp=_tmp/hnode
  clang-format $file > $tmp
  diff -u $file $tmp
}

"$@"
