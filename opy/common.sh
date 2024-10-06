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

# Used by scripts/release.sh too.
readonly OSH_BYTERUN=opy/_tmp/repo-with-opy/bin/osh-byterun 

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

# NOTES:
# - Exclude _devbuild/cpython-full, but include _devbuild/gen.
# - must exclude opy/testdata/, because some of it can't be compiled
# - exclude spec/ for spec/stateful tests, which are in Python 3
# Has some similarity to test/lint.sh, but not the same.
oil-python-sources() {
  local repo_root=$1
  local fmt=${2:-'%P\n'}

  # mycpp: exclude Python 3 sources
  find $repo_root \
    -name _tmp -a -prune -o \
    -name _cache -a -prune -o \
    -name _chroot -a -prune -o \
    -name _clone -a -prune -o \
    -name _deps -a -prune -o \
    -name _regtest -a -prune -o \
    -name mycpp -a -prune -o \
    -name pea -a -prune -o \
    -name yaks -a -prune -o \
    -name testdata -a -prune -o \
    -name Python-2.7.13 -a -prune -o \
    -name py-yajl -a -prune -o \
    -name spec -a -prune -o \
    -name '*.py' -a -printf "$fmt"

  # TODO: move type-annotated files to pea/, and get rid of py3_parse.py hack
}

opyc-run() {
  ../bin/opyc run "$@"
}

opyc-compile() {
  ../bin/opyc compile "$@"
}

