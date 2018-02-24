#!/usr/bin/env bash
#
# Miscellaneous scripts that don't belong elsewhere.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for OIL_SYMLINKS

# Python 3 stuff
replace-print() {
  #grep 'print >>' oil/*.py
  grep 'print ' {osh,core}/*.py
  #sed -i --regexp-extended -e 's/print (.*)/print(\1)/' {osh,core}/*.py
}

make-bin-links() {
  # bin/ is for running with the Python interpreter.  _bin/ is for running with
  # OVM app bundles.
  mkdir -p bin _bin

  for link in "${OIL_SYMLINKS[@]}"; do
    ln -s -f --verbose oil.py bin/$link
  done

  for link in "${OIL_SYMLINKS[@]}"; do
    ln -s -f --verbose oil.ovm _bin/$link
  done
}

"$@"
