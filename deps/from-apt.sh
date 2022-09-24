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
declare -a PY3_DEPS=(libssl-dev libffi-dev zlib1g-dev)

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

layer-python-symlink() {
  ### A special layer for building CPython; done as root
  ln -s -f -v /usr/bin/python2 /usr/bin/python
}

layer-for-soil() {
  # gcc: time-helper is needed.  TODO: remove this dependency
  # git: for checking out code
  # python2: for various tools
  apt-install gcc git python2
}

layer-common() {
  # with RUN --mount=type=cache

  # Can't install packages in Debian without this
  apt-get update  # uses /var/lib/apt

  layer-for-soil  # uses /var/cache/apt
}

layer-locales() {
  apt-get install -y locales
  # uncomment in a file
  sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
  locale-gen --purge en_US.UTF-8
}

test-image() {
  ### For testing builds, not run on CI

  apt-install build-essential "${PY3_DEPS[@]}"
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
  apt-install python3-pip
}

other-tests() {
  local -a packages=(
    # Includes C++ compiler.  This popped up with --no-install-recommends
    build-essential

    libreadline-dev
    python2-dev  # osh2oil needs build/py.sh minimal

    make  # to build py27.grammar.marshal, ugh

    python3  # for py3-parse

    r-base-core  # for r-libs

    # ICU for R stringi package.  This makes compilation faster; otherwise it
    # tries to compile it from source.
    # https://stringi.gagolewski.com/install.html
    libicu-dev
  )

  apt-install "${packages[@]}"
}

cpp() {
  ### For both cpp-small and cpp-spec

  local -a packages=(
    build-essential

    # retrieving deps -- TODO: move to build time
    wget

    # line_input.so needs this
    libreadline-dev
    python2-dev

    # for type checking with MyPy binary
    python3
    python3-pip  # TODO: remove
    python3-venv  # TODO: remove

    # for custom Python 3
    "${PY3_DEPS[@]}"

    # To build bloaty
    # TODO: should we use multi-stage builds?
    cmake
    bzip2  # to extract bloaty

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
    "${PY3_DEPS[@]}"
  )

  apt-get install -y "${packages[@]}"
}

ovm-tarball() {
  local -a packages=(
    # spec tests need the 'time' command, not the shell builtin
    time

    # This is a separate package needed for re2c.  TODO: remove when we've
    # built it into the image.
    g++

    # line_input.so needs this
    libreadline-dev
    python2-dev

    # retrieving deps -- TODO: move to build time
    wget
    # for syscall measurements
    strace

    # for cmark and yajl
    cmake

    # test/spec-runner.sh needs this
    gawk
  )

  apt-get install -y "${packages[@]}"
}

if test $(basename $0) = 'from-apt.sh'; then
  "$@"
fi
