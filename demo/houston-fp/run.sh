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

favorite-regex() {
  re2c --help
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
