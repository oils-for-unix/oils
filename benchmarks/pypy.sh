#!/bin/bash
#
# Summary: PyPy is slower than CPython for parsing.  (I bet it also uses more
# memory, although I didn't measure that.)
#
# I don't plan on using PyPy, but this is simple enough to save for posterity.
#
# Usage:
#   ./pypy.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly PYPY=~/install/pypy2-v5.9.0-linux64/bin/pypy

readonly ABUILD=~/git/alpine/abuild/abuild 

parse-abuild() {
  local vm=$1
  local out=_tmp/pypy
  mkdir -p $out

  time $vm bin/oil.py osh \
    --dump-proc-status-to $out/proc-status.txt \
    -n $ABUILD >/dev/null
}

# ~3.5 seconds
parse-with-cpython() {
  parse-abuild python
}

# ~4.8 seconds
# NOTE: We could run it in a loop to see if the JIT warms up, but that would
# only be for curiousity.  Most shell processes are short-lived, so it's the
# wrong thing to optimize for.
parse-with-pypy() {
  parse-abuild $PYPY
}

"$@"
