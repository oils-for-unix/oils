#!/usr/bin/env bash
#
# Usage:
#   benchmarks/gperftools.sh <function name>

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

readonly OILS_CPP='_bin/oils-for-unix.tcmalloc '

collect-small() {
  HEAPPROFILE=_tmp/small-parse.hprof $OILS_CPP -c 'echo hi'

  echo 'echo hi' > _tmp/h.sh
  HEAPPROFILE=_tmp/small-eval.hprof $OILS_CPP -n _tmp/h.sh
}

collect-big() {
  #local path=benchmarks/testdata/configure
  local path=${1:-configure}

  HEAPPROFILE=_tmp/big-parse.hprof $OILS_CPP --ast-format none -n $path

  # Run 200 iterations of fib(44).  Got about 18 MB of heap usage.
  # (This matches the 200 iterations in benchmarks/compute.sh, which shows 60
  # MB max RSS)
  HEAPPROFILE=_tmp/big-eval.hprof $OILS_CPP benchmarks/compute/fib.sh 200 44
}

# e.g. pass _tmp/osh_parse.hprof.0001.heap
browse() {
  ### Open it in a browser
  pprof --web $OILS_CPP "$@"
}

svg() {
  local in=$1
  local out=${in%.heap}.svg
  pprof --svg $OILS_CPP "$@" > $out

  echo "Wrote $out"
}

"$@"
