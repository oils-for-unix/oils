#!/bin/bash
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

make-bin-links() {
  mkdir -p bin
  for link in oil osh sh wok boil; do
    ln -s -f --verbose oil.py bin/$link
  done
}

"$@"
