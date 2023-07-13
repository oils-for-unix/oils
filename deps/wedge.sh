#!/usr/bin/env bash
#
# Build a wedge.
#
# Usage:
#   deps/wedge.sh <function name>
#
# Containerized build:
#
#   $0 build deps/source.medo/re2c/
#
# Host build, without containers:
#
#   $0 unboxed-build      deps/source.medo/re2c/
#
# Individual steps:
#
#   $0 unboxed-make       deps/source.medo/re2c/
#   $0 unboxed-install    deps/source.medo/re2c/
#   $0 unboxed-smoke-test deps/source.medo/re2c/
#
# Host dir structure:
#
# ~/git/oilshell/oil
#   deps/
#     source.medo/     # Source Files
#       MEDO           # points to silo
#       re2c.wedge.sh  # later it will be re2c.wedge.hay
#       re2c-3.0.blob  # .tar.gz file that you can 'medo sync'
#       re2c-3.1.blob
#     opaque.medo/     # Binary files, e.g. Clang
#     derived.medo/    # Svaed output of 'wedge build'
#
#   _build/            # Temp dirs and output
#     obj/             # for C++ / Ninja
#     wedge/           # for containerized builds
#       source/        # sync'd from deps/source.medo
#       unboxed-tmp/   # build directory
#       boxed/         # output of containerized build
#                      # TODO: rename from /binary/

# Every package ("wedge") has these dirs associated with it:
#
# 1. Dir with additional tests / files, near tarball and *.wedge.sh ($wedge_dir)
# 2. Where it's extracted ($src_dir)
# 3. The temp dir where you run ./configure --prefix; make; make install ($build_dir)
# 4. The dir to install to ($install_dir)
# 5. The temp dir where the smoke test is run

# For Debian/Ubuntu

# Note: xz-utils needed to extract, but medo should make that transparent?
#
# Container dir structure
#
# /home/uke/
#   tmp-mount/ 
#     _build/            # Build into this temp dir
#       deps-source/
#         re2c/
#           re2c-3.0.tar.xz
#           re2c-3.0/        # Extract it here
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

OILS_ABSOLUTE_ROOT='/wedge/oils-for-unix.org'

# The user may build a wedge outside a container here
OILS_RELATIVE_ROOT="$HOME/wedge/oils-for-unix.org"

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
    echo "$REPO_ROOT/_build/deps-source/$WEDGE_NAME/$WEDGE_TARBALL_NAME-$WEDGE_VERSION"

  else
    echo "$REPO_ROOT/_build/deps-source/$WEDGE_NAME/$WEDGE_NAME-$WEDGE_VERSION"
  fi
}

build-dir() {
  # call it tmp-build?
  echo "$REPO_ROOT/_build/wedge/tmp/$WEDGE_NAME"
}

install-dir() {
  local prefix
  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    prefix=$OILS_ABSOLUTE_ROOT
  else
    prefix=$OILS_RELATIVE_ROOT
  fi
  echo "$prefix/pkg/$WEDGE_NAME/$WEDGE_VERSION"
}

smoke-test-dir() {
  echo "$REPO_ROOT/_build/wedge/smoke-test/$WEDGE_NAME"
}

load-wedge() {
  ### source .wedge.sh file and ensure it conforms to protocol

  local wedge_dir=$1

  echo "Loading $wedge_dir"
  echo

  source $wedge_dir/WEDGE

  echo "  OK  name: ${WEDGE_NAME?"$wedge_dir: WEDGE_NAME required"}"
  echo "  OK  version: ${WEDGE_VERSION?"$wedge_dir: WEDGE_VERSION required"}"
  if test -n "${WEDGE_TARBALL_NAME:-}"; then
    echo "  --  tarball name: $WEDGE_TARBALL_NAME"
  fi
  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    echo '  --  WEDGE_IS_ABSOLUTE'
  fi

  # Python and R installation use the network
  if test -n "${WEDGE_LEAKY_BUILD:-}"; then
    echo '  --  WEDGE_LEAKY_BUILD'
  fi

  for func in wedge-make wedge-install wedge-smoke-test; do
    if declare -f $func > /dev/null; then
      echo "  OK  $func"
    else
      die "$wedge_dir: $func not declared"
    fi
  done
  echo

  echo "Loaded $wedge_dir"
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

unboxed-make() {
  ### Build on the host

  local wedge=$1  # e.g. re2c.wedge.sh

  load-wedge $wedge

  local build_dir=$(build-dir) 

  # NOT created because it might require root permissions!
  local install_dir=$(install-dir)

  rm -r -f -v $build_dir
  mkdir -p $build_dir

  echo SOURCE $(source-dir)

  # TODO: pushd/popd error handling

  pushd $build_dir
  wedge-make $(source-dir) $build_dir $install_dir
  popd
}


# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html

# Do not strip executables when installing them. This helps eventual
# debugging that may be needed later, and nowadays disk space is cheap and
# dynamic loaders typically ensure debug sections are not loaded during
# normal execution. Users that need stripped binaries may invoke the
# install-strip target to do that. 

_unboxed-install() {
  local wedge=$1  # e.g. re2c.wedge.sh

  load-wedge $wedge

  local install_dir
  install_dir=$(install-dir)
  mkdir -p $install_dir

  # Note: install-dir needed for time-helper, but not others
  wedge-install $(build-dir) $install_dir
}

unboxed-install() {
  local wedge=$1  # e.g. re2.wedge.sh

  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    sudo $0 _unboxed-install "$@"
  else
    _unboxed-install "$@"
  fi
}

unboxed-smoke-test() {
  local wedge_dir=$1  # e.g. re2c/ with WEDGE

  load-wedge $wedge_dir

  local smoke_test_dir=$(smoke-test-dir)
  local install_dir=$(install-dir)

  echo '  SMOKE TEST'

  local abs_wedge_dir
  case $wedge_dir in
    /*)  # it's already absolute
      abs_wedge_dir=$wedge_dir
      ;;
    *)
      abs_wedge_dir=$PWD/$wedge_dir
      ;;
  esac

  # TODO: To ensure a clean dir, it might be better to test that it does NOT
  # exist first, and just make it.  If it exists, then remove everything.

  rm -r -f -v $smoke_test_dir
  mkdir -p $smoke_test_dir

  pushd $smoke_test_dir
  set -x
  wedge-smoke-test $install_dir $abs_wedge_dir
  set +x
  popd

  echo '  OK'
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

unboxed-build() {
  local wedge_dir=$1

  # TODO:
  # - Would be nice to export the logs somewhere

  unboxed-make $wedge_dir

  unboxed-install $wedge_dir

  unboxed-smoke-test $wedge_dir
}

readonly BUILD_IMAGE=oilshell/soil-wedge-builder
readonly BUILD_IMAGE_TAG=v-2023-03-01

DOCKER=${DOCKER:-docker}

build() {
  ### Build inside a container, and put output in a specific place.

  # TODO: Specify the container OS, CPU like x86-64, etc.

  local wedge=$1

  load-wedge $wedge

  # Permissions will be different, so we separate the two

  local wedge_host_dir
  local wedge_guest_dir
  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    wedge_host_dir=_build/wedge/binary  # TODO: rename to /absolute/
    wedge_guest_dir=/wedge
  else
    wedge_host_dir=_build/wedge/relative
    wedge_guest_dir=/home/wedge-builder/wedge
  fi

  mkdir -v -p $wedge_host_dir

  # TODO: 
  #
  # Mount
  #  INPUTS: the PKG.wedge.sh, and the tarball
  #  CODE: this script: deps/wedge.sh
  #  OUTPUT: /wedge/oils-for-unix.org
  #    TODO: Also put logs and symbols somewhere

  # Run unboxed-{build,install,smoke-test} INSIDE the container
  local -a args=(
      sh -c 'cd ~/oil; deps/wedge.sh unboxed-build $1' dummy "$wedge"
  )

  local -a docker_flags=()
  if test -n "${WEDGE_LEAKY_BUILD:-}"; then
    :
  else
    # Disable network for hermetic builds.  TODO: Add automated test
    docker_flags=( --network none )
  fi

  # TODO:
  # - Don't mount the whole REPO_ROOT
  #   - We want the bare minimum of files, for cache invalidation
  # - Maybe make it read only
  # - Bind mount WEDGE_DEPS='', space separated list of paths
  #   - py3-libs depends on python3 and mypy wedges!

  # -E to preserve CONTAINERS_REGISTRIES_CONF
  sudo -E $DOCKER run "${docker_flags[@]}" \
    --mount "type=bind,source=$REPO_ROOT,target=/home/wedge-builder/oil" \
    --mount "type=bind,source=$PWD/$wedge_host_dir,target=$wedge_guest_dir" \
    $BUILD_IMAGE:$BUILD_IMAGE_TAG \
    "${args[@]}"
}

smoke-test() {
  local wedge_dir=$1
  local wedge_out_dir=${2:-_build/wedge/binary}  # TODO: rename to /boxed
  local debug_shell=${3:-}

  load-wedge $wedge_dir

  local -a args=(
      sh -c 'cd ~/oil; deps/wedge.sh unboxed-smoke-test $1' dummy "$wedge_dir"
  )
  local -a docker_flags=()
  if test -n "$debug_shell"; then
    docker_flags=( -i -t )
    args=( "$debug_shell" )
  fi

  local wedge_mount_dir
  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    wedge_mount_dir=/wedge
  else
    wedge_mount_dir=/home/wedge-builder/wedge
  fi

  sudo $DOCKER run "${docker_flags[@]}" \
    --network none \
    --mount "type=bind,source=$REPO_ROOT,target=/home/wedge-builder/oil" \
    --mount "type=bind,source=$PWD/$wedge_out_dir,target=$wedge_mount_dir" \
    $BUILD_IMAGE:$BUILD_IMAGE_TAG \
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
  validate|\
  unboxed-build|\
  unboxed-make|unboxed-install|_unboxed-install|\
  unboxed-smoke-test|unboxed-stats|\
  build|smoke-test)
    "$@"
    ;;

  *)
    die "$0: Invalid action '$1'"
    ;;
esac
