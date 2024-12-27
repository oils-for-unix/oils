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
#
# TODO: Do we need something faster, just python2, re2c, and cmark?
#
#   - build/deps.sh fetch-py
#   - build/deps.sh install-wedges-py
#
# TODO: Can we make most of them non-root deps?  This requires rebuilding
# containers, which requires podman.
#
#     rm -r -f ~/wedge  # would be better


# Check if we're in the right directory
if [[ ! -d "stdlib/osh" ]]; then
    echo "Error: This script must be run from the root of the Oil project directory"
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

source build/dev-shell.sh  # python3 in PATH, PY3_LIBS_VERSION
source deps/from-apt.sh  # PY3_BUILD_DEPS
#source deps/podman.sh
source test/tsv-lib.sh  # tsv-concat
source web/table/html.sh  # table-sort-{begin,end}

# Also in build/dev-shell.sh
USER_WEDGE_DIR=~/wedge/oils-for-unix.org
ROOT_WEDGE_DIR=/wedge/oils-for-unix.org

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

readonly ZSH_VERSION=5.1.1
readonly ZSH_URL="https://www.oilshell.org/blob/spec-bin/zsh-$ZSH_VERSION.tar.xz"

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

  download-to $DEPS_SOURCE_DIR/zsh "$ZSH_URL"
  maybe-extract $DEPS_SOURCE_DIR/zsh "$(basename $ZSH_URL)" zsh-$ZSH_VERSION

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

wedge-exists() {
  ### Does an installed wedge already exist?

  local name=$1
  local version=$2
  local wedge_dir=${3:-/wedge/oils-for-unix.org}

  local installed=$wedge_dir/pkg/$name/$version

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
  python3 -m pip download -d $py_package_dir pexpect
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
  time python3 -m pip install --find-links $package_dir pexpect
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

install-py3-libs() {
  ### Invoked by Dockerfile.cpp-small, etc.
  local mypy_dir=${1:-}

  download-py3-libs "$mypy_dir"
  install-py3-libs-from-cache "$mypy_dir"
}

# zsh notes
  # Fedora compiler error
  # zsh ./configure is NOT detecting 'boolcodes', and then it has a broken
  # fallback in Src/Modules/termcap.c that causes a compile error!  It seems
  # like ncurses-devel should fix this, but it doesn't
  #
  # https://koji.fedoraproject.org/koji/rpminfo?rpmID=36987813
  #
  # from /home/build/oil/_build/deps-source/zsh/zsh-5.1.1/Src/Modules/termcap.c:38:
  # /usr/include/term.h:783:56: note: previous declaration of ‘boolcodes’ with type ‘const char * const[]’
  # 783 | extern NCURSES_EXPORT_VAR(NCURSES_CONST char * const ) boolcodes[];
  #
  # I think the ./configure is out of sync with the actual build?


# TODO:
# - $ROOT_WEDGE_DIR vs. $USER_WEDGE_DIR is duplicating information that's
# already in each WEDGE file

py-wedges() {
  ### for build/py.sh all

  echo cmark $CMARK_VERSION $ROOT_WEDGE_DIR
  echo re2c $RE2C_VERSION $ROOT_WEDGE_DIR
  echo python2 $PY2_VERSION $ROOT_WEDGE_DIR
  echo pyflakes $PYFLAKES_VERSION $USER_WEDGE_DIR
}

cpp-wedges() {
  ### for ninja / mycpp translation

  echo python3 $PY3_VERSION $ROOT_WEDGE_DIR
  echo mypy $MYPY_VERSION $USER_WEDGE_DIR

  # py3-libs has a built time dep on both python3 and MyPy, so we're doing it
  # separately for now
  #echo py3-libs $PY3_LIBS_VERSION $USER_WEDGE_DIR
}

spec-bin-wedges() {
  ### for test/spec-py.sh osh-all

  echo dash $DASH_VERSION $USER_WEDGE_DIR
  echo bash $BASH_VER $USER_WEDGE_DIR
  echo bash $BASH5_VER $USER_WEDGE_DIR
  echo mksh $MKSH_VERSION $USER_WEDGE_DIR
  echo zsh $ZSH_VERSION $USER_WEDGE_DIR
  echo busybox $BUSYBOX_VERSION $USER_WEDGE_DIR
  echo yash $YASH_VERSION $USER_WEDGE_DIR
}

contributor-wedges() {
  py-wedges
  cpp-wedges
  spec-bin-wedges
}

extra-wedges() {
  # Contributors don't need uftrace, bloaty, and probably R-libs
  # Although R-libs could be useful for benchmarks

  # Test both outside the contianer, as well as inside?
  echo uftrace $UFTRACE_VERSION $ROOT_WEDGE_DIR
  echo bloaty $BLOATY_VERSION $ROOT_WEDGE_DIR

  #echo souffle $SOUFFLE_VERSION $USER_WEDGE_DIR
}

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
  local name=$1
  local version=$2
  local wedge_dir=$3  # e.g. $USER_WEDGE_DIR or empty

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

  if wedge-exists "$name" "$version" "$wedge_dir"; then
    echo "CACHED  $(timestamp)  $name $version"
    return
  fi

  local -a cmd=( deps/wedge.sh unboxed _build/deps-source/$name/ $version)

  set +o errexit
  my-time-tsv \
    --field "$XARGS_SLOT" \
    --field "$name" \
    --field "$name-$version.log.txt" \
    --field "$version" \
    --append \
    --output $task_file \
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

readonly WEDGE_LOG_DIR=_build/wedge/logs

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
    "$base_url/base.css"\

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
  local parallel=${1:-}

  mkdir -p _build/wedge/logs

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
  xargs "${flags[@]}" -n 3 --process-slot-var=XARGS_SLOT -- $0 maybe-install-wedge

  #xargs "${flags[@]}" -n 3 --process-slot-var=XARGS_SLOT -- $0 dummy-task-wrapper
}

write-task-report() {
  local tasks_tsv=_build/wedge/logs/tasks.tsv

  python3 devtools/tsv_concat.py $WEDGE_LOG_DIR/*.task.tsv > $tasks_tsv
  log "Wrote $tasks_tsv"

  # TODO: version can be right-justified?
  here-schema-tsv-4col >_build/wedge/logs/tasks.schema.tsv <<EOF
column_name   type      precision strftime
status        integer   0         -
elapsed_secs  float     1         -
user_secs     float     1         -
start_time    float     1         %H:%M:%S
end_time      float     1         %H:%M:%S
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

install-spec-bin-fast() {
  spec-bin-wedges | install-wedge-list T
  write-task-report
}

fake-py3-libs-wedge() {
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
    $0 install-py3-libs >$log_file 2>&1 || true

  echo "  FAKE  $(timestamp)  $name $version"
}

install-wedges() {
  local extra=${1:-}

  # For contributor setup: we need to use this BEFORE running build/py.sh all
  build/py.sh time-helper

  echo " START  $(timestamp)"

  # Do all of them in parallel
  if test -n "$extra"; then
    { contributor-wedges; extra-wedges; } | install-wedge-list T
  else
    contributor-wedges | install-wedge-list T
  fi

  fake-py3-libs-wedge
  echo "   END  $(timestamp)"

  write-task-report
}

install-wedges-soil() {
  install-wedges extra
}

install-wedges-fast() {
  ### Alias for compatibility
  install-wedges "$@"
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

boxed-wedges() {
  #### host _build/wedge/binary -> guest container /wedge or ~/wedge

  #export-podman

  # TODO:
  #
  # - Add equivalents of spec-bin
  # - Use the same manifest as install-wedges
  #   - so then you can delete the _build/wedge dir to re-run it
  #   - use xargs -n 1 so it's done serially

  # - Do these lazily like we do in install-wedges

  # We can test if the dir _build/wedge/binary/oils-for-unix.org/pkg/FOO exists
  # if wedge-exists "$name" "$version" "$wedge_dir"; then
  #  echo "CACHED  $(timestamp)  $name $version"
  #  return
  # fi

  if false; then
    deps/wedge.sh boxed deps/source.medo/time-helper
    deps/wedge.sh boxed deps/source.medo/cmark/
    deps/wedge.sh boxed deps/source.medo/re2c/
    deps/wedge.sh boxed deps/source.medo/python3/
  fi

  if false; then
    deps/wedge.sh boxed deps/source.medo/bloaty/
  fi

  if true; then
    # build with debian-12, because soil-benchmarks2 is, because it has R
    deps/wedge.sh boxed deps/source.medo/uftrace/ '' debian-12
    # python2 needed everywhere
    #deps/wedge.sh boxed deps/source.medo/python2/ '' debian-12

    # TODO: build with debian-12
    # Used in {benchmarks,benchmarks2,other-tests}
    #deps/wedge.sh boxed deps/source.medo/R-libs/ '' debian-12
  fi
}

boxed-spec-bin() {
  if false; then
    deps/wedge.sh boxed deps/source.medo/bash '4.4'
  fi

  if true; then
    deps/wedge.sh boxed deps/source.medo/bash '5.2.21'
  fi

  if true; then
    deps/wedge.sh boxed deps/source.medo/dash
    deps/wedge.sh boxed deps/source.medo/mksh
  fi

  if true; then
    # Note: zsh requires libncursesw5-dev
    deps/wedge.sh boxed deps/source.medo/zsh

    deps/wedge.sh boxed deps/source.medo/busybox

    # Problem with out of tree build, as above.  Skipping for now
    deps/wedge.sh boxed deps/source.medo/yash
    echo
  fi
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

task-five "$@"
