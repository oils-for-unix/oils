#!/usr/bin/env bash
#
# Usage:
#   devtools/py_refactor.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

list() {
  devtools/py_refactor.py -l

  #devtools/py_refactor.py -h
}

demo() {
  #devtools/py_refactor.py -f itertools_imports builtin/*_osh.py

  devtools/py_refactor.py -f itertools_imports */*.py -w
}

hi() {
  # copied from /usr/lib/python3.11/lib2to3/fixes

  ls devtools/fixes/*
}

"$@"
