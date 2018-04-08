#!/usr/bin/env bash
#
# Common functions.
# NOTE: The module that sources this must initialize THIS_DIR.
#
# Usage:
#   ./common.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly GRAMMAR=_tmp/py27.grammar.pickle

log() {
  echo "$@" >&2
}

die() {
  log "FATAL: $@"
  exit 1
}

opy_() {
  PYTHONPATH=$THIS_DIR $THIS_DIR/../bin/opy_.py "$@"
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

# NOTES:
# - Exclude _devbuild/cpython-full, but include _devbuild/gen.
# - must exclude opy/testdata/, because some of it can't be compiled
# Has some similiarity to test/lint.sh, but not the same.
oil-python-sources() {
  local repo_root=$1
  local fmt=${2:-'%P\n'}

  find $repo_root \
    -name _tmp -a -prune -o \
    -name _chroot -a -prune -o \
    -name _deps -a -prune -o \
    -name _regtest -a -prune -o \
    -name cpython-full -a -prune -o \
    -name testdata -a -prune -o \
    -name Python-2.7.13 -a -prune -o \
    -name '*.py' -a -printf "$fmt"
}

opyc-run() {
  ../bin/opyc run "$@"
}
opyc-compile() {
  ../bin/opyc compile "$@"
}

