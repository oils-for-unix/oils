#!/usr/bin/env bash
#
# Run yapf formatter; it's installed in ~/wedge/ by build/deps.sh
#
# Usage:
#   test/format.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source build/dev-shell.sh  # python3 in $PATH

# Hack to prevent interference.  TODO: Make a separate wedge for yapf.
unset PYTHONPATH

source build/common.sh  # $CLANG_DIR

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

yapf-known() {
  ### yapf some files that have been normalized

  time yapf-files \
    {asdl,benchmarks,build,builtin,core,data_lang,display,doctools,frontend,lazylex,mycpp,mycpp/examples,osh,spec/*,test,yaks,ysh}/*.py \
    */NINJA_subgraph.py
}

yapf-changed() {
  branch="${1:-master}"

  #git diff --name-only .."$branch" '*.py'

  git diff --name-only .."$branch" '*.py' \
    | xargs --no-run-if-empty -- $0 yapf-files 
}

#
# Doc strings - one off
#

install-docformatter() {
  python3 -m pip install docformatter
}

docstrings() {
  ### Format docstrings - NOT done automatically, because it can mangle them

  # Requires manual fix-up

  #time test/lint.sh py2-files-to-lint \
  #  | xargs --verbose -- python3 -m docformatter --in-place

  python3 -m docformatter --in-place test/*.py
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
  data_lang/*.{c,cc,h}
  mycpp/*.{cc,h} 
  mycpp/demo/*.{cc,h}
  demo/*.c
  doctools/*.{h,cc}
  yaks/*.h

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

task-five "$@"
