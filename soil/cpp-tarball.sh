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

OILS_VERSION=$(head -n 1 oils-version.txt)
OILS_TRANSLATOR=${OILS_TRANSLATOR:-mycpp}

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

    if ! test -d oils-for-unix-$OILS_VERSION; then
      tar -x < ../../$tar
    fi

    # Leaving out version
    pushd oils-for-unix-$OILS_VERSION

    ./configure

    for variant in "$@"; do
      time _build/oils.sh \
        --variant "$variant" --translator "$OILS_TRANSLATOR" --skip-rebuild
    done

    popd
    popd

    # Hack: copy to NInja location.  So the interface is the same.
    for variant in "$@"; do
      local out_bin_dir
      local tar_bin_dir
      case $OILS_TRANSLATOR in
        mycpp)
          out_bin_dir=_bin/cxx-$variant
          tar_bin_dir=_bin/cxx-$variant-sh
          ;;
        *)
          out_bin_dir=_bin/cxx-$variant/$OILS_TRANSLATOR
          tar_bin_dir=_bin/cxx-$variant-sh/$OILS_TRANSLATOR
          ;;
      esac
      mkdir -v -p $out_bin_dir
      cp -v \
        $tmp/oils-for-unix-$OILS_VERSION/$tar_bin_dir/{oils-for-unix,osh,ysh} \
        $out_bin_dir
    done

  else
    echo "Expected either build.ninja or $tar"
    exit 1
  fi
}

"$@"
