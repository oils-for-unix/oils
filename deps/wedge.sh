#!/usr/bin/env bash
#
# Build a wedge.
#
# Usage:
#   deps/wedge.sh <function name>
#
# Examples:
#
#   $0 raw-build   deps/source.medo/re2c.wedge.sh
#   $0 raw-install deps/source.medo/re2c.wedge.sh  # Do it as root
#
# Input:
#
#   deps/
#     source.medo/
#       MEDO           # points to silo
#       re2c.wedge.sh  # later it will be re2c.wedge.hay
#       re2c-3.0.blob  # .tar.gz file that you can 'medo sync'
#       re2c-3.1.blob
#
# Containerized build:
#
#   $0 create debian/bullseye deps/source.medo/re2c.wedge.sh _tmp/wedge/  # Output directory

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

# TODO: Install BUILD_PACKAGES in the build container
#
#   Dockerfile.wedge-builder

readonly -a BUILD_PACKAGES=( build-essential make )

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

OILS_WEDGE_ROOT='/wedge/oils-for-unix.org'

die() {
  echo "$@" >& 2
  exit 1
}

#
# Dirs
#

source-dir() {
  echo "$REPO_ROOT/_cache/$WEDGE_NAME-$WEDGE_VERSION"
}

build-dir() {
  echo "$REPO_ROOT/_build/wedge/$WEDGE_NAME"
}

install-dir() {
  # pkg/ leaves room for parallel debug-info/
  echo "$OILS_WEDGE_ROOT/pkg/$WEDGE_NAME/$WEDGE_VERSION"
}

load-wedge() {
  ### source .wedge.sh file an ensure it conforms to protocol

  local wedge=$1

  echo "Loading $wedge"
  source $wedge

  echo "  OK  name: ${WEDGE_NAME?"$wedge: WEDGE_NAME required"}"
  echo "  OK  version: ${WEDGE_VERSION?"$wedge: WEDGE_VERSION required"}"

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

raw-build() {
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

_raw-install() {
  local wedge=$1  # e.g. re2.wedge.sh

  load-wedge $wedge

  wedge-install $(build-dir)
}

raw-install() {
  local wedge=$1  # e.g. re2.wedge.sh

  sudo $0 _raw-install "$@"

  load-wedge $wedge

  echo '  SMOKE TEST'
  wedge-smoke-test $(install-dir)
  echo '  OK'
}

raw-stats() {
  local wedge=$1

  load-wedge $wedge

  du --si -s $(source-dir)
  echo

  du --si -s $(build-dir)
  echo

  du --si -s $(install-dir)
  echo
}

create() {
  # TODO: launch Docker container

  echo
}

case $1 in
  raw-build|raw-install|raw-stats|create|_raw-install)
    "$@"
    ;;

  *)
    die "$0: Invalid action '$1'"
    ;;
esac
