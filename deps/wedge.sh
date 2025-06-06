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
#   $0 unboxed            deps/source.medo/re2c/
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
#     derived.medo/    # Saved output of 'wedge build'
#
#   _build/            # Temp dirs and output
#     obj/             # for C++ / Ninja
#     deps-source/     # sync'd from deps/source.medo - should it be
#                      # _build/wedge/source?
#     wedge/           # for containerized builds
#       tmp/           # build directory
#       boxed/         # output of containerized build
#                      # TODO: rename from /binary/
#       logs/
#       smoke-test/    # current dir for smoke test

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

log() {
  echo "$@" >&2
}

die() {
  log "$0: fatal: $@"
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
  echo "$REPO_ROOT/_build/wedge/tmp/$WEDGE_NAME-$WEDGE_VERSION"
}

install-dir() {
  local prefix
  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    prefix=$OILS_ABSOLUTE_ROOT
  else
    prefix=$OILS_RELATIVE_ROOT
  fi

  # TODO: We want to support multiple versions of the same wedge
  # So maybe we can provide
  # 
  # WEDGE_VERSION_LIST='4.4 5.2'
  #
  # And then provide a flag to select them?

  echo "$prefix/pkg/$WEDGE_NAME/$WEDGE_VERSION"
}

smoke-test-dir() {
  echo "$REPO_ROOT/_build/wedge/smoke-test/$WEDGE_NAME-$WEDGE_VERSION"
}

load-wedge() {
  ### source .wedge.sh file and ensure it conforms to protocol

  local wedge_dir=$1
  local version_requested=${2:-}

  echo "Loading $wedge_dir"
  echo

  source $wedge_dir/WEDGE

  echo "  OK  name: ${WEDGE_NAME?"$wedge_dir: WEDGE_NAME required"}"

  # This WEDGE supports a single version.
  if test -n "${WEDGE_VERSION:-}"; then
    echo "  --  single version: $WEDGE_VERSION"
  fi

  # Can validate version against this
  if test -n "${WEDGE_VERSION_LIST:-}"; then
    echo "  --  version list: $WEDGE_VERSION_LIST"

    if test -z "$version_requested"; then
      die "FAIL  Expected explicit version, one of: $WEDGE_VERSION_LIST"
    fi

    case "$WEDGE_VERSION_LIST" in
      *"$version_requested"*)
        echo "  OK  Setting WEDGE_VERSION to $version_requested"
        WEDGE_VERSION=$version_requested
        ;;
      *)
        die "FAIL  Requested version $version_requested should be one of: $WEDGE_VERSION_LIST"
        ;;
    esac
  fi

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

  if declare -f wedge-make; then
    echo "  OK  wedge-make"
  elif declare -f wedge-make-from-source-dir; then
    echo "  OK  wedge-make-from-source-dir"
  else
    die "$wedge_dir: wedge-make(-from-source-dir) not declared"
  fi

  if declare -f wedge-install; then
    echo "  OK  wedge-install"
  elif declare -f wedge-make-from-source-dir; then
    echo "  OK  wedge-install-from-source-dir"
  else
    die "$wedge_dir: wedge-install(-from-source-dir) not declared"
  fi

  # Just one function for now
  for func in wedge-smoke-test; do
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
  local version_requested=${2:-}

  load-wedge $wedge "$version_requested"
}

abs-wedge-dir() {
  local wedge_dir=$1
  case $wedge_dir in
    /*)  # it's already absolute
      echo $wedge_dir
      ;;
    *)
      echo $PWD/$wedge_dir
      ;;
  esac
}

unboxed-make() {
  ### Build on the host

  local wedge_dir=$1  # e.g. re2c.wedge.sh
  local version_requested=${2:-}  # e.g. 5.2

  load-wedge $wedge_dir "$version_requested"

  local source_dir
  source_dir=$(source-dir) 
  echo " SRC $source_dir"

  local build_dir
  build_dir=$(build-dir) 

  # NOT created because it might require root permissions!
  local install_dir
  install_dir=$(install-dir)

  local abs_wedge_dir
  abs_wedge_dir=$(abs-wedge-dir $wedge_dir)

  rm -r -f -v $build_dir
  mkdir -p $build_dir

  if declare -f wedge-make-from-source-dir; then
    # e.g. for yash, which can't build outside the source tree
    pushd $source_dir
    wedge-make-from-source-dir $source_dir $install_dir $abs_wedge_dir
    popd
  else
    pushd $build_dir
    wedge-make $source_dir $build_dir $install_dir $abs_wedge_dir
    popd
  fi
}


# https://www.gnu.org/prep/standards/html_node/Standard-Targets.html

# Do not strip executables when installing them. This helps eventual
# debugging that may be needed later, and nowadays disk space is cheap and
# dynamic loaders typically ensure debug sections are not loaded during
# normal execution. Users that need stripped binaries may invoke the
# install-strip target to do that. 

_unboxed-install() {
  local wedge=$1  # e.g. re2c.wedge.sh
  local version_requested=${2:-}  # e.g. 5.2

  load-wedge $wedge "$version_requested"

  local source_dir
  source_dir=$(source-dir) 

  local build_dir
  build_dir=$(build-dir) 

  local install_dir
  install_dir=$(install-dir)
  mkdir -p $install_dir

  if declare -f wedge-make-from-source-dir; then
    pushd $source_dir
    wedge-install-from-source-dir $source_dir $install_dir
    popd
  else
    # Note: install-dir needed for time-helper, but not others
    #
    # I think it would nicer to pushd $build_dir in most cases

    wedge-install $build_dir $install_dir
  fi
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
  local version_requested=${2:-}  # e.g. 5.2

  load-wedge $wedge_dir "$version_requested"

  local smoke_test_dir
  smoke_test_dir=$(smoke-test-dir)
  local install_dir
  install_dir=$(install-dir)

  echo '  SMOKE TEST'

  local abs_wedge_dir
  abs_wedge_dir=$(abs-wedge-dir $wedge_dir)

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

  load-wedge $wedge "$version_requested"

  du --si -s $(source-dir)
  echo

  du --si -s $(build-dir)
  echo

  du --si -s $(install-dir)
  echo
}

unboxed() {
  local wedge_dir=$1

  # Can override default version.  Could be a flag since it's optional?  But
  # right now we always pass it.
  local version_requested=${2:-}

  # TODO:
  # - Would be nice to export the logs somewhere

  unboxed-make $wedge_dir "$version_requested"

  unboxed-install $wedge_dir "$version_requested"

  unboxed-smoke-test $wedge_dir "$version_requested"
}

readonly DEFAULT_DISTRO=debian-10  # Debian Buster

DOCKER=${DOCKER:-docker}

boxed() {
  ### Build inside a container, and put output in a specific place.

  # TODO: Specify the container OS, CPU like x86-64, etc.

  local wedge=$1
  local version_requested=${2:-}
  local distro=${3:-$DEFAULT_DISTRO}

  local bootstrap_image=oilshell/wedge-bootstrap-$distro

  load-wedge $wedge "$version_requested"

  # Permissions will be different, so we separate the two

  local wedge_host_dir
  local wedge_guest_dir
  if test -n "${WEDGE_IS_ABSOLUTE:-}"; then
    wedge_host_dir=_build/wedge/binary  # TODO: rename to /absolute/
    wedge_guest_dir=/wedge
  else
    wedge_host_dir=_build/wedge/relative
    wedge_guest_dir=/home/uke0/wedge
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
      sh -c 'cd ~/oil; deps/wedge.sh unboxed "$1" "$2"'
      dummy "$wedge" "$version_requested"
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
    --mount "type=bind,source=$REPO_ROOT,target=/home/uke0/oil" \
    --mount "type=bind,source=$PWD/$wedge_host_dir,target=$wedge_guest_dir" \
    $bootstrap_image \
    "${args[@]}"
}

smoke-test() {
  local wedge_dir=$1
  local wedge_out_dir=${2:-_build/wedge/binary}  # TODO: rename to /boxed
  local version_requested=${3:-}
  local distro=${4:-$DEFAULT_DISTRO}
  local debug_shell=${5:-}

  load-wedge $wedge_dir "$version_requested"

  local bootstrap_image=oilshell/wedge-bootstrap-$distro

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
    wedge_mount_dir=/home/uke0/wedge
  fi

  sudo $DOCKER run "${docker_flags[@]}" \
    --network none \
    --mount "type=bind,source=$REPO_ROOT,target=/home/uke0/oil" \
    --mount "type=bind,source=$PWD/$wedge_out_dir,target=$wedge_mount_dir" \
    $bootstrap_image \
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
  unboxed|\
  unboxed-make|unboxed-install|_unboxed-install|\
  unboxed-smoke-test|unboxed-stats|\
  boxed|smoke-test)
    "$@"
    ;;

  *)
    die "Invalid action '$1'"
    ;;
esac
