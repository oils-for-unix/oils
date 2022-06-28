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
  # TODO:
  # - Invoke the compiler to get all headers, like we do with CPython.
  # - Needs to be updated for the new GC runtime
  # - Provide a way to run C++ tests?  Unit tests and smoke tests alike.
  # - MESSY: Are we using asdl/runtime?  It contains the SAME DEFINITIONS as
  #   _build/cpp/osh_eval.h.  We use it to run ASDL unit tests without
  #   depending on Oil.

  find \
    LICENSE.txt \
    README-native.txt \
    asdl/runtime.h \
    build/common.sh \
    build/native.sh \
    cpp/ \
    mycpp/common.sh \
    mycpp/mylib.{cc,h} \
    mycpp/gc_heap.{cc,h} \
    mycpp/my_runtime.{cc,h} \
    mycpp/myerror.h \
    mycpp/common.h \
    _devbuild/gen/*.h \
    _build/cpp/ \
    _build/oil-native.sh \
    -name _bin -a -prune -o -type f -a -print
}

make-tar() {
  local app_name='oil-native'

  local sed_expr="s,^,${app_name}-${OIL_VERSION}/,"

  local out=_release/${app_name}-${OIL_VERSION}.tar

  # NOTE: Could move this to the Makefile, which will make it
  mkdir -p _release 

  # TODO: This could skip compiling oil-native
  build/dev.sh oil-cpp

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

  pushd oil-native-$OIL_VERSION
  build/native.sh tarball-demo
  popd
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
  _build/oil-native.sh '' dbg SKIP_REBUILD
  _build/oil-native.sh '' opt SKIP_REBUILD
  popd

  git add oil-native-$OIL_VERSION

  git status
  echo "Now run git commit"

  popd
}

"$@"
