#!/usr/bin/env bash
#
# Script for contributors to quickly set up core packages
#
# Usage:
#   build/deps.sh <function name>
#
# Examples:
#   build/deps.sh fetch
#   build/deps.sh install
#
# - re2c
# - cmark
# - python3
# - mypy and deps, so mycpp can import htem

# TODO:
# - remove cmark dependency for help.  It's still used for docs and benchmarks.
# - remove re2c from dev build?  Are there any bugs?  I think it's just slow.
# - add spec-bin so people can always run the tests
#
# - change Contributing page
#   - build/deps.sh fetch-py
#   - build/deps.sh install-wedges-py
#
# mycpp/README.md:
#
#   - build/deps.sh fetch
#   - build/deps.sh install-wedges
#
# Can we make most of them non-root deps?

set -o nounset
set -o pipefail
set -o errexit

source deps/from-apt.sh   # PY3_BUILD_DEPS

# Also in build/dev-shell.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org

readonly DEPS_SOURCE_DIR=_build/deps-source

readonly RE2C_VERSION=3.0
readonly RE2C_URL="https://github.com/skvadrik/re2c/releases/download/$RE2C_VERSION/re2c-$RE2C_VERSION.tar.xz"

readonly CMARK_VERSION=0.29.0
readonly CMARK_URL="https://github.com/commonmark/cmark/archive/$CMARK_VERSION.tar.gz"

readonly PY3_VERSION=3.10.4
readonly PY3_URL="https://www.python.org/ftp/python/3.10.4/Python-$PY3_VERSION.tar.xz"

readonly MYPY_GIT_URL=https://github.com/python/mypy
readonly MYPY_VERSION=0.780

readonly PY3_LIBS_VERSION=2023-03-04

readonly PY3_LIBS=~/wedge/oils-for-unix.org/pkg/py3-libs/$MYPY_VERSION


log() {
  echo "$0: $@" >& 2
}

die() {
  log "$@"
  exit 1
}

install-ubuntu-packages() {
  ### Packages for build/py.sh all and more

  # python-dev: for all the extension modules
  # libreadline-dev: needed for the build/prepare.sh Python build.
  # gawk: used by spec-runner.sh for the special match() function.
  # cmake: for build/py.sh yajl-release (TODO: remove eventually)
  if apt-cache show python2-dev > /dev/null 2>&1; then
    local python2_package=python2-dev 
  else
    local python2_package=python-dev 
  fi

  set -x  # show what needs sudo

  # pass -y for say gitpod
  sudo apt "$@" install \
    $python2_package gawk libreadline-dev ninja-build cmake \
    "${PY3_BUILD_DEPS}"
  set +x

  test/spec.sh install-shells-with-apt
}

download-to() {
  local dir=$1
  local url=$2
  wget --no-clobber --directory "$dir" "$url"
}

maybe-extract() {
  local wedge_dir=$1
  local tar_name=$2
  local out_dir=$3

  if test -d "$wedge_dir/$out_dir"; then
    log "Not extracting because $wedge_dir/$out_dir exists"
    return
  fi

  local tar=$wedge_dir/$tar_name
  case $tar_name in
    *.gz)
      flag='--gzip'
      ;;
    *.bz2)
      flag='--bzip2'
      ;;
    *.xz)
      flag='--xz'
      ;;
    *)
      die "tar with unknown extension: $tar_name"
      ;;
  esac

  tar --extract $flag --file $tar --directory $wedge_dir
}

clone-mypy() {
  ### replaces deps/from-git
  local dest_dir=$1

  local dest=$dest_dir/mypy-$MYPY_VERSION
  if test -d $dest; then
    log "Not cloning because $dest exists"
    return
  fi

  # TODO: verify commit checksum
  git clone --recursive --depth=50 --branch=release-$MYPY_VERSION \
    $MYPY_GIT_URL $dest
}

fetch() {
  local py_only=${1:-}

  # For now, simulate what 'medo expand deps/source.medo _build/deps-source'
  # would do: fetch compressed tarballs designated by .treeptr files, and
  # expand them.

  # _build/deps-source/
  #   re2c/
  #     WEDGE
  #     re2c-3.0/  # expanded .tar.xz file

  mkdir -p $DEPS_SOURCE_DIR

  # Copy the whole tree, including the .treeptr files
  cp --verbose --recursive --no-target-directory \
    deps/source.medo/ $DEPS_SOURCE_DIR/

  download-to $DEPS_SOURCE_DIR/re2c "$RE2C_URL"
  download-to $DEPS_SOURCE_DIR/cmark "$CMARK_URL"

  if test -n "$py_only"; then
    log "Fetched dependencies for 'build/py.sh'"
    return
  fi

  download-to $DEPS_SOURCE_DIR/python3 "$PY3_URL"

  maybe-extract $DEPS_SOURCE_DIR/re2c "$(basename $RE2C_URL)" re2c-$RE2C_VERSION
  maybe-extract $DEPS_SOURCE_DIR/cmark "$(basename $CMARK_URL)" cmark-$CMARK_VERSION
  maybe-extract $DEPS_SOURCE_DIR/python3 "$(basename $PY3_URL)" Python-$PY3_VERSION

  # This is in $DEPS_SOURCE_DIR to COPY into containers, which mycpp will directly import.
  # It's also copied into a wedge in install-wedges.
  clone-mypy $DEPS_SOURCE_DIR/mypy

  if command -v tree > /dev/null; then
    tree -L 2 $DEPS_SOURCE_DIR
    tree -L 2 $USER_WEDGE_DIR
  fi
}

fetch-py() {
  fetch py_only
}

wedge-exists() {
  local installed=/wedge/oils-for-unix.org/pkg/$1/$2
  if test -d $installed; then
    log "$installed already exists"
    return 0
  else
    return 1
  fi
}

# TODO: py3-libs needs to be a WEDGE, so that that you can run
# 'wedge build deps/source.medo/py3-libs/' and then get it in
#
# _build/wedge/{absolute,relative}   # which one?
#
# It needs a BUILD DEPENDENCY on the python3 wedge, so you can do python3 -m
# pip install.


install-py3-libs-in-venv() {
  local venv_dir=$1
  local mypy_dir=$2  # This is a param for host build vs. container build

  source $venv_dir/bin/activate  # enter virtualenv

  # Needed for spec/stateful/*.py
  python3 -m pip install pexpect

  # for mycpp/
  time python3 -m pip install -r $mypy_dir/test-requirements.txt
}

install-py3-libs() {
  local mypy_dir=${1:-$DEPS_SOURCE_DIR/mypy/mypy-$MYPY_VERSION}

  # Load it as the default python3
  source build/dev-shell.sh

  local py3
  py3=$(command -v python3)
  case $py3 in
    *wedge/oils-for-unix.org/*)
      ;;
    *)
      die "python3 is '$py3', but expected it to be in a wedge"
      ;;
  esac

  log "Ensuring pip is installed (interpreter $(command -v python3)"
  python3 -m ensurepip

  local venv_dir=$USER_WEDGE_DIR/pkg/py3-libs/$PY3_LIBS_VERSION
  log "Creating venv in $venv_dir"

  # Note: the bin/python3 in this venv is a symlink to python3 in $PATH, i.e.
  # the /wedge we just built
  python3 -m venv $venv_dir

  log "Installing MyPy deps in venv"

  # Run in a subshell because it mutates shell state
  $0 install-py3-libs-in-venv $venv_dir $mypy_dir
}

install-wedges() {
  local py_only=${1:-}

  # TODO:
  # - Make all of these RELATIVE wedges
  # - Add
  #   - unboxed-rel-smoke-test -- move it inside container
  #   - rel-smoke-test -- mount it in a different location
  # - Should have a CI task that does all of this!

  if ! wedge-exists cmark 0.29.0; then
    deps/wedge.sh unboxed-build _build/deps-source/cmark/
  fi

  if ! wedge-exists re2c 3.0; then
    deps/wedge.sh unboxed-build _build/deps-source/re2c/
  fi

  if test -n "$py_only"; then
    log "Installed dependencies for 'build/py.sh'"
    return
  fi

  # TODO: make the Python build faster by using all your cores?
  if ! wedge-exists python3 3.10.4; then
    deps/wedge.sh unboxed-build _build/deps-source/python3/
  fi

  # Copy all the contents, except for .git folder.
  if ! wedge-exists mypy $MYPY_VERSION; then

    # NOTE: We have to also copy the .git dir, because it has
    # .git/modules/typeshed

    local dest_dir=$USER_WEDGE_DIR/pkg/mypy/$MYPY_VERSION
    mkdir -p $dest_dir

    cp --verbose --recursive --no-target-directory \
      $DEPS_SOURCE_DIR/mypy/mypy-$MYPY_VERSION $dest_dir
  fi

  install-py3-libs
}

install-wedges-py() {
  install-wedges py_only
}

container-wedges() {
  deps/wedge.sh build deps/source.medo/time-helper
  return
  deps/wedge.sh build deps/source.medo/cmark/
  deps/wedge.sh build deps/source.medo/re2c/
  deps/wedge.sh build deps/source.medo/bloaty/
  deps/wedge.sh build deps/source.medo/uftrace/
  deps/wedge.sh build deps/source.medo/python3/
  deps/wedge.sh build deps/source.medo/R-libs/
}

"$@"
