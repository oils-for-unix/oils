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
  gzip -c $in > $out
  ls -l $out
}

oil() {
  _compressed-tarball oil $(head -n 1 oil-version.txt)
}

hello() {
  _compressed-tarball hello $(head -n 1 build/testdata/hello-version.txt)
}

"$@"
