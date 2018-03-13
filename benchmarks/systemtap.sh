#!/bin/bash
#
# Following:
# https://docs.python.org/3/howto/instrumentation.html
#
# Couldn't get this to work.  Even building it from source doesn't work!
# 'stap' invokes a compiler, and I get compiler errors.
#
# It appears to be very brittle.
#
# https://stackoverflow.com/questions/46047270/systemtap-error-on-ubuntu
#
# Usage:
#   ./systemtap.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

deps() {
  # 'stap' lives in systemtap package
  sudo apt install systemtap systemtap-sdt-dev
}

stap-deps() {
  # For DWARF debugging info, interesting.
  sudo apt install libdw-dev libdw1
}

# NOTE: systemtap-3.2 is out, but doesn't compile on Ubuntu xenial!
download() {
  wget --no-clobber --directory _tmp \
    https://sourceware.org/systemtap/ftp/releases/systemtap-3.1.tar.gz
}

extract() {
  cd _tmp
  tar -x -z < systemtap-3.1.tar.gz
}

readonly PY36=~/src/languages/Python-3.6.1

build-python() {
  pushd $PY36
  # There is no --with-systemtap/
  ./configure --with-dtrace
  make -j 7
  popd
}

# Default Python build doesn't have it
elf() {
  readelf -n $(which python3)
  echo ---
  # Now this has "stapsdt" -- SystemTap probe descriptors.
  readelf -n $PY36/python
}

_demo() {
  #local stp="$PWD/benchmarks/call-hierarchy.stp"

  # C compile errors?  It's getting further.
  #local stp="$PY36/Lib/test/dtracedata/call_stack.stp"
  local stp="$PY36/Lib/test/dtracedata/gc.stp"
  #local stp="$PY36/Lib/test/dtracedata/assert_usable.stp"

  local py="$PWD/test/sh_spec.py"

  pushd $PY36
  stap -v $stp -c "./python $py"
  popd
}
demo() { sudo $0 _demo; }

"$@"
