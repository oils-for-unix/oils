#!/bin/bash
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

  tar --create --transform "$sed_expr" --file $out \
    LICENSE.txt \
    README-native.txt \
    build/common.sh \
    build/mycpp.sh \
    cpp/ \
    mycpp/mylib.{cc,h} \
    _devbuild/gen/*.h \
    _build/cpp/

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
  build/mycpp.sh compile-osh-parse
  build/mycpp.sh compile-osh-parse-opt
  popd

  git add oil-native-$OIL_VERSION

  git status
  echo "Now run git commit"

  popd
}

"$@"
