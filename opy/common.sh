#!/usr/bin/env bash
#
# Usage:
#   ./common.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly GRAMMAR=$THIS_DIR/_tmp/py27.grammar.pickle

opy_() {
  PYTHONPATH=$THIS_DIR $THIS_DIR/../bin/opy_.py "$@"
}

opyg() {
  opy_ -g $GRAMMAR -- "$@"
}

# The old compile path
_compile-one() {
  # The production testlist_starexpr is unhandled in the compiler package.
  # Python 2.7 doesn't have it.
  #local g=2to3.grammar 
  local g=py27.grammar
  # pgen2 + old compiler/
  #PYTHONPATH=. ./opy_main.py $g old-compile "$@"

  # opy is pgen2 + compiler2
  opyg compile "$@"
}

_compile2-one() {
  opyg compile2 "$@"
}

_stdlib-compile-one() {
  # Run it from source, so we can patch.  Bug still appears.

  #$PY27/python misc/stdlib_compile.py "$@"

  # No with statement
  #~/src/Python-2.4.6/python misc/stdlib_compile.py "$@"

  # NOT here
  #~/src/Python-2.6.9/python misc/stdlib_compile.py "$@"

  # Bug appears in Python 2.7.9 too!
  #~/src/Python-2.7.9/python misc/stdlib_compile.py "$@"

  # Why is it in 2.7.2?  No hash randomization there?
  #~/src/Python-2.7.2/python misc/stdlib_compile.py "$@"

  # Woah it took 51 iterations to find!
  # Much rarer in Python 2.7.0.  100 iterations didn't find it?
  # Then 35 found it.  Wow.
  ~/src/Python-2.7/python misc/stdlib_compile.py "$@"

  #misc/stdlib_compile.py "$@"
}

_ccompile-one() {
  misc/ccompile.py "$@"
}
