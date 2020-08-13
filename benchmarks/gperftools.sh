#!/bin/bash
#
# Usage:
#   ./gperftools.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Hm these appear to be ancient versions, google-pprof --version says 2.0, but
# we're on 2.7
#
# https://github.com/gperftools/gperftools/releases

uninstall() {
  sudo apt remove google-perftools libgoogle-perftools-dev
}

# /usr/local/bin/pprof also seems to have the 2.0 version number!
download() {
  wget --directory _deps \
    'https://github.com/gperftools/gperftools/releases/download/gperftools-2.7/gperftools-2.7.tar.gz'
}

readonly OSH_EVAL='_bin/osh_eval.tcmalloc '

run-small() {
  HEAPPROFILE=_tmp/osh_parse.hprof $OSH_EVAL -c 'echo hi'

  echo 'echo hi' > _tmp/h.sh
  HEAPPROFILE=_tmp/osh_parse.hprof $OSH_EVAL -n _tmp/h.sh

  # Parse it.  Works fine.
  #HEAPPROFILE=_tmp/osh_parse.hprof $OSH_EVAL -n -c 'echo hi'
}

parse-big() {
  #local path=benchmarks/testdata/configure
  local path=${1:-configure}

  HEAPPROFILE=_tmp/osh_parse.hprof $OSH_EVAL --ast-format none -n $path
}

# e.g. pass _tmp/osh_parse.hprof.0001.heap
svg-report() {
  pprof --web $OSH_EVAL "$@"
}

"$@"
