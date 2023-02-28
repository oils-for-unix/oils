#!/usr/bin/env bash
#
# Usage:
#   deps/from-apt.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# These are needed for bootstrapping pip in Python 3.10
# (Also used by build/py.sh ubuntu-deps)
#
# For building Python 3.10 with working 'pip install'
#   libssl-dev: to download packages
#   libffi-dev: for working setuptools
#   zlib1g-dev: needed for 'import zlib'
declare -a PY3_BUILD_DEPS=(libssl-dev libffi-dev zlib1g-dev)

# for deps/from-R.sh
declare -a R_DEPS=(
    r-base-core  # R interpreter

    # ICU for the R stringi package.  This makes compilation faster; otherwise
    # it tries to compile it from source.
    # https://stringi.gagolewski.com/install.html
    libicu-dev
)

install-R() {
  ### For manual use OUTSIDE container
  apt-install "${R_DEPS[@]}"
}

# https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md#run---mounttypecache

# TODO: Use this for ALL images
apt-install() {
  ### Helper to slim down images

  apt-get install -y --no-install-recommends "$@"
}

init-deb-cache() {
  rm -f /etc/apt/apt.conf.d/docker-clean
  echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
}

layer-wedge-builder() {
  local -a packages=(
    # xz-utils  # do we need this for extraction?

    build-essential  # build re2c in C++
    make  # to build re2c

    # for cmark and yajl
    cmake

    # For 'deps/wedge.sh unboxed-install'
    sudo

    # Make sure Python3 wedge works.
    # Dockerfile.{cpp,pea,..} need runtime deps if they do pip3 install
    "${PY3_BUILD_DEPS[@]}"
  )

  apt-get update

  apt-install "${packages[@]}"
}

layer-python-symlink() {
  ### A special layer for building CPython; done as root
  ln -s -f -v /usr/bin/python2 /usr/bin/python
}

layer-for-soil() {
  # gcc: time-helper is needed.  TODO: remove this dependency
  # git: for checking out code
  # python2: for various tools
  apt-install git python2
}

layer-common() {
  # with RUN --mount=type=cache

  # Can't install packages in Debian without this
  apt-get update  # uses /var/lib/apt

  layer-for-soil  # uses /var/cache/apt
}

layer-locales() {
  apt-install locales
  # uncomment in a file
  sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
  locale-gen --purge en_US.UTF-8
}

test-image() {
  ### For testing builds, not run on CI

  apt-install build-essential "${PY3_BUILD_DEPS[@]}"
}

wild() {
  # for build/py.sh all
  local -a packages=(
    gcc  # 'cc' for compiling Python extensions
    python2-dev
    libreadline-dev
  )

  apt-install "${packages[@]}"
}

dev-minimal() {
  local -a packages=(
    # Shouldn't require a C++ compiler in build-essential?  Only gcc?

    libreadline-dev
    procps  # pgrep used by test/interactive
    gawk

    python2-dev  # for building Python extensions
    python-setuptools  # Python 2, for flake8

    python-pip  # flake8 typing
    python3-setuptools  # mypy
    python3-pip

    # Note: osh-minimal task needs shells; not using spec-bin for now
    busybox-static mksh zsh

    # for oil-spec task
    jq
  )

  apt-install "${packages[@]}"
}

pea() {
  # For installing MyPy
  # apt-install python3-pip

  echo 'None'
}

other-tests() {
  local -a packages=(
    # Includes C++ compiler.  This popped up with --no-install-recommends
    build-essential

    libreadline-dev
    python2-dev  # osh2oil needs build/py.sh minimal

    make  # to build py27.grammar.marshal, ugh

    # for py3-parse -- is this obsolete?
    python3

    "${R_DEPS[@]}"
  )

  apt-install "${packages[@]}"
}

cpp() {
  ### For both cpp-small and cpp-spec

  local -a packages=(
    # for build/py.sh all
    libreadline-dev
    python2-dev

    build-essential

    # retrieving deps like benchmarks/osh-runtime -- TODO: move to build time
    wget

    # for type checking with MyPy binary
    python3
    python3-pip  # for pexpect

    # for custom Python 3
    # I think we should have a working pip3 ?
    # "${PY3_BUILD_DEPS[@]}"

    "${R_DEPS[@]}"

    # To build Oil
    ninja-build
    # to create _test/index.html
    gawk

    # for stable benchmarks
    valgrind
    # the shell benchmarks compare shells
    busybox-static mksh zsh
  )

  apt-install "${packages[@]}"
}

clang() {
  ### For cpp-coverage

  local -a packages=(
    # retrieving deps -- TODO: move to build time
    wget

    build-essential
    xz-utils  # to extract Clang

    # build/py.sh minimal is necessary to run tests?
    libreadline-dev
    python2-dev

    ninja-build

    # for type checking with MyPy binary
    python3
    python3-pip  # TODO: try removing
    python3-venv  # TODO: try removing

    # for custom Python 3
    "${PY3_BUILD_DEPS[@]}"
  )

  apt-install "${packages[@]}"
}

ovm-tarball() {
  local -a packages=(
    # retrieving deps -- TODO: move to build time
    wget
    # for wget https://.  TODO: remove when the build is hermetic
    ca-certificates

    # spec tests need the 'time' command, not the shell builtin
    'time'

    # This is a separate package needed for re2c.  TODO: remove when we've
    # built it into the image.
    g++
    # for cmark and yajl
    cmake
    # needed to build cmark (although we could use Ninja)
    make

    xz-utils  # extract e.g. re2c tarball
    bzip2  # extract e.g. busybox tarball

    # line_input.so needs this
    libreadline-dev
    python2-dev

    # for syscall measurements
    strace

    # test/spec-runner.sh needs this
    gawk
  )

  apt-install "${packages[@]}"
}

if test $(basename $0) = 'from-apt.sh'; then
  "$@"
fi
