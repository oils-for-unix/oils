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
declare -a R_BUILD_DEPS=(
    r-base-core  # R interpreter

    # ICU for the R stringi package.  This makes compilation faster; otherwise
    # it tries to compile it from source.
    # https://stringi.gagolewski.com/install.html
    libicu-dev
)

install-R() {
  ### For manual use OUTSIDE container
  apt-install "${R_BUILD_DEPS[@]}"
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

    gcc
    g++  # re2c is C++
    make  # to build re2c

    # for cmark
    cmake

    # cmake -G Ninja can be used
    ninja-build

    # For 'deps/wedge.sh unboxed-install'
    sudo

    # uftrace configure uses pkg-config to find python3 flags
    pkg-config
    # uftrace configure detects with #include "Python.h"
    python3-dev
    # shared library for uftrace to do dlopen()
    # requires path in uftrace source
    libpython3.7

    # Dependencies for building our own Python3 wedge.  Otherwise 'pip install'
    # won't work.
    # TODO: We should move 'pip install' to build time.
    "${PY3_BUILD_DEPS[@]}"

    # For installing R packages
    "${R_BUILD_DEPS[@]}"
  )

  apt-get update

  apt-install "${packages[@]}"
}

layer-python-symlink() {
  ### A special layer for building CPython; done as root
  ln -s -f -v /usr/bin/python2 /usr/bin/python
}

layer-for-soil() {
  # git: for checking out code
  # python2: for various tools

  # TODO: change python2 to python3
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
    g++  # for C++ tarball

    python2-dev
    libreadline-dev
    curl  # wait for cpp-tarball
  )

  apt-install "${packages[@]}"
}

dev-minimal() {
  local -a packages=(
    # TODO: remove
    python2-dev  # for building Python extensions
    python-setuptools  # Python 2, for flake8
    python-pip  # flake8 typing

    gcc  # for building Python extensions
    libreadline-dev

    python3-setuptools  # mypy
    python3-pip
    # 2023-07: somehow this became necessary to pip3 install typed_ast, a MyPy
    # dep, which recently updated to version 1.5.5
    python3-dev

    # Note: osh-minimal task needs shells; testing WITHOUT spec-bin shells
    busybox-static mksh zsh

    gawk

    # 'ps' used by spec tests
    procps
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
    libreadline-dev
    python2-dev  # osh2oil needs build/py.sh minimal

    # Compilers for R.  TODO: try removing after wedge
    gcc g++

    make  # to build py27.grammar.marshal, ugh

    r-base-core
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

    # For 32-bit binaries with -m32
    gcc-multilib
    g++-multilib

    # For some tests
    gawk

    # for MyPy git clone https://.  TODO: remove when the build is hermetic
    ca-certificates

    # for test/ltrace
    ltrace
  )

  apt-install "${packages[@]}"
}

benchmarks() {
  ### For benchmarks

  local -a packages=(
    # for build/py.sh all
    libreadline-dev
    python2-dev

    # To build Oil
    g++
    ninja-build
    make  # to build R packages

    # to create _test/index.html
    gawk

    # for stable benchmarks.  TODO: could move osh-parser cachegrind to benchmarks2
    valgrind

    # benchmarks compare system shells -- they don't use our spec-bin?  In case
    # there are perf bugs caused by the build
    busybox-static mksh zsh

    # retrieving deps like benchmarks/osh-runtime -- TODO: move to build time
    wget
    bzip2  # extracting benchmarks/osh-runtime
    xz-utils

    # For analyzing benchmarks.
    r-base-core

    # pgrep used by test/stateful in interactive task
    # TODO: Could move both Python and C++ to their own image
    # That will be a good use case once we have
    procps
  )

  apt-install "${packages[@]}"
}

benchmarks2() {
  ### uftrace needs a Python plugin

  local -a packages=(
    # for build/py.sh all
    libreadline-dev
    python2-dev

    # To build Oil
    g++
    ninja-build

    # uftrace needs a Python 3 plugin
    # Technically we don't need 'python3' or 'python3.7' -- only the shared
    # lib?
    libpython3.7

    # for stable benchmarks.
    valgrind

    # Analyze uftrace
    r-base-core

    # for MyPy git clone https://.  TODO: remove when the build is hermetic
    ca-certificates
  )

  apt-install "${packages[@]}"
}

cpp-spec() {
  ### For cpp-spec

  local -a packages=(
    # for build/py.sh all
    libreadline-dev
    python2-dev

    # To build Oil
    g++
    ninja-build

    # to create _test/index.html
    gawk

    # spec tests use these
    procps
    jq

    # for MyPy git clone https://.  TODO: remove when the build is hermetic
    ca-certificates
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

    # TODO: probably can remove C++ compiler now that re2c is a wedge
    gcc
    g++

    # for cmark
    cmake
    # to build Python-2.7.13 (could be a wedge)
    make

    xz-utils  # extract e.g. zsh/yash tarballs
    bzip2  # extract e.g. busybox tarball

    # for syscall measurements
    strace

    # used by test/spec-runner.sh
    gawk
  )

  apt-install "${packages[@]}"
}

app-tests() {
  local -a packages=(
    # build/py.sh all
    libreadline-dev
    python2-dev

    # retrieving spec-bin -- TODO: move to build time
    wget
    # for wget https://.  TODO: remove when the build is hermetic
    ca-certificates

    curl  # wait for cpp-tarball

    gcc
    g++  # for C++ tarball

    # to build ble.sh
    make
    # used by ble.sh
    gawk
    procps

    # for ble.sh contra
    libx11-dev
    libxft-dev
    libncursesw5-dev
  )

  apt-install "${packages[@]}"
}

if test $(basename $0) = 'from-apt.sh'; then
  "$@"
fi
