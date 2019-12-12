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

# Run compile-osh-parse-opt
# TODO: Make osh-parse-tcmalloc

osh-parse-small() {
  HEAPPROFILE=_tmp/osh_parse.hprof $OSH_PARSE -c 'echo hi'
}

# Why doesn't compiling with tcmalloc work?
# getline() fails with "no such file or directory", even though fopen()
# succeeded?

osh-parse() {
  set -x
  #local path=configure
  local path=benchmarks/testdata/configure

  HEAPPROFILE=_tmp/osh_parse.hprof $OSH_PARSE -n $path
  #HEAPPROFILE=_tmp/osh_parse.hprof _bin/osh_parse.opt -n 3.txt
}

readonly OSH_PARSE='_bin/osh_parse.tcmalloc '

svg-report() {
  pprof --web $OSH_PARSE "$@"
}

"$@"
