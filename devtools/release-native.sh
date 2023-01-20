#!/usr/bin/env bash
# 
# Make a tarball containing native (C++) code.
#
# Usage:
#   devtools/release-native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# adapted from build/ovm-compile.sh
# and devtools/release.sh

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

gen-oils-sh() {
  PYTHONPATH=. build/ninja_main.py shell
  chmod +x _build/oils.sh
}

make-tar() {
  local app_name='oil-native'

  local tar=_release/${app_name}.tar

  # NOTE: Could move this to the Makefile, which will make it
  mkdir -p _release 

  gen-oil-native-sh
  # Build default target to generate code
  ninja

  local sed_expr="s,^,${app_name}-${OIL_VERSION}/,"
  PYTHONPATH=. build/ninja_main.py tarball-manifest \
    | xargs -- tar --create --transform "$sed_expr" --file $tar

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
  ./configure
  _build/oils.sh '' dbg SKIP_REBUILD
  _build/oils.sh '' opt SKIP_REBUILD
  popd

  git add oil-native-$OIL_VERSION

  git status
  echo "Now run git commit"

  popd
}

"$@"
