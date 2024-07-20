#!/usr/bin/env bash
#
# Build
#
# Usage:
#   soil/cpp-build.sh

set -o nounset
set -o pipefail
set -o errexit

#REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
#source soil/common.sh

OILS_VERSION=$(head -n 1 oil-version.txt)

build-like-ninja() {
  local tar=_release/oils-for-unix.tar

  if test -f build.ninja; then
    # Just use Ninja

    local -a targets=()
    for variant in "$@"; do
      targets+=( _bin/cxx-$variant/{oils-for-unix,osh,ysh} )
    done
    ninja "${targets[@]}"

  elif test -f $tar; then
    # Build out of the tarball, but put in WHERE NINJA would have put it

    local tmp=_tmp/native-tar-test  # like oil-tar-test

    # Don't defeat SKIP_REBUILD
    #rm -r -f $tmp

    mkdir -p $tmp
    pushd $tmp

    tar -x < ../../$tar

    # Leaving out version
    pushd oils-for-unix-$OILS_VERSION

    ./configure

    for variant in "$@"; do
      time _build/oils.sh '' $variant SKIP_REBUILD
    done

    popd
    popd

    # Hack: copy to NInja location.  So the interface is the same.
    for variant in "$@"; do
      mkdir -v -p _bin/cxx-$variant
      cp -v \
        $tmp/oils-for-unix-$OILS_VERSION/_bin/cxx-$variant-sh/{oils-for-unix,osh,ysh} \
        _bin/cxx-$variant
    done

  else
    echo "Expected either build.ninja or $tar"
    exit 1
  fi
}

"$@"
