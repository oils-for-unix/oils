#!/usr/bin/env bash
# 
# Make a tarball containing native (C++) code.
#
# Usage:
#   ./release-native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# adapted from build/compile.sh
# and devtools/release.sh

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

manifest() {
  # Skip _bin/heap, etc.

  # TODO: Invoke the compiler to get all headers, like we do with CPython.

  find \
    LICENSE.txt \
    README-native.txt \
    asdl/runtime.h \
    build/common.sh \
    build/mycpp.sh \
    cpp/ \
    mycpp/mylib.{cc,h} \
    mycpp/gc_heap.{cc,h} \
    mycpp/my_runtime.{cc,h} \
    mycpp/myerror.h \
    mycpp/common.h \
    _devbuild/gen/*.h \
    _build/cpp/ \
    -name _bin -a -prune -o -type f -a -print
}

make-tar() {
  local app_name='oil-native'

  local sed_expr="s,^,${app_name}-${OIL_VERSION}/,"

  local out=_release/${app_name}-${OIL_VERSION}.tar

  # NOTE: Could move this to the Makefile, which will make it
  mkdir -p _release 

  build/dev.sh oil-cpp
  # Note: could run build/mycpp.sh osh-parse-smoke

  # TODO:
  # - Provide a way to run C++ tests?  Unit tests and smoke tests alike.
  # - MESSY: asdl/runtime.h contains the SAME DEFINITIONS as
  #   _build/cpp/osh_eval.h.  But we use it to run ASDL unit tests without
  #   depending on Oil.

  manifest | xargs -- tar --create --transform "$sed_expr" --file $out

  xz -c $out > $out.xz

  ls -l _release
}

test-tar() {
  local tmp=_tmp/native-tar-test  # like oil-tar-test
  rm -r -f $tmp
  mkdir -p $tmp
  cd $tmp
  tar -x < ../../_release/oil-native-$OIL_VERSION.tar

  cd oil-native-$OIL_VERSION
  build/mycpp.sh tarball-demo
}

extract-for-benchmarks() {
  local tar=$PWD/_release/oil-native-$OIL_VERSION.tar
  local dest='../benchmark-data/src'
  mkdir -p $dest

  pushd $dest
  git pull
  tar -x < $tar

  # For benchmarks
  pushd oil-native-$OIL_VERSION
  build/mycpp.sh compile-oil-native
  build/mycpp.sh compile-oil-native-opt
  popd

  git add oil-native-$OIL_VERSION

  git status
  echo "Now run git commit"

  popd
}

"$@"
