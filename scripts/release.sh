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
