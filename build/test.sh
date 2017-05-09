#!/bin/bash
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
  _bin/hello.bundle 
  if test $? = 1; then
    echo OK
  else
    echo 'FAIL: expected exit code 1'
    exit 1
  fi
}

oil-bundle() {
  _bin/oil.bundle osh -c 'echo hi'
  ln -s oil.bundle _bin/osh
  _bin/osh -c 'echo hi from osh'
}

_tarball() {
  local name=${1:-hello}
  local tmp=_tmp/$name-tar-test
  rm -r -f $tmp
  mkdir -p $tmp
  cd $tmp
  tar --extract < ../../_release/$name.tar
  make _bin/$name.bundle
  _bin/$name.bundle
}

hello-tar() {
  _tarball hello
}

oil-tar() {
  _tarball oil
}



"$@"
