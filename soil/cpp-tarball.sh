#!/usr/bin/env bash
#
# Build the tarball
#
# Usage:
#   soil/cpp-tarball.sh


# Notes:
#   soil-benchmarks/    # uses ninja in $REPO_ROOT
#   soil-benchmarks2/   # uses build-like-ninja, which copies
#                       #  _tmp/native-tar-test/ to $REPO_ROOT
#     uftrace
#     gc-cachegrind
#   soil-benchmarks3/   # TODO: use same scheme as benchmarks2
#     osh-parser
#     osh-runtime

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh  # python2 for gen-shell-build

#REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
#source soil/common.sh

OILS_VERSION=$(head -n 1 oils-version.txt)
OILS_TRANSLATOR=${OILS_TRANSLATOR:-mycpp}

build-like-ninja() {
  ### Build a list of variants with either Ninja or the tarball
  # The tarball build copies from _bin/cxx-$variant-sh/ -> _bin/cxx-$variant,
  # to be consistent
  # And it passes --skip-rebuild

  local tar=_release/oils-for-unix.tar

  if test -f build.ninja; then
    # Just use Ninja

    local -a targets=()

    for variant in "$@"; do
      # TODO: clean this code up!
      case "$OILS_TRANSLATOR" in
        mycpp)
          targets+=( _bin/cxx-$variant/{osh,ysh} )
          ;;
        *)
          # mycpp-souffle, mycpp-nosouffle
          targets+=( _bin/cxx-$variant/$OILS_TRANSLATOR/{osh,ysh} )
          ;;
      esac
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

    # Hack: copy to Ninja location.  So the interface is the same.
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

benchmark-build() {
  ### Binaries tested by osh-runtime, osh-parser, ...

  #devtools/release-native.sh gen-shell-build  # _build/oils.sh

  # generate C++ and _build/oils.sh
  devtools/release-native.sh make-tar

  # Now build 3 binaries - with that same code
  # TODO: It would be nice to do this faster. The tarball should check
  # timestamps

  _build/oils.sh --skip-rebuild
  _build/oils.sh --translator mycpp-nosouffle --skip-rebuild
  build/static-oils.sh
}

"$@"
