#!/usr/bin/env bash
#
# Script for contributors to build dev dependencies -- packaged as cross-distro
# "wedges".  Tested in the Soil CI.
#
# Usage:
#   build/deps.sh <function name>
#
# Examples:
#   build/deps.sh fetch
#   build/deps.sh install-wedges  # for both Python and C++
#
#   build/deps.sh rm-oils-crap  # rm -r -f /wedge ~/wedge to start over


# Check if we're in the right directory
if [[ ! -d "stdlib/osh" ]]; then
    echo "Error: This script must be run from the root of the Oils project directory"
    echo "Please cd to the root directory and try again"
    exit 1
fi

: ${LIB_OSH=stdlib/osh}
if [[ ! -f "$LIB_OSH/bash-strict.sh" ]] || [[ ! -f "$LIB_OSH/task-five.sh" ]]; then
    echo "Error: Required source files not found in $LIB_OSH/"
    echo "Expected files:"
    echo "  - $LIB_OSH/bash-strict.sh"
    echo "  - $LIB_OSH/task-five.sh"
    exit 1
fi

source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/dev-shell.sh  # TODO: remove this
source deps/from-apt.sh  # PY3_BUILD_DEPS
#source deps/podman.sh
source test/tsv-lib.sh  # tsv-concat
source web/table/html.sh  # table-sort-{begin,end}

# Also in build/dev-shell.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org/pkg
ROOT_WEDGE_DIR=/wedge/oils-for-unix.org/pkg

readonly WEDGE_2025_DIR=../oils.DEPS/wedge
mkdir -p $WEDGE_2025_DIR

readonly DEPS_SOURCE_DIR=_build/deps-source

readonly RE2C_VERSION=3.0
readonly RE2C_URL="https://github.com/skvadrik/re2c/releases/download/$RE2C_VERSION/re2c-$RE2C_VERSION.tar.xz"

readonly CMARK_VERSION=0.29.0
readonly CMARK_URL="https://github.com/commonmark/cmark/archive/$CMARK_VERSION.tar.gz"

readonly PY_FTP_MIRROR="${PY_FTP_MIRROR:-https://www.python.org/ftp}"

readonly PY2_VERSION=2.7.18
readonly PY2_URL="$PY_FTP_MIRROR/python/$PY2_VERSION/Python-$PY2_VERSION.tar.xz"

readonly PY3_VERSION=3.10.4
readonly PY3_URL="$PY_FTP_MIRROR/python/$PY3_VERSION/Python-$PY3_VERSION.tar.xz"

readonly BASH_VER=4.4  # don't clobber BASH_VERSION
readonly BASH_URL="https://www.oilshell.org/blob/spec-bin/bash-$BASH_VER.tar.gz"

# Another version of bash to test
readonly BASH5_VER=5.2.21
readonly BASH5_URL="https://www.oilshell.org/blob/spec-bin/bash-$BASH5_VER.tar.gz"

readonly DASH_VERSION=0.5.10.2
readonly DASH_URL="https://www.oilshell.org/blob/spec-bin/dash-$DASH_VERSION.tar.gz"

readonly ZSH_OLD_VER=5.1.1
readonly ZSH_OLD_URL="https://www.oilshell.org/blob/spec-bin/zsh-$ZSH_OLD_VER.tar.xz"

readonly ZSH_NEW_VER=5.9
readonly ZSH_NEW_URL="https://www.oilshell.org/blob/spec-bin/zsh-$ZSH_NEW_VER.tar.xz"

readonly MKSH_VERSION=R52c
readonly MKSH_URL="https://www.oilshell.org/blob/spec-bin/mksh-$MKSH_VERSION.tgz"

readonly BUSYBOX_VERSION='1.35.0'
readonly BUSYBOX_URL="https://www.oilshell.org/blob/spec-bin/busybox-$BUSYBOX_VERSION.tar.bz2"

readonly YASH_VERSION=2.49
readonly YASH_URL="https://www.oilshell.org/blob/spec-bin/yash-$YASH_VERSION.tar.xz"

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

readonly SOUFFLE_VERSION=2.4.1
readonly SOUFFLE_URL=https://github.com/souffle-lang/souffle/archive/refs/tags/2.4.1.tar.gz

readonly R_LIBS_VERSION='2023-04-18'
readonly TIME_HELPER_VERSION='2023-02-28'
readonly PY3_LIBS_VERSION=2023-03-04

readonly WEDGE_LOG_DIR=_build/wedge/logs

readonly BOXED_WEDGE_DIR=_build/boxed/wedge
readonly BOXED_LOG_DIR=_build/boxed/logs

log() {
  echo "$@" >& 2
}

die() {
  log "$0: fatal: $@"
  exit 1
}

rm-oils-crap() {
  ### When you want to start over

  rm -r -f -v ~/wedge
  sudo rm -r -f -v /wedge
}

# Note: git is an implicit dependency -- that's how we got the repo in the
# first place!

# python2-dev is no longer available on Debian 12
# python-dev also seems gone
#
# wget: for fetching wedges (not on Debian by default!)
# tree: tiny package that's useful for showing what we installed
# g++: essential
# libreadline-dev: needed for the build/prepare.sh Python build.
# gawk: used by spec-runner.sh for the special match() function.
# cmake: for cmark
# PY3_BUILD_DEPS - I think these will be used for building the Python 2 wedge
# as well
readonly -a WEDGE_DEPS_DEBIAN=(
  bzip2 
  wget
  tree
  gawk 
  g++ 
  ninja-build
  cmake
  libreadline-dev 
  systemtap-sdt-dev

  # for Souffle, flex and bison
  #flex bison

  "${PY3_BUILD_DEPS[@]}"
)

readonly -a WEDGE_DEPS_ALPINE=(
  coreutils findutils

  bzip2
  xz

  wget tree gawk

  gcc g++
  ninja-build
  # https://pkgs.alpinelinux.org/packages?name=ninja-is-really-ninja&branch=v3.19&repo=&arch=&maintainer=
  ninja-is-really-ninja
  cmake

  readline-dev
  zlib-dev
  libffi-dev
  openssl-dev

  ncurses-dev

  # for Souffle, flex and bison
  #flex bison
)

readonly -a WEDGE_DEPS_FEDORA=(

  # Weird, Fedora doesn't have these by default!
  hostname
  tar
  bzip2

  # https://packages.fedoraproject.org/pkgs/wget/wget/
  wget
  # https://packages.fedoraproject.org/pkgs/tree-pkg/tree/
  tree
  gawk

  # https://packages.fedoraproject.org/pkgs/gcc/gcc/
  gcc gcc-c++

  ninja-build
  cmake

  readline-devel

  # Like PY3_BUILD_DEPS
  # https://packages.fedoraproject.org/pkgs/zlib/zlib-devel/
  zlib-devel
  # https://packages.fedoraproject.org/pkgs/libffi/libffi-devel/
  libffi-devel
  # https://packages.fedoraproject.org/pkgs/openssl/openssl-devel/
  openssl-devel

  # For building zsh from source?
  # https://koji.fedoraproject.org/koji/rpminfo?rpmID=36987813
  ncurses-devel
  #libcap-devel

  # still have a job control error compiling bash
  # https://packages.fedoraproject.org/pkgs/glibc/glibc-devel/
  # glibc-devel

  libasan
)

readonly -a WEDGE_DEPS_ARCH=(
  # https://archlinux.org/packages/core/x86_64/bzip2/
  bzip2

  # https://archlinux.org/packages/extra/x86_64/wget/
  wget

  # https://archlinux.org/packages/extra/x86_64/tree/
  tree

  # https://archlinux.org/packages/core/x86_64/gawk/
  gawk

  # https://archlinux.org/packages/core/x86_64/gcc/
  gcc

  # https://archlinux.org/packages/community/x86_64/ninja/
  ninja

  # https://archlinux.org/packages/extra/x86_64/cmake/
  cmake

  # https://archlinux.org/packages/core/x86_64/readline/
  readline

  # https://archlinux.org/packages/core/x86_64/zlib/
  zlib

  # https://archlinux.org/packages/core/x86_64/libffi/
  libffi

  # https://archlinux.org/packages/core/x86_64/openssl/
  openssl

  # https://archlinux.org/packages/core/x86_64/ncurses/
  ncurses

  # Development headers are included in the main packages on Arch,
  # unlike other distros that separate them into -dev/-devel packages

  # Python 2 from the AUR
  # https://aur.archlinux.org/packages/python2
  base-devel # needed for building packages from the AUR

)


install-debian-packages() {
  ### Packages for build/py.sh all, building wedges, etc.

  set -x  # show what needs sudo

  # pass -y for say gitpod
  sudo apt "$@" install "${WEDGE_DEPS_DEBIAN[@]}"
  set +x

  # maybe pass -y through
  test/spec-bin.sh install-shells-with-apt "$@"
}

install-ubuntu-packages() {
  ### Debian and Ubuntu packages are the same; this function is suggested on the wiki
  install-debian-packages "$@"
}

wedge-deps-debian() {
  # Install packages without prompt

  # 2024-02 - there was an Ubuntu update, and we started needing this
  sudo apt-get -y update

  install-debian-packages -y
}

wedge-deps-fedora() {
  # https://linuxconfig.org/install-development-tools-on-redhat-8
  # Trying to get past compile errors
  # sudo dnf group install --assumeyes 'Development Tools'

  sudo dnf install --assumeyes "${WEDGE_DEPS_FEDORA[@]}"
}

wedge-deps-alpine() {
  # https://linuxconfig.org/install-development-tools-on-redhat-8
  # Trying to get past compile errors
  # sudo dnf group install --assumeyes 'Development Tools'

  sudo apk add "${WEDGE_DEPS_ALPINE[@]}"
}

wedge-deps-arch() {
  # Install packages without prompt 
  
  # First sync the package database
  sudo pacman -Sy

  # Then install packages
  for pkg in "${WEDGE_DEPS_ARCH[@]}"; do
    # Only install if not already installed
    if ! pacman -Qi "$pkg" >/dev/null 2>&1; then
      sudo pacman --noconfirm -S "$pkg"
    fi
  done
}

#
# Unused patch, was experiment for Fedora
#

get-typed-ast-patch() {
  curl -o deps/typed_ast.patch https://github.com/python/typed_ast/commit/123286721923ae8f3885dbfbad94d6ca940d5c96.patch
}

# Work around typed_ast bug:
#   https://github.com/python/typed_ast/issues/169
#
# Apply this patch
# https://github.com/python/typed_ast/commit/123286721923ae8f3885dbfbad94d6ca940d5c96
#
# typed_ast is tarred up though
patch-typed-ast() {
  local package_dir=_cache/py3-libs
  local patch=$PWD/deps/typed_ast.patch

  pushd $package_dir
  cat $patch
  echo

  local dir=typed_ast-1.4.3
  local tar=typed_ast-1.4.3.tar.gz

  echo OLD
  ls -l $tar
  echo

  rm -r -f -v $dir
  tar -x -z < $tar

  pushd $dir
  patch -p1 < $patch
  popd
  #find $dir

  # Create a new one
  tar --create --gzip --file $tar typed_ast-1.4.3

  echo NEW
  ls -l $tar
  echo

  popd
}

#
# Fetch
#

download-to() {
  local dir=$1
  local url=$2
  wget --no-clobber --directory-prefix "$dir" "$url"
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
    *.gz|*.tgz)  # mksh ends with .tgz
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

  # v$VERSION is a tag, not a branch

  # size optimization: --depth=1 --shallow-submodules
  # https://git-scm.com/docs/git-clone

  git clone --recursive --branch v$version \
    --depth=1 --shallow-submodules \
    $MYPY_GIT_URL $dest

  # TODO: verify commit checksum
}

copy-source-medo() {
  mkdir -p $DEPS_SOURCE_DIR

  # Copy the whole tree, including the .treeptr files
  cp --verbose --recursive --no-target-directory \
    deps/source.medo/ $DEPS_SOURCE_DIR/
}

fetch-spec-bin() {
  download-to $DEPS_SOURCE_DIR/bash "$BASH_URL"
  maybe-extract $DEPS_SOURCE_DIR/bash "$(basename $BASH_URL)" bash-$BASH_VER

  download-to $DEPS_SOURCE_DIR/bash "$BASH5_URL"
  maybe-extract $DEPS_SOURCE_DIR/bash "$(basename $BASH5_URL)" bash-$BASH5_VER

  download-to $DEPS_SOURCE_DIR/dash "$DASH_URL"
  maybe-extract $DEPS_SOURCE_DIR/dash "$(basename $DASH_URL)" dash-$DASH_VERSION

  download-to $DEPS_SOURCE_DIR/zsh "$ZSH_OLD_URL"
  maybe-extract $DEPS_SOURCE_DIR/zsh "$(basename $ZSH_OLD_URL)" zsh-$ZSH_OLD_VER

  download-to $DEPS_SOURCE_DIR/zsh "$ZSH_NEW_URL"
  maybe-extract $DEPS_SOURCE_DIR/zsh "$(basename $ZSH_NEW_URL)" zsh-$ZSH_NEW_VER

  download-to $DEPS_SOURCE_DIR/mksh "$MKSH_URL"
  maybe-extract $DEPS_SOURCE_DIR/mksh "$(basename $MKSH_URL)" mksh-$MKSH_VERSION

  download-to $DEPS_SOURCE_DIR/busybox "$BUSYBOX_URL"
  maybe-extract $DEPS_SOURCE_DIR/busybox "$(basename $BUSYBOX_URL)" busybox-$BUSYBOX_VERSION

  download-to $DEPS_SOURCE_DIR/yash "$YASH_URL"
  maybe-extract $DEPS_SOURCE_DIR/yash "$(basename $YASH_URL)" yash-$YASH_VERSION

  # Patch: this tarball doesn't follow the convention $name-$version
  if test -d $DEPS_SOURCE_DIR/mksh/mksh; then
    pushd $DEPS_SOURCE_DIR/mksh
    mv -v mksh mksh-$MKSH_VERSION
    popd
  fi
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

  copy-source-medo

  # Hack
  local dest=$DEPS_SOURCE_DIR/time-helper/time-helper-$TIME_HELPER_VERSION
  mkdir -p $dest
  cp -v benchmarks/time-helper.c $dest

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

  fetch-spec-bin

  # bloaty and uftrace are for benchmarks, in containers
  download-to $DEPS_SOURCE_DIR/bloaty "$BLOATY_URL"
  download-to $DEPS_SOURCE_DIR/uftrace "$UFTRACE_URL"
  maybe-extract $DEPS_SOURCE_DIR/bloaty "$(basename $BLOATY_URL)" bloaty-$BLOATY_VERSION
  maybe-extract $DEPS_SOURCE_DIR/uftrace "$(basename $UFTRACE_URL)" uftrace-$UFTRACE_VERSION

  # This is in $DEPS_SOURCE_DIR to COPY into containers, which mycpp will directly import.

  # It's also copied into a wedge in install-wedges.
  clone-mypy $DEPS_SOURCE_DIR/mypy

  if false; then
    download-to $DEPS_SOURCE_DIR/souffle "$SOUFFLE_URL"
    maybe-extract $DEPS_SOURCE_DIR/souffle "$(basename $SOUFFLE_URL)" souffle-$SOUFFLE_VERSION
  fi

  if command -v tree > /dev/null; then
    tree -L 2 $DEPS_SOURCE_DIR
  fi
}

fetch-py() {
  fetch py_only
}

mirror-pyflakes() {
  ### Workaround for network error during release
  scp \
    $DEPS_SOURCE_DIR/pyflakes/"$(basename $PYFLAKES_URL)" \
    oilshell.org:oilshell.org/blob/
}

mirror-python() {
  ### Can't reach python.org from some machines
  scp \
    $DEPS_SOURCE_DIR/python2/"$(basename $PY2_URL)" \
    oilshell.org:oilshell.org/blob/

  scp \
    $DEPS_SOURCE_DIR/python3/"$(basename $PY3_URL)" \
    oilshell.org:oilshell.org/blob/
}

mirror-zsh() {
  scp \
    _tmp/zsh-5.9.tar.xz \
    oilshell.org:oilshell.org/blob/
}

wedge-exists() {
  ### Does an installed wedge already exist?
  local name=$1
  local version=$2
  local wedge_base_dir=${3:-/wedge/oils-for-unix.org}  # e.g. ../oils.DEPS/wedge

  local installed=$wedge_base_dir/$name/$version

  if test -d $installed; then
    log "$installed already exists"
    return 0
  else
    return 1
  fi
}

boxed-wedge-exists() {
  ### Does an installed wedge already exist?

  local name=$1
  local version=$2

  # NOT USED for now
  local distro=${3:-debian-12}

  local installed=$BOXED_WEDGE_DIR/$name/$version

  if test -d $installed; then
    log "$installed already exists"
    return 0
  else
    return 1
  fi
}

#
# Install
#

# TODO: py3-libs needs to be a WEDGE, so that that you can run
# 'wedge build deps/source.medo/py3-libs/' and then get it in
#
# _build/wedge/{absolute,relative}   # which one?
#
# It needs a BUILD DEPENDENCY on:
# - the python3 wedge, so you can do python3 -m pip install.
# - the mypy repo, which has test-requirements.txt

download-py3-libs() {
  ### Download source/binary packages, AFTER python3 is installed

  # Note that this is NOT source code; there is binary code, e.g.  in
  # lxml-*.whl

  local mypy_dir=${1:-$DEPS_SOURCE_DIR/mypy/mypy-$MYPY_VERSION}
  local py_package_dir=_cache/py3-libs
  mkdir -p $py_package_dir

  # Avoids a warning, but doesn't fix typed_ast
  #python3 -m pip download -d $py_package_dir wheel

  python3 -m pip download -d $py_package_dir -r $mypy_dir/test-requirements.txt
  python3 -m pip download -d $py_package_dir pexpect pyte
}

install-py3-libs-in-venv() {
  local venv_dir=$1
  local mypy_dir=$2  # This is a param for host build vs. container build
  local package_dir=_cache/py3-libs

  source $venv_dir/bin/activate  # enter virtualenv

  # 2023-07 note: we're installing yapf in a DIFFERENT venv, because it
  # conflicts with MyPy deps!
  # "ERROR: pip's dependency resolver does not currently take into account all
  # the packages that are installed."

  # --find-links uses a "cache dir" for packages (weird flag name!)

  # Avoids a warning, but doesn't fix typed_ast
  #time python3 -m pip install --find-links $package_dir wheel

  upgrade-typed-ast $mypy_dir/mypy-requirements.txt

  # for mycpp/
  time python3 -m pip install --find-links $package_dir -r $mypy_dir/test-requirements.txt

  # pexpect: for spec/stateful/*.py
  time python3 -m pip install --find-links $package_dir pexpect pyte
}

upgrade-typed-ast() {
  local file=$1
  sed -i 's/typed_ast.*/typed_ast==1.5.0/' $file
}

test-typed-ast() {
  local dir=~/wedge/oils-for-unix.org/pkg/mypy/0.780

  cp -v $dir/mypy-requirements.txt _tmp

  local file=_tmp/mypy-requirements.txt
  cat $file
  #echo

  # 1.5.0 fixed this bug
  # https://github.com/python/typed_ast/issues/169 

  upgrade-typed-ast $file
  echo
  cat $file
}

install-py3-libs-from-cache() {
  # As well as end users
  local mypy_dir=${1:-$DEPS_SOURCE_DIR/mypy/mypy-$MYPY_VERSION}
  local wedge_out_dir=${2:-$USER_WEDGE_DIR}

  local py3
  py3=$(command -v python3)
  case $py3 in
    *wedge/oils-for-unix.org/*)
      ;;
    *oils.DEPS/*)
      ;;
    *)
      die "python3 is '$py3', but expected it to be in a wedge"
      ;;
  esac

  log "Ensuring pip is installed (interpreter $(command -v python3)"
  python3 -m ensurepip

  local venv_dir=$wedge_out_dir/py3-libs/$PY3_LIBS_VERSION
  log "Creating venv in $venv_dir"

  # Note: the bin/python3 in this venv is a symlink to python3 in $PATH, i.e.
  # the /wedge we just built
  python3 -m venv $venv_dir

  log "Installing MyPy deps in venv"

  # Run in a subshell because it mutates shell state
  $0 install-py3-libs-in-venv $venv_dir $mypy_dir
}

install-py3-libs() {
  ### Invoked by Dockerfile.cpp-small, etc.
  local mypy_dir=${1:-}
  local wedge_out_dir=${2:-}

  download-py3-libs $mypy_dir
  install-py3-libs-from-cache "$mypy_dir" "$wedge_out_dir"
}

#
# Wedge manifests
#

py-wedges() {
  ### for build/py.sh all
  local how=${1:-legacy}

  if test $how = 'boxed'; then
    local where='debian-12'
  else
    local where='HOST'
  fi
  case $how in
    boxed|unboxed)
      echo time-helper $TIME_HELPER_VERSION $WEDGE_2025_DIR $where
      echo cmark $CMARK_VERSION $WEDGE_2025_DIR $where
      echo re2c $RE2C_VERSION $WEDGE_2025_DIR $where
      echo python2 $PY2_VERSION $WEDGE_2025_DIR $where
      echo pyflakes $PYFLAKES_VERSION $WEDGE_2025_DIR $where
      ;;
    legacy)
      echo time-helper $TIME_HELPER_VERSION $ROOT_WEDGE_DIR $where
      echo cmark $CMARK_VERSION $ROOT_WEDGE_DIR $where
      echo re2c $RE2C_VERSION $ROOT_WEDGE_DIR $where
      echo python2 $PY2_VERSION $ROOT_WEDGE_DIR $where
      echo pyflakes $PYFLAKES_VERSION $USER_WEDGE_DIR $where
      ;;
    *)
      die "Invalid how $how"
  esac
}

cpp-wedges() {
  ### for ninja / mycpp translation
  local how=${1:-legacy}

  if test $how = 'boxed'; then
    local where='debian-12'
  else
    local where='HOST'
  fi
  case $how in
    boxed|unboxed)
      echo python3 $PY3_VERSION $WEDGE_2025_DIR $where
      echo mypy $MYPY_VERSION $WEDGE_2025_DIR $where
      ;;
    legacy)
      echo python3 $PY3_VERSION $ROOT_WEDGE_DIR $where
      echo mypy $MYPY_VERSION $USER_WEDGE_DIR $where
      ;;
    *)
      die "Invalid how $how"
  esac

  # py3-libs has a built time dep on both python3 and MyPy, so we're doing it
  # separately for now
  #echo py3-libs $PY3_LIBS_VERSION $USER_WEDGE_DIR
}

spec-bin-wedges() {
  ### for test/spec-py.sh osh-all
  local how=${1:-legacy}

  if test $how = 'boxed'; then
    local where='debian-12'
  else
    local where='HOST'
  fi
  case $how in
    boxed|unboxed)
      echo dash $DASH_VERSION $WEDGE_2025_DIR $where
      echo bash $BASH_VER $WEDGE_2025_DIR $where
      echo bash $BASH5_VER $WEDGE_2025_DIR $where
      echo mksh $MKSH_VERSION $WEDGE_2025_DIR $where
      echo zsh $ZSH_OLD_VER $WEDGE_2025_DIR $where
      echo zsh $ZSH_NEW_VER $WEDGE_2025_DIR $where
      echo busybox $BUSYBOX_VERSION $WEDGE_2025_DIR $where
      echo yash $YASH_VERSION $WEDGE_2025_DIR $where
      ;;
    legacy)
      echo dash $DASH_VERSION $USER_WEDGE_DIR $where
      echo bash $BASH_VER $USER_WEDGE_DIR $where
      echo bash $BASH5_VER $USER_WEDGE_DIR $where
      echo mksh $MKSH_VERSION $USER_WEDGE_DIR $where
      echo zsh $ZSH_OLD_VER $USER_WEDGE_DIR $where
      echo zsh $ZSH_NEW_VER $USER_WEDGE_DIR $where
      echo busybox $BUSYBOX_VERSION $USER_WEDGE_DIR $where
      echo yash $YASH_VERSION $USER_WEDGE_DIR $where
      ;;
    *)
      die "Invalid how $how"
  esac
}

zsh-wedges() {
  local how=${1:-legacy}

  if test $how = 'boxed'; then
    local where='debian-12'
  else
    local where='HOST'
  fi
  case $how in
    boxed|unboxed)
      echo zsh $ZSH_OLD_VER $WEDGE_2025_DIR $where
      echo zsh $ZSH_NEW_VER $WEDGE_2025_DIR $where
      ;;
    legacy)
      echo zsh $ZSH_OLD_VER $USER_WEDGE_DIR $where
      echo zsh $ZSH_NEW_VER $USER_WEDGE_DIR $where
      ;;
    *)
      die "Invalid how $how"
  esac
}

smoke-wedges() {
  local how=${1:-legacy}

  if test $how = 'boxed'; then
    local where='debian-12'
  else
    local where='HOST'
  fi
  case $how in
    boxed|unboxed)
      echo dash $DASH_VERSION $WEDGE_2025_DIR $where
      ;;
    legacy)
      echo dash $DASH_VERSION $USER_WEDGE_DIR $where
      ;;
    *)
      die "Invalid how $how"
  esac
}

cmark-wedges() {
  local how=${1:-legacy}

  if test $how = 'boxed'; then
    local where='debian-12'
  else
    local where='HOST'
  fi
  case $how in
    boxed|unboxed)
      echo cmark $CMARK_VERSION $WEDGE_2025_DIR $where
      ;;
    legacy)
      echo cmark $CMARK_VERSION $ROOT_WEDGE_DIR $where
      ;;
    *)
      die "Invalid how $how"
  esac
}

extra-wedges() {
  # Contributors don't need uftrace, bloaty, and probably R-libs
  # Although R-libs could be useful for benchmarks

  local how=${1:-legacy}

  case $how in
    boxed)
      echo R-libs $R_LIBS_VERSION $WEDGE_2025_DIR debian-12
      echo uftrace $UFTRACE_VERSION $WEDGE_2025_DIR debian-12
      echo bloaty $BLOATY_VERSION $WEDGE_2025_DIR debian-10  # It works on Debian 10, not 12
      ;;
    unboxed)
      echo R-libs $R_LIBS_VERSION $WEDGE_2025_DIR HOST
      echo uftrace $UFTRACE_VERSION $WEDGE_2025_DIR HOST
      echo bloaty $BLOATY_VERSION $WEDGE_2025_DIR HOST
      ;;
    legacy)
      echo R-libs $R_LIBS_VERSION $USER_WEDGE_DIR HOST
      echo uftrace $UFTRACE_VERSION $ROOT_WEDGE_DIR HOST
      echo bloaty $BLOATY_VERSION $ROOT_WEDGE_DIR HOST
      ;;
    *)
      die "Invalid how $how"
  esac
}

contributor-wedges() {
  local how=${1:-}

  py-wedges "$how"
  cpp-wedges "$how"
  spec-bin-wedges "$how"
}

#
# More
#

timestamp() {
  date '+%H:%M:%S'
}

my-time-tsv() {
  python3 benchmarks/time_.py \
    --tsv \
    --time-span --rusage \
    "$@"
}

maybe-install-wedge() {
  local how=${1:-legacy}
  local name=$2
  local version=$3
  local wedge_base_dir=$4
  local where=$5

  if test $where != HOST; then
    die 'Expected $where to be "HOST"'
  fi

  local task_file=$WEDGE_LOG_DIR/$name-$version.task.tsv
  local log_file=$WEDGE_LOG_DIR/$name-$version.log.txt

  echo "  TASK  $(timestamp)  $name $version > $log_file"

  # python3 because it's OUTSIDE the container
  # Separate columns that could be joined: number of files, total size
  my-time-tsv --print-header \
    --field xargs_slot \
    --field wedge \
    --field wedge_HREF \
    --field version \
    --output $task_file

  if wedge-exists "$name" "$version" "$wedge_base_dir"; then
    echo "CACHED  $(timestamp)  $name $version"
    return
  fi

  case $how in
    unboxed)
      # TODO: I think all the builds should set the install dir, which is the LOCAL output
      # - wedge unboxed
      # - wedge unboxed-2025
      # - wedge boxed-2025
      # instead of relying on this flag
      #
      # So we have (NAME, VERSION, INSTALL_OUT) as our params.  That makes sense
      export WEDGE_2025=1
      ;;
  esac

  local -a cmd=( deps/wedge.sh unboxed _build/deps-source/$name/ $version $wedge_base_dir)

  set +o errexit
  my-time-tsv \
    --field "$XARGS_SLOT" \
    --field "$name" \
    --field "$name-$version.log.txt" \
    --field "$version" \
    --append \
    --output $task_file \
    -- \
    "${cmd[@]}" "$@" >$log_file 2>&1
  local status=$?
  set -o errexit

  if test "$status" -eq 0; then
    echo "    OK  $(timestamp)  $name $version"
  else
    echo "  FAIL  $(timestamp)  $name $version"
  fi
}

dummy-task() {
  ### For testing log capture
  local name=$1
  local version=$2

  echo "Building $name $version"

  # random float between 0 and 3
  # weirdly we need a seed from bash
  # https://stackoverflow.com/questions/4048378/random-numbers-generation-with-awk-in-bash-shell
  local secs
  secs=$(awk -v seed=$RANDOM 'END { srand(seed); print rand() * 3 }' < /dev/null)

  echo "sleep $secs"
  sleep $secs

  echo 'stdout'
  log 'stderr'

  if test $name = 'mksh'; then
    echo "simulate failure for $name"
    exit 2
  fi
}

dummy-task-wrapper() {
  # Similar to test/common.sh run-task-with-status, used by
  # test/{spec,wild}-runner.sh
  local name=$1
  local version=$2

  local task_file=$WEDGE_LOG_DIR/$name.task.tsv
  local log_file=$WEDGE_LOG_DIR/$name.log.txt

  echo "  TASK  $(timestamp)  $name $version > $log_file"

  # python3 because it's OUTSIDE the container
  # Separate columns that could be joined: number of files, total size
  my-time-tsv --print-header \
    --field xargs_slot \
    --field wedge \
    --field wedge_HREF \
    --field version \
    --output $task_file

  my-time-tsv \
    --field "$XARGS_SLOT" \
    --field "$name" \
    --field "$name.log.txt" \
    --field "$version" \
    --append \
    --output $task_file \
    $0 dummy-task "$@" >$log_file 2>&1 || true

  echo "  DONE  $(timestamp)  $name $version"
}

html-head() {
  # python3 because we're outside containers
  PYTHONPATH=. python3 doctools/html_head.py "$@"
}

index-html()  {
  local tasks_tsv=$1

  local base_url='../../../web'
  html-head --title 'Wedge Builds' \
    "$base_url/ajax.js" \
    "$base_url/table/table-sort.js" \
    "$base_url/table/table-sort.css" \
    "$base_url/base.css"

  table-sort-begin 'width60'

  cat <<EOF
    <p id="home-link">
      <a href="/">oils.pub</a>
    </p>

  <h1>Wedge Builds</h1>
EOF

  tsv2html3 $tasks_tsv

  cat <<EOF
  <p>
    <a href="tasks.tsv">tasks.tsv</a>
  </p>
EOF

  table-sort-end 'tasks'  # ID for sorting
}

NPROC=$(nproc)
#NPROC=1

install-wedge-list() {
  ### Reads task rows from stdin
  local how=${1:-legacy}  # unboxed | legacy
  local parallel=${2:-}

  mkdir -p $WEDGE_LOG_DIR

  local -a flags
  if test -n "$parallel"; then
    log ""
    log "=== Installing wedges with $NPROC jobs in parallel"
    log ""
    flags=( -P $NPROC )
  else
    log ""
    log "=== Installing wedges serially"
    log ""
  fi

  # Reads from stdin
  # Note: --process-slot-var requires GNU xargs!  busybox args doesn't have it.
  #
  # $name $version $wedge_dir
  xargs "${flags[@]}" -n 4 --process-slot-var=XARGS_SLOT -- $0 maybe-install-wedge "$how"

  #xargs "${flags[@]}" -n 3 --process-slot-var=XARGS_SLOT -- $0 dummy-task-wrapper
}

write-task-report() {
  local tasks_tsv=$WEDGE_LOG_DIR/tasks.tsv

  python3 devtools/tsv_concat.py $WEDGE_LOG_DIR/*.task.tsv > $tasks_tsv
  log "Wrote $tasks_tsv"

  # TODO: version can be right-justified?
  here-schema-tsv-4col >$WEDGE_LOG_DIR/tasks.schema.tsv <<EOF
column_name   type      precision strftime
status        integer   0         -
elapsed_secs  float     1         -
start_time    float     1         %H:%M:%S
end_time      float     1         %H:%M:%S
user_secs     float     1         -
sys_secs      float     1         -
max_rss_KiB   integer   0         -
xargs_slot    integer   0         -
wedge         string    0         -
wedge_HREF    string    0         -
version       string    0         -
EOF

  index-html $tasks_tsv > $WEDGE_LOG_DIR/index.html
  log "Wrote $WEDGE_LOG_DIR/index.html"
}

fake-py3-libs-wedge() {
  local wedge_out_dir=${1:-}

  local name=py3-libs
  local version=$PY3_LIBS_VERSION

  local task_file=$WEDGE_LOG_DIR/$name.task.tsv
  local log_file=$WEDGE_LOG_DIR/$name.log.txt

  my-time-tsv --print-header \
    --field xargs_slot \
    --field wedge \
    --field wedge_HREF \
    --field version \
    --output $task_file

  # There is no xargs slot!
  my-time-tsv \
    --field "-1" \
    --field "$name" \
    --field "$name.log.txt" \
    --field "$version" \
    --append \
    --output $task_file \
    -- \
    $0 install-py3-libs '' "$wedge_out_dir" >$log_file 2>&1 || true

  echo "  FAKE  $(timestamp)  $name $version"
}

print-wedge-list() {
  local which_wedges=${1:-contrib}  # contrib | soil | smoke
  local how=${2:-legacy}            # boxed | unboxed | legacy

  case $which_wedges in
    contrib)
      contributor-wedges "$how"
      ;;
    soil)
      contributor-wedges "$how"
      extra-wedges "$how"
      ;;
    extra-only)
      extra-wedges "$how"
      ;;
    smoke)
      #zsh-wedges "$how"
      smoke-wedges "$how"
      ;;
    cmark)  # for testing mkdir /wedge BUG
      cmark-wedges "$how"
      ;;
    *)
      die "Invalid which_wedges $which_wedges"
      ;;
  esac 
}

install-wedges() {
  local which_wedges=${1:-contrib}  # contrib | soil | smoke
  local how=${2:-legacy}            # boxed | unboxed | legacy

  # For contributor setup: we need to use this BEFORE running build/py.sh all
  build/py.sh time-helper

  echo " START  $(timestamp)"

  # Do all of them in parallel
  print-wedge-list "$which_wedges" "$how" | install-wedge-list "$how" T

  local wedge_out_dir
  case $how in
    unboxed)
      wedge_out_dir=$WEDGE_2025_DIR
      ;;
    legacy)
      wedge_out_dir=$USER_WEDGE_DIR
      ;;
    *)
      die "Invalid how $how"
      ;;
  esac
  fake-py3-libs-wedge "$wedge_out_dir"

  echo "   END  $(timestamp)"

  write-task-report
}

install-wedges-fast() {
  ### Alias for compatibility
  install-wedges "$@"
}

install-wedges-soil() {
  install-wedges soil
}

#
# Unboxed wedge builds
#

uftrace-host() {
  ### built on demand; run $0 first

  # BUG: doesn't detect python3
  # WEDGE tells me that it depends on pkg-config
  # 'apt-get install pkgconf' gets it
  # TODO: Should use python3 WEDGE instead of SYSTEM python3?
  deps/wedge.sh unboxed _build/deps-source/uftrace
}

bloaty-host() {
  deps/wedge.sh unboxed _build/deps-source/bloaty
}

R-libs-host() {
  deps/wedge.sh unboxed _build/deps-source/R-libs
}

#
# Wedges built inside a container, for copying into a container
#

boxed-clean() {
  # Source dir is _build/deps-source
  time sudo rm -r -f _build/boxed
}

boxed-spec-bin() {
  if true; then
    deps/wedge.sh boxed deps/source.medo/bash '4.4'
    deps/wedge.sh boxed deps/source.medo/bash '5.2.21'
  fi

  if true; then
    deps/wedge.sh boxed deps/source.medo/dash
    deps/wedge.sh boxed deps/source.medo/mksh
  fi

  if true; then
    # Note: zsh requires libncursesw5-dev
    deps/wedge.sh boxed deps/source.medo/zsh $ZSH_OLD_VER
    deps/wedge.sh boxed deps/source.medo/zsh $ZSH_NEW_VER
  fi

  if true; then
    deps/wedge.sh boxed deps/source.medo/busybox

    # Problem with out of tree build, as above.  Skipping for now
    deps/wedge.sh boxed deps/source.medo/yash
    echo
  fi
}

_boxed-wedges() {
  #### host _build/wedge/binary -> guest container /wedge or ~/wedge

  # This is in contrast

  # TODO:
  # - Use the same manifest as install-wedges
  #   - so then you can delete the _build/wedge dir to re-run it
  #   - use xargs -n 1 so it's done serially
  # - Do these lazily like we do in install-wedges
  # - Migrate to podman
  #   - Pass --network=none where possible

  # We can test if the dir _build/wedge/binary/oils-for-unix.org/pkg/FOO exists
  # if wedge-exists "$name" "$version" "$wedge_dir"; then
  #  echo "CACHED  $(timestamp)  $name $version"
  #  return
  # fi

  local resume1=${1:-}

  if true; then
    deps/wedge.sh boxed deps/source.medo/dash/ '' $USER_WEDGE_DIR debian-12
  fi

  #if test -z "$resume1"; then
  if false; then
    boxed-spec-bin

    deps/wedge.sh boxed deps/source.medo/python2/ '' debian-12
  fi

  if false; then
    deps/wedge.sh boxed deps/source.medo/python3/ '' debian-12
    deps/wedge.sh boxed deps/source.medo/time-helper '' debian-12
  fi

  if false; then
    # soil-benchmarks
    deps/wedge.sh boxed deps/source.medo/uftrace/ '' debian-12
  fi

  if false; then
    deps/wedge.sh boxed deps/source.medo/cmark/ '' debian-12
    deps/wedge.sh boxed deps/source.medo/re2c/ '' debian-12
  fi

  if false; then
    # debian 10 for now
    deps/wedge.sh boxed deps/source.medo/bloaty/ '' # debian-12
  fi

  if false; then
    # Used in {benchmarks,benchmarks2,other-tests}
    deps/wedge.sh boxed deps/source.medo/R-libs/ '' debian-12
  fi
}

boxed-wedges() {
  time $0 _boxed-wedges "$@"
}

uftrace-boxed() {
  ### until we can move uftrace to ../oils.DEPS/wedge

  deps/wedge.sh boxed deps/source.medo/uftrace/ '' $ROOT_WEDGE_DIR debian-12
}


maybe-boxed-wedge() {
  local name=$1
  local version=$2
  local wedge_base_dir=$3  # e.g. oils.DEPS or _build/boxed/wedge?
  local distro=$4  # e.g. debian-12 or empty

  local task_file=$BOXED_LOG_DIR/$name-$version.task.tsv
  local log_file=$BOXED_LOG_DIR/$name-$version.log.txt

  echo "  TASK  $(timestamp)  $name $version > $log_file"

  # python3 because it's OUTSIDE the container
  # Separate columns that could be joined: number of files, total size
  my-time-tsv --print-header \
    --field xargs_slot \
    --field wedge \
    --field wedge_HREF \
    --field version \
    --output $task_file

  if boxed-wedge-exists "$name" "$version" "$distro"; then
    echo "CACHED  $(timestamp)  $name $version"
    return
  fi

  #local -a cmd=( deps/wedge.sh boxed-2025 _build/deps-source/$name/ $version)
  local -a cmd=(
    deps/wedge.sh boxed-2025 deps/source.medo/$name/ "$version" "$wedge_base_dir" "$distro"
  )

  set +o errexit
  my-time-tsv \
    --field "$XARGS_SLOT" \
    --field "$name" \
    --field "$name-$version.log.txt" \
    --field "$version" \
    --append \
    --output $task_file \
    -- \
    "${cmd[@]}" "$@" >$log_file 2>&1
  local status=$?
  set -o errexit

  if test "$status" -eq 0; then
    echo "    OK  $(timestamp)  $name $version"
  else
    echo "  FAIL  $(timestamp)  $name $version"
  fi
}

do-boxed-wedge-list() {
  ### Reads task rows from stdin
  local parallel=${1:-}

  mkdir -p $BOXED_LOG_DIR

  local -a flags
  if test -n "$parallel"; then
    log ""
    log "=== Building boxed wedges with $NPROC jobs in parallel"
    log ""
    flags=( -P $NPROC )
  else
    log ""
    log "=== Building boxed wedges serially"
    log ""
  fi

  # Reads from stdin
  # Note: --process-slot-var requires GNU xargs!  busybox args doesn't have it.
  #
  # $name $version $wedge_dir
  xargs "${flags[@]}" -n 4 --process-slot-var=XARGS_SLOT -- $0 maybe-boxed-wedge

  #xargs "${flags[@]}" -n 3 --process-slot-var=XARGS_SLOT -- $0 dummy-task-wrapper
}


_boxed-wedges-2025-TEST() {
  # fastest one
  deps/wedge.sh boxed-2025 deps/source.medo/time-helper '' debian-12

  if true; then
    # debian 10 for now
    deps/wedge.sh boxed-2025 deps/source.medo/bloaty/ '' # debian-12
  fi
}

_boxed-wedges-2025() {
  local which_wedges=${1:-contrib}  # contrib | soil | smoke

  # For contributor setup: we need to use this BEFORE running build/py.sh all
  #build/py.sh time-helper

  echo " START  $(timestamp)"

  # Do all of them in parallel
  print-wedge-list "$which_wedges" boxed | do-boxed-wedge-list T

  # Dockerfile.* calls install-py3-libs from within the container, so we don't need this
  # It depends on MyPy
  #fake-py3-libs-wedge ../oils.DEPS/wedge

  echo "   END  $(timestamp)"

  write-task-report
}

boxed-wedges-2025() {
  time $0 _boxed-wedges-2025 "$@"
}


#
# Report
#

commas() {
  # Wow I didn't know this :a trick
  #
  # OK this is a label and a loop, which makes sense.  You can't do it with
  # pure regex.
  #
  # https://shallowsky.com/blog/linux/cmdline/sed-improve-comma-insertion.html
  # https://shallowsky.com/blog/linux/cmdline/sed-improve-comma-insertion.html
  sed ':a;s/\b\([0-9]\+\)\([0-9]\{3\}\)\b/\1,\2/;ta'   
}

wedge-sizes() {
  local tmp=_tmp/wedge-sizes.txt

  # -b is --bytes, but use short flag for busybox compat
  du -s -b /wedge/*/*/* ~/wedge/*/*/* | awk '
    { print $0  # print the line
      total_bytes += $1  # accumulate
    }
END { print total_bytes " TOTAL" }
' > $tmp
  
  # printf justifies du output
  cat $tmp | commas | xargs -n 2 printf '%15s  %s\n'
  echo

  #du -s --si /wedge/*/*/* ~/wedge/*/*/* 
  #echo
}

wedge-report() {
  # 4 levels deep shows the package
  if command -v tree > /dev/null; then
    tree -L 4 /wedge ~/wedge
    echo
  fi

  wedge-sizes

  local tmp=_tmp/wedge-manifest.txt

  echo 'Biggest files'
  if ! find /wedge ~/wedge -type f -a -printf '%10s %P\n' > $tmp; then
    # busybox find doesn't have -printf
    echo 'find -printf failed'
    return
  fi

  set +o errexit  # ignore SIGPIPE
  sort -n --reverse $tmp | head -n 20 | commas
  set -o errexit

  echo

  # Show the most common file extensions
  #
  # I feel like we should be able to get rid of .a files?  That's 92 MB, second
  # most common
  #
  # There are also duplicate .a files for Python -- should look at how distros
  # get rid of those

  cat $tmp | python3 -c '
import os, sys, collections

bytes = collections.Counter()
files = collections.Counter()

for line in sys.stdin:
  size, path = line.split(None, 1)
  path = path.strip()  # remove newline
  _, ext = os.path.splitext(path)
  size = int(size)

  bytes[ext] += size
  files[ext] += 1

#print(bytes)
#print(files)

n = 20

print("Most common file types")
for ext, count in files.most_common()[:n]:
  print("%10d  %s" % (count, ext))

print()

print("Total bytes by file type")
for ext, total_bytes in bytes.most_common()[:n]:
  print("%10d  %s" % (total_bytes, ext))
' | commas
}

libssl-bug() {
  set -x
  file=_build/wedge/binary/oils-for-unix.org/pkg/python3/3.10.4/lib/python3.10/lib-dynload/_ssl.cpython-310-x86_64-linux-gnu.so

  # TODO: figure out how to get this to find libssl.so.3, not .so.1.1
  ldd $file
  echo
  ls -l $file
 
}

libssl-smoke() {
  deps/wedge.sh smoke-test deps/source.medo/python3/ '' '' debian-12
}

smoke-unboxed-boxed() {
  install-wedges smoke legacy
  echo
  ls -l ~/wedge/oils-for-unix.org/pkg/dash

  install-wedges smoke unboxed
  echo
  ls -l ../oils.DEPS/wedge/dash

  boxed-wedges-2025 smoke
  echo
  ls -l _build/boxed/wedge/dash

  # old boxed wedges: they never had xargs automation
  #boxed-wedges

  # TODO: now invalidate cache, and build again
}

each-one() {
  # like xargs -n 1, but RESPECTS ERREXIT!
  while read -r task; do
    "$@" "$task"
  done
}

_build-soil-images() {
  # this excludes the test image

  deps/images.sh list soil | each-one deps/images.sh build-cached
}

build-soil-images() {
  time _build-soil-images "$@"
}

push-all-images() {
  deps/images.sh list | xargs --verbose -n 1 -- deps/images.sh push
}

download-for-soil() {
  deps/from-binary.sh download-clang
  deps/from-tar.sh download-wild
}

_full-soil-rebuild() {
  local resume1=${1:-}
  local resume2=${2:-}
  local resume3=${3:-}
  local resume4=${4:-}

  if test -z "$resume1"; then
    download-for-soil
  fi

  if test -z "$resume2"; then
    boxed-clean
    # TODO: can also rm-oils-crap and _build/wedge/*

    fetch
    # 'soil' includes bloaty, uftrace, R-libs
    boxed-wedges-2025 soil
  fi

  if test -z "$resume3"; then
    # build to populate apt-cache
    deps/images.sh build wedge-bootstrap-debian-12
    deps/images.sh build soil-debian-12
  fi

  if test -z "$resume4"; then
    build-soil-images
  fi

  push-all-images

  # soil/worker.sh list-jobs?  No this has the VIM
  # we need soil/host-shim.sh list-images.sh or something

  # Full rebuilds DONE:
  # a. soil-debian-12 rebuild - with python2 etc.
  # b. Remove commented out code from dockerfiles
  #
  # TODO
  # 2. Remove OLD COMPAT stuff that contributors won't use
  #    - pea_main wrapper - build/ninja-rules-py.sh
  # 3. wedge-boostrap: rename uke0 -> uke
  #    - hopefully this fixes the uftrace wedge
  # 4. everything with podman - build on hoover machine
  # 5. everything with rootless podman
  # 6. everything with raw crun - requires some other rewrites
  # 7. coarse tree-shaking for task-five.sh, etc.

  # MORE WEDGES
  # - test/wild.sh - oil_DEPS ->
  # - ovm-tarball - oil_DEPS -> ../oils.DEPS/wedge/python2-slice
  # - clang binary - contributors use this
  # - benchmarks/osh-runtime files

  # Dependencies
  # - py3-libs depends on python3, and on mypy-requirements.txt
  # - uftrace depends on python3 - is it system python3?
}

full-soil-rebuild() {
  time _full-soil-rebuild "$@"
}

_full-host-rebuild() {
  rm-oils-crap  # old dirs
  rm -r -f ../oils.DEPS/  # new dir
  install-wedges contrib unboxed
}

full-host-rebuild() {
  time _full-host-rebuild "$@"
}

task-five "$@"
