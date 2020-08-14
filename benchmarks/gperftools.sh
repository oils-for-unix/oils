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

collect-small() {
  HEAPPROFILE=_tmp/small-parse.hprof $OSH_EVAL -c 'echo hi'

  echo 'echo hi' > _tmp/h.sh
  HEAPPROFILE=_tmp/small-eval.hprof $OSH_EVAL -n _tmp/h.sh
}

collect-big() {
  #local path=benchmarks/testdata/configure
  local path=${1:-configure}

  HEAPPROFILE=_tmp/big-parse.hprof $OSH_EVAL --ast-format none -n $path

  # Run 100 iterations of fib(44).  Got about 18 MB of heap usage.
  HEAPPROFILE=_tmp/big-eval.hprof $OSH_EVAL benchmarks/compute/fib.sh 100 44
}

# e.g. pass _tmp/osh_parse.hprof.0001.heap
browse() {
  ### Open it in a browser
  pprof --web $OSH_EVAL "$@"
}

svg() {
  local in=$1
  local out=${in%.hprof}.svg
  pprof --svg $OSH_EVAL "$@" > $out

  echo "Wrote $out"
}

"$@"
