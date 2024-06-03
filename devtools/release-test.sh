#!/usr/bin/env bash
# 
# Test release tarballs
#
# Usage:
#   devtools/release-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

fetch() {
  local dir=$1
  local tar_url=$2

  wget --directory $dir --no-clobber $tar_url

  pushd $dir
  tar -x -v < $(basename $tar_url)
  popd
}

fetch-2() {
  fetch _tmp/release-test/github \
    'http://travis-ci.oilshell.org/github-jobs/7098/cpp-tarball.wwz/_release/oils-for-unix.tar'

  fetch _tmp/release-test/sourcehut \
    'http://travis-ci.oilshell.org/srht-jobs/1236802/cpp-tarball.wwz/_release/oils-for-unix.tar'
}

diff-2() {
  diff -u -r _tmp/release-test/{github,sourcehut}
}

"$@"
