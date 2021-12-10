#!/usr/bin/env bash
#
# Usage:
#   ./image-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# Common Helpers
#

download-re2c() {
  mkdir -p _deps
  wget --directory _deps \
    https://github.com/skvadrik/re2c/releases/download/1.0.3/re2c-1.0.3.tar.gz
}

install-re2c() {
  cd _deps
  tar -x -z < re2c-1.0.3.tar.gz
  cd re2c-1.0.3
  ./configure
  make
}

#
# Image definitions: dummy, dev-minimal, other-tests, ovm-tarball, cpp
#

dummy() {
  # gcc: time-helper is needed
  # git: for checking out code
  # python2: for various tools
  apt-get install -y gcc git python2
}

dev-minimal() {
  local -a packages=(
    # common
    git python2

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

dev-minimal-py() {
  # Python 2 packages for linting linting Python 2 code.
  pip install --user flake8 typing

  # Python 3 packages
  # - MyPy requires Python 3
  # - pexpect is for test/interactive.py
  pip3 install --user mypy pexpect
}

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

other-tests-R() {
  readonly R_PATH=~/R  # duplicates what's in test/common.sh

  # Install to a directory that doesn't require root.  This requires setting
  # R_LIBS_USER.  Or library(dplyr, lib.loc = "~/R", but the former is preferable.
  mkdir -p ~/R

  # Note: dplyr 1.0.3 as of January 2021 made these fail on Xenial.  See R 4.0
  # installation below.
  INSTALL_DEST=$R_PATH Rscript -e 'install.packages(c("dplyr", "tidyr", "stringr"), lib=Sys.getenv("INSTALL_DEST"), repos="https://cloud.r-project.org")'
}

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

cpp-source-deps() {
  download-re2c
  install-re2c

  # TODO: Remove these from runtime:
  #
  # mycpp-pip
  # mycpp-git
}

ovm-tarball() {
  local -a packages=(
    # common
    gcc git python2

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

ovm-tarball-source-deps() {
  echo TODO

  # TODO: Move the ln /usr/bin/python here
  #
  # Run it LOCALLY with the tasks that are failing

  # Remove these from runtime:
  #
  # spec-deps
  # tarball-deps
}

"$@"
