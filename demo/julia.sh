#!/usr/bin/env bash
#
# Usage:
#   demo/julia.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

download() {
  # 139 MB
  wget --directory _tmp --no-clobber \
    'https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.3-linux-x86_64.tar.gz'
}

# TODO: should make a wedge that's lazy
extract() {
  pushd _tmp
  tar -x -z < julia-*.tar.gz
  popd
}

julia() {
  _tmp/julia-*/bin/julia "$@"
}

"$@"
