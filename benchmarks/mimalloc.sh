#!/usr/bin/env bash
#
# Usage:
#   benchmarks/mimalloc.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Docs: https://github.com/microsoft/mimalloc

readonly DIR=~/git/oilshell/mimalloc

build-ld-preload() {
  gcc -Wall -fPIC -shared -o _tmp/ld_preload_hook.so demo/ld_preload_hook.c -ldl

  gcc -o _tmp/ld_preload_main demo/ld_preload_main.c
}

# 
# These work.  mimalloc doesn't work?
#

run-main-hook() {
  LD_PRELOAD=_tmp/ld_preload_hook.so _tmp/ld_preload_main || true
}

run-osh-hook() {
  LD_PRELOAD=_tmp/ld_preload_hook.so _bin/cxx-dbg/osh -c 'echo hi'
}


#
# Mimalloc
#

build-mimalloc() {
  pushd $DIR

  # Unity build!
  # -fPIC for shared library
  gcc -O2 -fPIC -I include -o mimalloc.o -c src/static.c
  ls -l mimalloc.*

  # -lpthread required
  gcc -shared -o mimalloc.so mimalloc.o -lpthread

  popd
}

# https://microsoft.github.io/mimalloc/environment.html

# Not working, try STATIC linking
# https://microsoft.github.io/mimalloc/overrides.html

run-main-mim() {
  # Doesn't show stats?
  # MIMALLOC_SHOW_STATS=1 LD_PRELOAD=$DIR/mimalloc.so ls

  # Works
  MIMALLOC_VERBOSE=1 LD_PRELOAD=$DIR/mimalloc.so \
    _tmp/ld_preload_main
}

run-osh-mim() {
  local osh=_bin/cxx-opt/osh

  #local osh=_bin/cxx-opt/mycpp/demo/gc_header

  #local osh=_bin/cxx-dbg/osh

  ninja $osh
  #export MIMALLOC_SHOW_STATS=1
  MIMALLOC_VERBOSE=1 LD_PRELOAD=$DIR/mimalloc.so \
     $osh "$@"
}

# No stats?
osh-demo() {
  run-osh-mim -c 'for i in $(seq 1000); do echo $i; done'
}



"$@"
