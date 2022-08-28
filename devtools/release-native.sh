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
  # - MESSY: asdl/runtime.h is used by _build/cpp/*_asdl.cc

  find \
    LICENSE.txt \
    README-native.txt \
    asdl/runtime.h \
    build/common.sh \
    build/native.sh \
    cpp/*.{cc,h,sh} \
    mycpp/common.sh \
    mycpp/*.{cc,h} \
    _devbuild/gen/*.h \
    _build/cpp/ \
    _build/oil-native.sh \
    -name _bin -a -prune -o -type f -a -print
}

make-tar() {
  local app_name='oil-native'

  local tar=_release/${app_name}.tar

  # NOTE: Could move this to the Makefile, which will make it
  mkdir -p _release 

  # TODO: Use Ninja here?
  #
  # ninja _release/oil-native.tar
  #
  # The ./NINJA-config.sh step could even read oil-native.sh
  #
  # Then you wouldn't need a duplicate manifest

  build/dev.sh cpp-codegen

  local sed_expr="s,^,${app_name}-${OIL_VERSION}/,"
  manifest | xargs -- tar --create --transform "$sed_expr" --file $tar

  local tar_xz=_release/${app_name}-${OIL_VERSION}.tar.xz
  xz -c $tar > $tar_xz

  ls -l _release
}

test-tar() {
  local tmp=_tmp/native-tar-test  # like oil-tar-test
  rm -r -f $tmp
  mkdir -p $tmp
  cd $tmp
  tar -x < ../../_release/oil-native.tar

  pushd oil-native-$OIL_VERSION
  build/native.sh tarball-demo
  popd
}

extract-for-benchmarks() {
  local tar=$PWD/_release/oil-native.tar
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
