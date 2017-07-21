#!/bin/bash
#
# Usage:
#   ./release.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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

readonly OIL_VERSION=$(head -n 1 oil-version.txt)

oil() {
  _compressed-tarball oil $OIL_VERSION
}

hello() {
  _compressed-tarball hello $(head -n 1 build/testdata/hello-version.txt)
}

publish-doc() {
  local user=$1
  local host=$2

  # TODO: Change this to make
  rm -rf _tmp/doc
  doc/run.sh osh-quick-ref
  doc/run.sh install
  doc/run.sh index
  rsync --archive --verbose \
    _tmp/doc/ "$user@$host:oilshell.org/doc/$OIL_VERSION/"

  echo "Visit https://www.oilshell.org/doc/$OIL_VERSION/"
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
