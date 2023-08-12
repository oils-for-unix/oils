#!/usr/bin/env bash
#
# Script for contributors to quickly set up core packages
#
# Usage:
#   build/deps.sh <function name>
#
# Examples:
#   build/deps.sh fetch
#   build/deps.sh install-wedges
#   build/deps.sh rm-oils-crap  # rm /wedge ~/wedge to start over
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

source build/dev-shell.sh  # python3 in PATH, PY3_LIBS_VERSION
source deps/from-apt.sh      # PY3_BUILD_DEPS
#source deps/podman.sh
source devtools/run-task.sh  # run-task

# Also in build/dev-shell.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org

readonly DEPS_SOURCE_DIR=_build/deps-source

readonly RE2C_VERSION=3.0
readonly RE2C_URL="https://github.com/skvadrik/re2c/releases/download/$RE2C_VERSION/re2c-$RE2C_VERSION.tar.xz"

readonly CMARK_VERSION=0.29.0
readonly CMARK_URL="https://github.com/commonmark/cmark/archive/$CMARK_VERSION.tar.gz"

readonly PY2_VERSION=2.7.18
readonly PY2_URL="https://www.python.org/ftp/python/2.7.18/Python-$PY2_VERSION.tar.xz"

readonly PY3_VERSION=3.10.4
readonly PY3_URL="https://www.python.org/ftp/python/3.10.4/Python-$PY3_VERSION.tar.xz"

readonly MYPY_GIT_URL=https://github.com/python/mypy
readonly MYPY_VERSION=0.780

readonly PY3_LIBS=~/wedge/oils-for-unix.org/pkg/py3-libs/$MYPY_VERSION

# Version 2.4.0 from 2021-10-06 was the last version that supported Python 2
# https://github.com/PyCQA/pyflakes/blob/main/NEWS.rst
readonly PYFLAKES_VERSION=2.4.0
#readonly PYFLAKES_URL='https://files.pythonhosted.org/packages/15/60/c577e54518086e98470e9088278247f4af1d39cb43bcbd731e2c307acd6a/pyflakes-2.4.0.tar.gz'
# 2023-07: Mirrored to avoid network problem on broome during release
readonly PYFLAKES_URL='https://www.oilshell.org/blob/pyflakes-2.4.0.tar.gz'

readonly BLOATY_VERSION=1.1
readonly BLOATY_URL='https://github.com/google/bloaty/releases/download/v1.1/bloaty-1.1.tar.bz2'

readonly UFTRACE_VERSION=0.13
readonly UFTRACE_URL='https://github.com/namhyung/uftrace/archive/refs/tags/v0.13.tar.gz'

log() {
  echo "$0: $@" >& 2
}

die() {
  log "$@"
  exit 1
}

rm-oils-crap() {
  ### When you want to start over

  rm -r -f -v ~/wedge
  sudo rm -r -f -v /wedge
}


install-ubuntu-packages() {
  ### Packages for build/py.sh all, building wedges, etc.

  # python2-dev is no longer available on Debian 12
  # python-dev also seems gone
  #
  # g++: essential
  # libreadline-dev: needed for the build/prepare.sh Python build.
  # gawk: used by spec-runner.sh for the special match() function.
  # cmake: for build/py.sh yajl-release (TODO: remove eventually)

  set -x  # show what needs sudo

  # pass -y for say gitpod
  sudo apt "$@" install \
    g++ gawk libreadline-dev ninja-build cmake \
    "${PY3_BUILD_DEPS[@]}"
  set +x

  test/spec-bin.sh install-shells-with-apt
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
  local version=${2:-$MYPY_VERSION}

  local dest=$dest_dir/mypy-$version
  if test -d $dest; then
    log "Not cloning because $dest exists"
    return
  fi

  # TODO: verify commit checksum

  # v$VERSION is a tag, not a branch
  git clone --recursive --depth=50 --branch v$version \
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
  maybe-extract $DEPS_SOURCE_DIR/re2c "$(basename $RE2C_URL)" re2c-$RE2C_VERSION
  maybe-extract $DEPS_SOURCE_DIR/cmark "$(basename $CMARK_URL)" cmark-$CMARK_VERSION

  if test -n "$py_only"; then
    log "Fetched dependencies for 'build/py.sh'"
    return
  fi
 
  download-to $DEPS_SOURCE_DIR/pyflakes "$PYFLAKES_URL"
  maybe-extract $DEPS_SOURCE_DIR/pyflakes "$(basename $PYFLAKES_URL)" \
    pyflakes-$PYFLAKES_VERSION

  download-to $DEPS_SOURCE_DIR/python2 "$PY2_URL"
  download-to $DEPS_SOURCE_DIR/python3 "$PY3_URL"
  maybe-extract $DEPS_SOURCE_DIR/python2 "$(basename $PY2_URL)" Python-$PY2_VERSION
  maybe-extract $DEPS_SOURCE_DIR/python3 "$(basename $PY3_URL)" Python-$PY3_VERSION

  # bloaty and uftrace are for benchmarks, in containers
  download-to $DEPS_SOURCE_DIR/bloaty "$BLOATY_URL"
  download-to $DEPS_SOURCE_DIR/uftrace "$UFTRACE_URL"
  maybe-extract $DEPS_SOURCE_DIR/bloaty "$(basename $BLOATY_URL)" uftrace-$BLOATY_VERSION
  maybe-extract $DEPS_SOURCE_DIR/uftrace "$(basename $UFTRACE_URL)" bloaty-$UFTRACE_VERSION

  # This is in $DEPS_SOURCE_DIR to COPY into containers, which mycpp will directly import.
  # It's also copied into a wedge in install-wedges.
  clone-mypy $DEPS_SOURCE_DIR/mypy

  if command -v tree > /dev/null; then
    tree -L 2 $DEPS_SOURCE_DIR
    tree -L 2 $USER_WEDGE_DIR
  fi
}

mirror-pyflakes() {
  ### Workaround for network error during release
  scp \
    $DEPS_SOURCE_DIR/pyflakes/"$(basename $PYFLAKES_URL)" \
    oilshell.org:oilshell.org/blob/
}

fetch-py() {
  fetch py_only
}

mypy-new() {
  local version=0.971
  # Do the latest version for Python 2
  clone-mypy $DEPS_SOURCE_DIR/mypy $version

  local dest_dir=$USER_WEDGE_DIR/pkg/mypy/$version
  mkdir -p $dest_dir

  cp --verbose --recursive --no-target-directory \
    $DEPS_SOURCE_DIR/mypy/mypy-$version $dest_dir
}

wedge-exists() {
  # TODO: Doesn't take into account ~/wedge/ vs. /wedge
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
# It needs a BUILD DEPENDENCY on:

# - the python3 wedge, so you can do python3 -m pip install.
# - the mypy repo, which has test-requirements.txt

install-py3-libs-in-venv() {
  local venv_dir=$1
  local mypy_dir=$2  # This is a param for host build vs. container build

  source $venv_dir/bin/activate  # enter virtualenv

  # 2023-07 bug fix: have to install MyPy deps FIRST, THEN yapf.  Otherwise
  # we get an error from pip:
  # "ERROR: pip's dependency resolver does not currently take into account all
  # the packages that are installed."

  # for mycpp/
  time python3 -m pip install -r $mypy_dir/test-requirements.txt

  # pexpect: for spec/stateful/*.py
  python3 -m pip install pexpect

  # TODO:
  # - Do something like this 'pip download' in build/deps.sh fetch
  # - Then create a WEDGE which installs it
  #   - However note that this is NOT source code; there is binary code, e.g.
  #   in lxml-*.whl
  if false; then
    local pip_dir=_tmp/pip
    mkdir -p $pip_dir
    python3 -m pip download -d $pip_dir -r $mypy_dir/test-requirements.txt
    python3 -m pip download -d $pip_dir pexpect
  fi
}

install-py3-libs() {
  local mypy_dir=${1:-$DEPS_SOURCE_DIR/mypy/mypy-$MYPY_VERSION}

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

  if ! wedge-exists python2 $PY2_VERSION; then
    deps/wedge.sh unboxed-build _build/deps-source/python2/
  fi

  if test -n "$py_only"; then
    log "Installed dependencies for 'build/py.sh'"
    return
  fi

  # Just copy this source tarball
  if ! wedge-exists pyflakes $PYFLAKES_VERSION; then
    local dest_dir=$USER_WEDGE_DIR/pkg/pyflakes/$PYFLAKES_VERSION
    mkdir -p $dest_dir

    cp --verbose --recursive --no-target-directory \
      $DEPS_SOURCE_DIR/pyflakes/pyflakes-$PYFLAKES_VERSION $dest_dir
  fi

  # TODO: make the Python build faster by using all your cores?
  if ! wedge-exists python3 $PY3_VERSION; then
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

# Host wedges end up in ~/wedge
uftrace-host() {
  ### built on demand; run $0 first

  # BUG: doesn't detect python3
  # WEDGE tells me that it depends on pkg-config
  # 'apt-get install pkgconf' gets it
  # TODO: Should use python3 WEDGE instead of SYSTEM python3?

  deps/wedge.sh unboxed-build _build/deps-source/uftrace
}

R-libs-host() {
  deps/wedge.sh unboxed-build _build/deps-source/R-libs
}

bloaty-host() {
  deps/wedge.sh unboxed-build _build/deps-source/bloaty
}

install-wedges-py() {
  install-wedges py_only
}

container-wedges() {
  ### Build wedges that are copied into containers, not run on host
  
  # These end up in _build/wedge/binary

  #export-podman

  if true; then
    deps/wedge.sh build deps/source.medo/time-helper
    deps/wedge.sh build deps/source.medo/cmark/
    deps/wedge.sh build deps/source.medo/re2c/
    deps/wedge.sh build deps/source.medo/python3/
  fi

  if false; then
    deps/wedge.sh build deps/source.medo/bloaty/
    deps/wedge.sh build deps/source.medo/uftrace/
  fi

  if false; then
    # For soil-benchmarks/ images
    deps/wedge.sh build deps/source.medo/R-libs/
  fi

}

run-task "$@"
