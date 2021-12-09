#!/usr/bin/env bash
#
# Usage:
#   ./image-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

dummy() {
  # gcc: time-helper is needed
  # git: for checking out code
  # python2: for various tools
  apt-get install -y gcc git python2
}

dev-minimal() {
  local -a packages=(
    # common
    git
    python2

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
    git
    python2

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

"$@"
