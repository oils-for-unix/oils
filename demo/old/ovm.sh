#!/usr/bin/env bash
#
# Miscellaneous scripts for figuring out OVM.
#
# Usage:
#   ./ovm.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # $PY27

grep-cpython() {
  find $PY27 -type f | xargs grep "$@"
}

grep-cpython-c() {
  find $PY27 -type f -a -name '*.[ch]' | xargs grep "$@"
}

# https://stackoverflow.com/questions/2224334/gcc-dump-preprocessor-defines

# 493 variables.
pp-vars() {
  gcc -E -dM - < $PY27/pyconfig.h
}

# Modify this function to trace imports.  It helped with 're'.
# Where do codecs.c and codecs.py get imported?
# codecs.py is from encodings, but I don't know where that gets imported.
#
# I think runpy use encodings.
blame-import() {
  PYTHONVERBOSE=9 \
  _OVM_RESOURCE_ROOT=. PYTHONPATH=. \
    python -S -c 'from bin import oil; import sys; print sys.modules["codecs"]'
}

"$@"
