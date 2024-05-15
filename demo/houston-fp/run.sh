#!/usr/bin/env bash
#
# Demonstrated re2c and Zephyr ASDL.
#
# Note: this is a "TASK FILE"!  (Cleaner than Makefile)
#
# Demo
# - show-oils
# - show static type error, caught by MyPy
# - show generated Python code
# - generated C++
#
# Usage:
#   demo/houston-fp/run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh

readonly BASE_DIR=_tmp/houston-fp

#
# Utilities
#

# Note: not showing metaprogramming from frontend/lexer_def.py - only re2c

re2c-gen() {
  local name=$1
  shift
  # Rest are flags

  #re2c --help
  #return

  set -x
  # Generate C switch and goto
  # Flags copied from Oils

  local more_flags=''
  # Extra flags for number
  #local more_flags='-i --case-ranges'

  # -i to debug the generated source directly?  Doesn't work
  # --no-debug-info
  #local more_flags='-i'
  #local more_flags='--debug-output'
  #local more_flags='--no-debug-info'

  re2c \
    $more_flags \
    -W -Wno-match-empty-string -Werror \
    -o $BASE_DIR/$name-re2c.cc demo/houston-fp/$name.re2c.cc

  # Generate DOT graph (text)
  re2c --emit-dot \
    -o $BASE_DIR/$name-re2c.dot demo/houston-fp/$name.re2c.cc

  # Generate image
  dot -Tpng \
    -o $BASE_DIR/$name-re2c.png $BASE_DIR/$name-re2c.dot

  set +x
}

compile() {
  local name=$1

  c++ -std=c++11 -g \
    -o $BASE_DIR/$name-re2c $BASE_DIR/$name-re2c.cc
}

# TUI debugger!
debug() {
  local name=${1:-favorite}
  shift

  gdb --tui --args _tmp/houston-fp/$name-re2c "$@"
}

number() {
  re2c-gen number
  compile number

  $BASE_DIR/number-re2c ''
  $BASE_DIR/number-re2c 'z'
  $BASE_DIR/number-re2c '123'
}

favorite() {
  re2c-gen favorite

  ls -l $BASE_DIR/*.png
  echo

  wc -l $BASE_DIR/favorite*.{dot,h}
  echo

  compile favorite

  $BASE_DIR/favorite-re2c '"hello world"'
  $BASE_DIR/favorite-re2c '""'
  $BASE_DIR/favorite-re2c '"foo \n bar"'
  $BASE_DIR/favorite-re2c '"bad \"'
  $BASE_DIR/favorite-re2c '"unclosed '
  $BASE_DIR/favorite-re2c 'unquoted'

  echo
}

show-oils() {
  # 68 instances
  egrep '%[a-zA-Z]+' */*.asdl
  echo

  egrep -C 1 '%[a-zA-Z]+' */*.asdl
}

check-types() {
  time MYPYPATH=".:pyext:$BASE_DIR" python3 -m mypy \
    --py2 \
    --follow-imports=silent \
    demo/houston-fp/demo_main.py
}

#
# ASDL
#

readonly SCHEMA=demo/houston-fp/demo.asdl

asdl-main() {
  PYTHONPATH='.:vendor/' asdl/asdl_main.py "$@"
}

count-lines() {
  wc -l $SCHEMA
  echo

  wc -l $BASE_DIR/*
  echo
}

gen-asdl() {
  asdl-main mypy $SCHEMA > $BASE_DIR/demo_asdl.py

  asdl-main cpp $SCHEMA $BASE_DIR/demo.asdl  # out prefix
}

asdl-demo() {
  PYTHONPATH=".:vendor/:$BASE_DIR" demo/houston-fp/demo_main.py
}

asdl-case-classes() {
  gen-asdl

  count-lines

  check-types

  asdl-demo
}

soil-run() {
  # For local testing
  rm -r -f $BASE_DIR/*
  mkdir -p $BASE_DIR

  asdl-case-classes
}

"$@"
