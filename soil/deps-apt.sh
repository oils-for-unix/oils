#!/usr/bin/env bash
#
# Usage:
#   ./deps-apt.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

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
  )

  apt-get install -y "${packages[@]}"

}

# TODO: use layer-for-soil
other-tests() {
  local -a packages=(
    # common
    git python2

    libreadline-dev
    python2-dev  # osh2oil needs build/dev.sh minimal

    python3  # for py3-parse

    r-base-core  # for r-libs
  )

  apt-get install -y "${packages[@]}"
}

# TODO: use layer-for-soil
cpp() {
  local -a packages=(
    # common
    git python2

    # retrieving deps -- TODO: move to build time
    wget

    # line_input.so needs this
    libreadline-dev
    python2-dev

    python3-pip
    # for MyPy virtualenv for requirements.txt -- TODO: move to build time.
    python3-venv

    ninja-build
    # to create mycpp/_ninja/index.html
    gawk

    # for stable benchmarks
    valgrind
    # the shell benchmarks compare shells
    busybox-static mksh zsh
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

"$@"
