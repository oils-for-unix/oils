#!/usr/bin/env bash
#
# Build a wedge.
#
# Usage:
#   deps/wedge.sh <function name>
#
# Examples:
#
#   $0 unboxed-build   deps/source.medo/re2c.wedge.sh
#   $0 unboxed-install deps/source.medo/re2c.wedge.sh
#
#   # Containerized build
#   $0 build deps/source.medo/re2c.wedge.sh _tmp/wedge-out
#
# Input:
#
#   deps/
#     source.medo/
#       MEDO           # points to silo
#       re2c.wedge.sh  # later it will be re2c.wedge.hay
#       re2c-3.0.blob  # .tar.gz file that you can 'medo sync'
#       re2c-3.1.blob

# TODO:
# - Right now they assume shared Dockerfile.wedge-build ?  I think that's
#   easiest.

# TODO:
# 1. Build and install re2c outside the container, for Ubuntu 18
#
# 2. Then run the same script inside a Debian container
#    Copy the directory out
#
# 3. Store the tarball somewhere -- deps/derived.medo/debian/bullseye/re2c/$VERSION
#
# 4. Mount that result inside a container, and use it to build Oil, test Oil, etc.


# Every C package has 4 dirs:
#
# 1. Where the tarball is stored
# 2. Where it's extracted
# 3. The directory you run ./configure --prefix; make; make install from
# 4. The directory you install to 

# For Debian/Ubuntu

# Note: xz-utils needed to extract, but medo should make that transparent?
#
# Container dir structure
#
# /home/uke/
#   tmp-mount/ 
#     _cache/            # Mounted from oil/_cache
#       re2c-3.0.tar.xz
#       re2c-3.0/        # Extract it here
#       
#     _build/            # Build into this temp dir
#       wedge/
#         re2c
# /wedge/                # Output is mounted to oil/_mount/wedge-out
#   oilshell.org/
#     pkg/
#       re2c/
#         3.0/
#     debug-info/        # Probably needs to be at an absolute path because of
#                        # --debug-link
#       re2c/
#         3.0/

# Oil temp dir structure
#
# ~/git/oilshell/oil
#   _build/
#     obj/       # for C++ / Ninja
#     wedge/     # for containerized builds
#       source/          # sync'd from deps/source.medo
#       unboxed-tmp/     # build directory
#       binary/          # output of containerized build
#                        # can be mounted
#                   
# Then Dockerfile.wild does:
#
#  COPY _build/wedge/binary/oils-for-unix.org/pkg/re2c/3.0 \
#    /wedge/oils-for-unix.org/pkg/re2c/3.0

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

OILS_WEDGE_ROOT='/wedge/oils-for-unix.org'

die() {
  echo "$0: $@" >& 2
  exit 1
}

#
# Dirs
#

source-dir() {
  if test -n "${WEDGE_TARBALL_NAME:-}"; then

    # for Python-3.10.4 to override 'python3' package name
    echo "$REPO_ROOT/_cache/$WEDGE_TARBALL_NAME-$WEDGE_VERSION"

  else
    echo "$REPO_ROOT/_cache/$WEDGE_NAME-$WEDGE_VERSION"
  fi
}

build-dir() {
  echo "$REPO_ROOT/_build/wedge/tmp/$WEDGE_NAME"
}

install-dir() {
  # pkg/ leaves room for parallel debug-info/
  echo "$OILS_WEDGE_ROOT/pkg/$WEDGE_NAME/$WEDGE_VERSION"
}

load-wedge() {
  ### source .wedge.sh file and ensure it conforms to protocol

  local wedge=$1

  echo "Loading $wedge"
  echo

  source $wedge

  echo "  OK  name: ${WEDGE_NAME?"$wedge: WEDGE_NAME required"}"
  echo "  OK  version: ${WEDGE_VERSION?"$wedge: WEDGE_VERSION required"}"
  if test -n "${WEDGE_TARBALL_NAME:-}"; then
    echo "  --  tarball name: $WEDGE_TARBALL_NAME"
  fi

  for func in wedge-build wedge-install wedge-smoke-test; do
    if declare -f $func > /dev/null; then
      echo "  OK  $func"
    else
      die "$wedge: $func not declared"
    fi
  done
  echo

  echo "Loaded $wedge"
  echo
}

_run-sourced-func() {
  "$@"
}

#
# Actions
#

validate() {
  local wedge=$1

  load-wedge $wedge
}

unboxed-build() {
  ### Build on the host

  local wedge=$1  # e.g. re2c.wedge.sh

  load-wedge $wedge

  local build_dir=$(build-dir) 

  rm -r -f -v $build_dir
  mkdir -p $build_dir

  echo SOURCE $(source-dir)

  wedge-build $(source-dir) $build_dir $(install-dir)
}


# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html

# Do not strip executables when installing them. This helps eventual
# debugging that may be needed later, and nowadays disk space is cheap and
# dynamic loaders typically ensure debug sections are not loaded during
# normal execution. Users that need stripped binaries may invoke the
# install-strip target to do that. 

_unboxed-install() {
  local wedge=$1  # e.g. re2.wedge.sh

  load-wedge $wedge

  # Note: install-dir needed for time-helper, but not others
  wedge-install $(build-dir) $(install-dir)
}

unboxed-install() {
  local wedge=$1  # e.g. re2.wedge.sh

  sudo $0 _unboxed-install "$@"

  load-wedge $wedge

  echo '  SMOKE TEST'
  wedge-smoke-test $(install-dir)
  echo '  OK'
}

unboxed-smoke-test() {
  local wedge=$1  # e.g. re2.wedge.sh

  load-wedge $wedge
  wedge-smoke-test $(install-dir)
}

unboxed-stats() {
  local wedge=$1

  load-wedge $wedge

  du --si -s $(source-dir)
  echo

  du --si -s $(build-dir)
  echo

  du --si -s $(install-dir)
  echo
}

_build-inside() {
  local wedge=$1

  # TODO:
  # - Would be nice to export the logs somewhere

  unboxed-build $wedge

  unboxed-install $wedge
}

build() {
  ### Build inside a container, and put output in a specific place.

  # TODO: Specify the container OS, CPU like x86-64, etc.

  local wedge=$1
  local wedge_out_dir=${2:-_build/wedge/binary}

  mkdir -p $wedge_out_dir

  # Can use podman too
  local docker=${3:-docker}

  load-wedge $wedge

  # TODO: 
  #
  # Mount
  #  INPUTS: the PKG.wedge.sh, and the tarball
  #  CODE: this script: deps/wedge.sh
  #  OUTPUT: /wedge/oils-for-unix.org
  #    TODO: Also put logs and symbols somewhere

  local repo_root=$REPO_ROOT

  # Run unboxed-build,unboxed-install INSIDE the container
  local -a args=(
      sh -c 'cd ~/oil; deps/wedge.sh _build-inside $1' dummy "$wedge"
  )

  local image=oilshell/soil-wedge-builder
  local tag=v-2023-02-28f

  # TODO:
  # - It would be nice to make the repo root mount read-only
  # - Should we not mount the whole repo root?
  # - We only want to make the bare minimum of files visible, for cache invalidation

  # - Disable network for hermetic builds.  TODO: Add automated test
  sudo $docker run \
    --network none \
      --mount "type=bind,source=$repo_root,target=/home/uke/oil" \
      --mount "type=bind,source=$PWD/$wedge_out_dir,target=/wedge" \
      $image:$tag \
      "${args[@]}"
}

if [[ $# -eq 0 || $1 =~ ^(--help|-h)$ ]]; then
  # A trick for help.  TODO: Move this to a common file, and combine with help
  # in test/spec.sh.

  awk '
  $0 ~ /^#/ { print $0 }
  $0 !~ /^#/ { print ""; exit }
  ' $0
  exit
fi

case $1 in
  validate|unboxed-build|unboxed-install|_unboxed-install|unboxed-smoke-test|unboxed-stats|build|_build-inside)
    "$@"
    ;;

  *)
    die "$0: Invalid action '$1'"
    ;;
esac
