#!/usr/bin/env bash
#
# Miscellaneous scripts that don't belong elsewhere.
#
# Usage:
#   ./run.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Python 3 stuff
replace-print() {
  #grep 'print >>' oil/*.py
  grep 'print ' {osh,core}/*.py
  #sed -i --regexp-extended -e 's/print (.*)/print(\1)/' {osh,core}/*.py
}

readonly LINKS='oil oilc osh sh wok boil true false'

make-bin-links() {
  # bin/ is for running with the Python interpreter.  _bin/ is for running with
  # OVM app bundles.
  mkdir -p bin _bin

  for link in $LINKS; do
    ln -s -f --verbose oil.py bin/$link
  done

  for link in $LINKS; do
    ln -s -f --verbose oil.ovm _bin/$link
  done
}

# For OPy, called by opy/smoke.sh
make-pyc-links() {
  for link in $LINKS; do
    ln -s -f --verbose oil.pyc bin/$link
  done
}

"$@"
