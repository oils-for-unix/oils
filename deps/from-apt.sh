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
    gawk

    procps  # pgrep used by test/stateful

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
    # TODO: try g++
    build-essential

    libreadline-dev
    python2-dev  # osh2oil needs build/py.sh minimal

    make  # to build py27.grammar.marshal, ugh

    # TODO: Try removing
    # for py3-parse -- is this obsolete?
    python3

    "${R_DEPS[@]}"
  )

  apt-install "${packages[@]}"
}

cpp-small() {
  local -a packages=(
    # for build/py.sh all
    libreadline-dev
    python2-dev

    # To compile Oil
    g++
    ninja-build

    # For some tests
    gawk

    # for MyPy git clone https://.  TODO: remove when the build is hermetic
    ca-certificates
  )

  apt-install "${packages[@]}"
}

cpp() {
  ### For cpp-spec, benchmarks

  local -a packages=(
    # for build/py.sh all
    libreadline-dev
    python2-dev

    # build-essential is for building Debian packages, which we're not really
    # doing.
    # TODO: try 'g++' package
    build-essential

    # For benchmarks only
    "${R_DEPS[@]}"

    # To build Oil
    ninja-build
    # to create _test/index.html
    gawk

    # for stable benchmarks
    valgrind

    # benchmarks compare system shells -- they don't use our spec-bin?  In case
    # there are perf bugs caused by the build
    busybox-static mksh zsh

    # Can remove some of these

    # Keep system Python for awhile, e.g. for
    python3
    python3-pip  # for pexpect

    # retrieving deps like benchmarks/osh-runtime -- TODO: move to build time
    wget

    # for custom Python 3
    # I think we should have a working pip3 ?
    # "${PY3_BUILD_DEPS[@]}"
  )

  apt-install "${packages[@]}"
}

clang() {
  ### For cpp-coverage

  local -a packages=(
    # For build/py.sh minimal
    libreadline-dev
    python2-dev

    # Compile Oils
    g++
    ninja-build

    xz-utils  # to extract Clang

    # for MyPy git clone https://.  TODO: remove when the build is hermetic
    ca-certificates
  )

  apt-install "${packages[@]}"
}

ovm-tarball() {
  local -a packages=(
    # build/py.sh all
    libreadline-dev
    python2-dev

    # retrieving spec-bin -- TODO: move to build time
    wget
    # for wget https://.  TODO: remove when the build is hermetic
    ca-certificates

    # when spec tests use 'time', dash falls back on 'time' command
    'time'

    # This is a separate package needed for re2c.  TODO: remove when we've
    # built it into the image.
    g++
    # for cmark and yajl
    cmake
    # needed to build CPython
    make

    xz-utils  # extract e.g. zsh/yash tarballs
    bzip2  # extract e.g. busybox tarball

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
