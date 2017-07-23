#!/bin/bash
#
# Usage:
#   ./release.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

# TODO: enforce that there is a release-0.0.0 branch?
build-and-test() {
  rm -r -f _devbuild _build _release
  rm -f _bin/oil.*

  build/pylibc.sh build  # for libc.so
  build/doc.sh osh-quick-ref  # for _devbuild/osh_help.py

  test/unit.sh all

  build/prepare.sh configure
  build/prepare.sh build-python

  # Could do build/prepare.sh test too?
  make clean
  make

  # Make sure
  test/spec.sh smoke

  test/spec.sh all

  # Build the oil tar
  $0 oil

  # Test the oil tar
  build/test.sh oil-tar

  # TODO: Make a clean alpine chroot?
  test/alpine.sh copy-tar oil
  test/alpine.sh test-tar oil
}

# Release procedure after build-and-test:
#
# ./local.sh publish-doc
# ./local.sh publish-release
# ./local.sh publish-spec

# TODO:
# - publish-unit
# - Update the doc/ "latest" redirect?
# - Publish Alpine test log?  (along with build stats?)

_compressed-tarball() {
  local name=${1:-hello}
  local version=${2:-0.0.0}

  local in=_release/$name.tar
  local out=_release/$name-$version.tar.gz

  # Overwrite it to cause rebuild of oil.tar (_build/oil/bytecode.zip will be
  # out of date.)
  build/actions.sh write-release-date

  make $in
  time gzip -c $in > $out
  ls -l $out

  # xz version is considerably smaller.  1.15 MB  vs. 1.59 MB.
  local out2=_release/$name-$version.tar.xz
  time xz -c $in > $out2
  ls -l $out2
}

oil() {
  _compressed-tarball oil $OIL_VERSION
}

hello() {
  _compressed-tarball hello $(head -n 1 build/testdata/hello-version.txt)
}

publish-doc() {
  local user=$1
  local host=$2

  build/doc.sh osh-quick-ref
  build/doc.sh install
  build/doc.sh index
  rsync --archive --verbose \
    _build/doc/ "$user@$host:oilshell.org/release/$OIL_VERSION/doc/"

  echo "Visit https://www.oilshell.org/release/$OIL_VERSION/doc/"
}

publish-release() {
  local user=$1
  local host=$2

  rsync --archive --verbose \
    _release/oil-$OIL_VERSION.tar.* \
    "$user@$host:oilshell.org/download/"

  echo "Visit https://www.oilshell.org/download/"
}

"$@"
