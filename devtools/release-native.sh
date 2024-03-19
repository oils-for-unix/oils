#!/usr/bin/env bash
# 
# Make a tarball containing native (C++) code.
#
# Usage:
#   devtools/release-native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

# adapted from build/ovm-compile.sh
# and devtools/release.sh

OIL_VERSION=$(head -n 1 oil-version.txt)
readonly OIL_VERSION

gen-oils-sh() {
  PYTHONPATH=. build/ninja_main.py shell
  chmod +x _build/oils.sh
}

tarball-manifest() {
  # 100 files
  PYTHONPATH=. build/ninja_main.py tarball-manifest 
}

make-tar() {
  local app_name='oils-for-unix'

  local tar=_release/${app_name}.tar

  # NOTE: Could move this to the Makefile, which will make it
  mkdir -p _release 

  gen-oils-sh
  # Build default target to generate code
  ninja

  local sed_expr="s,^,${app_name}-${OIL_VERSION}/,"
  tarball-manifest | xargs -- tar --create --transform "$sed_expr" --file $tar

  local tar_gz=_release/${app_name}-${OIL_VERSION}.tar.gz
  gzip -c $tar > $tar_gz

  ls -l _release
}

test-tar() {
  local install=${1:-}

  local tmp=_tmp/native-tar-test  # like oil-tar-test
  rm -r -f $tmp
  mkdir -p $tmp
  cd $tmp
  tar -x < ../../_release/oils-for-unix.tar

  pushd oils-for-unix-$OIL_VERSION
  build/native.sh tarball-demo

  if test -n "$install"; then
    sudo ./install
  fi

  popd
}

extract-for-benchmarks() {
  local install=${1:-}

  local tar=$PWD/_release/oils-for-unix.tar
  local dest='../benchmark-data/src'
  mkdir -p $dest

  pushd $dest
  git pull
  tar -x < $tar

  # For benchmarks
  pushd oils-for-unix-$OIL_VERSION

  # Remove binaries left over from old attempts
  rm -v _bin/cxx-{dbg,opt}-sh/* || true

  ./configure
  _build/oils.sh '' dbg
  _build/oils.sh '' opt

  build/native.sh tarball-demo

  if test -n "$install"; then
    sudo ./install
  fi
  popd

  git add oils-for-unix-$OIL_VERSION

  git status
  echo "Now run git commit"

  popd
}

#
# Repro bug #1731 -- passing duplicate files to tar results in weird hard
# links!
#

install-bsdtar() {
  sudo apt-get install libarchive-tools
}

test-with-bsdtar() {
  pushd _release
  bsdtar -x < oils-for-unix.tar
  popd
}

"$@"
