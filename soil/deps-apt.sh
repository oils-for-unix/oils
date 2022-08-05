#!/usr/bin/env bash
#
# Usage:
#   soil/deps-apt.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# These are needed for bootstrapping pip in Python 3.10
# (Also used by build/dev.sh ubuntu-deps)
#
# For building Python 3.10 with working 'pip install'
#   libssl-dev: to download packages
#   libffi-dev: for working setuptools
#   zlib1g-dev: needed for 'import zlib'
declare -a PY3_DEPS=(libssl-dev libffi-dev zlib1g-dev)

layer-python-symlink() {
  ### A special layer for building CPython; done as root
  ln -s -f -v /usr/bin/python2 /usr/bin/python
}

layer-for-soil() {
  # gcc: time-helper is needed
  # git: for checking out code
  # python2: for various tools
  apt-get install -y gcc git python2
}

layer-locales() {
  apt-get install -y locales
  # uncomment in a file
  sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen
  locale-gen --purge en_US.UTF-8
}

dev-minimal() {
  local -a packages=(
    libreadline-dev
    procps  # pgrep used by test/interactive
    gawk

    python2-dev  # for building Python extensions

    python-pip  # flake8 typing
    python3-setuptools  # mypy
    python3-pip

    # Note: osh-minimal task needs shells; not using spec-bin for now
    busybox-static mksh zsh

    # for oil-spec task
    jq
  )

  apt-get install -y "${packages[@]}"

}

pea() {
  # For installing MyPy
  apt-get install -y python3-pip
}

test-image() {
  ### Minimal build with custom Python 3

  apt-get install -y build-essential "${PY3_DEPS[@]}"
}

other-tests() {
  local -a packages=(
    libreadline-dev
    python2-dev  # osh2oil needs build/dev.sh minimal

    python3  # for py3-parse

    r-base-core  # for r-libs
  )

  apt-get install -y "${packages[@]}"
}

cpp() {
  ### For both cpp-small and cpp-spec

  local -a packages=(
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

    ninja-build
    # to create _test/index.html
    gawk

    # for stable benchmarks
    valgrind
    # the shell benchmarks compare shells
    busybox-static mksh zsh
  )

  apt-get install -y "${packages[@]}"
}

clang() {
  ### For both cpp-small and cpp-spec

  local -a packages=(
    # retrieving deps -- TODO: move to build time
    wget

    build-essential
    xz-utils  # to extract Clang

    # build/dev.sh minimal is necessary to run tests?
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

if test $(basename $0) = 'deps-apt.sh'; then
  "$@"
fi
