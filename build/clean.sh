#!/usr/bin/env bash
#
# Usage:
#   build/clean.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# To test building stdlib.
clean-pyc() {
  # skip _chroot, _tmp, etc.  But delete __init__.pyc
  find . \( -type d -a -name '_*' -a -prune \) -o -name '*.pyc' -a -print |
    xargs --no-run-if-empty -- rm --verbose
}

py() {
  rm -f --verbose *.so
  rm -r -f --verbose _devbuild _cache

  # These can be stale after renaming things
  clean-pyc
}

cpp() {
  ### e.g. to time ninja build
  rm -r -f --verbose _bin _build _gen _release _test build.ninja

  clean-pyc

  # _release is for docs
}

all() {
  rm -r -f --verbose _tmp
  py
  cpp
}

# This is 'make clean' for the oil.ovm build.
#
# - Take care not to remove _build/oil/bytecode-opy.zip, etc.
# - There are no object files written now.
# - We're not cleaning _build/detect-config.* ?

source-tarball-build() {
  rm -f -v _bin/oil.{ovm,ovm-dbg}
  # NOTE: delete ovm-opt, ovm-opt.{stripped,symbols}
  rm -f -v \
      _build/oil/{ovm-opt,ovm-dbg} \
      _build/oil/ovm-opt.{stripped,symbols}
}


if test $# -eq 0; then
  # clean all if no args
  all
else
  "$@"
fi
