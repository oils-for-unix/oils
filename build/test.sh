#!/usr/bin/env bash
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

make-zip() {
  local out=_tmp/make-zip-test.zip 
  build/make_zip.py $out _build/runpy-deps-py.txt
  unzip -l $out
}

hello-bundle() {
  set +o errexit
  _bin/hello.ovm
  if test $? = 1; then
    echo OK
  else
    echo 'FAIL: expected exit code 1'
    exit 1
  fi
}

oil-bundle() {
  _bin/oil.ovm osh -c 'echo hi'
  ln -s -f oil.ovm _bin/osh
  _bin/osh -c 'echo hi from osh'
}

_tarball() {
  local name=${1:-hello}
  local version=${2:-0.0.0}

  local tmp=_tmp/${name}-tar-test
  rm -r -f $tmp
  mkdir -p $tmp
  cd $tmp
  tar --extract -z < ../../_release/$name-$version.tar.gz

  cd $name-$version
  ./configure

  # Build the fast one for a test.
  # TODO: Maybe edit the Makefile to change the top target.
  local bin=_bin/${name}.ovm  # not dbg
  time make $bin
  $bin --version
}

hello-tar() {
  _tarball hello $(head -n 1 build/testdata/hello-version.txt)
}

oil-tar() {
  _tarball oil $(head -n 1 oil-version.txt)
}

# Test the different entry points.
ovm-main-func() {
  echo ---
  echo 'Running nothing'
  echo ---
  local ovm=_build/hello/ovm-dbg

  _OVM_RUN_SELF=0 $ovm || true

  echo ---
  echo 'Running bytecode.zip'
  echo ---

  _OVM_RUN_SELF=0 $ovm _build/hello/bytecode.zip || true

  # Doesn't work because of stdlib deps?
  echo ---
  echo 'Running lib.pyc'
  echo ---

  _OVM_RUN_SELF=0 $ovm build/testdata/lib.pyc

}


"$@"
