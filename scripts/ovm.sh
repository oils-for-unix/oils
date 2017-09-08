#!/bin/bash
#
# Miscellaneous scripts for figuring out OVM.
#
# Usage:
#   ./ovm.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # $PY27

grep-python() {
  find $PY27 -type f | xargs grep "$@"
}

# https://stackoverflow.com/questions/2224334/gcc-dump-preprocessor-defines

# 493 variables.
pp-vars() {
  gcc -E -dM - < $PY27/pyconfig.h
}

"$@"
