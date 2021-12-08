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

    gawk
    libreadline-dev
    python2-dev 

    python-pip  # flake8 typing
    python3-setuptools  # mypy
    python3-pip

    # Note: osh-minimal task needs shells; not using spec-bin for now
    busybox-static mksh zsh
  )

  apt-get install -y "${packages[@]}"

}

dev-minimal-py() {
  pip install --user flake8 typing

  # MyPy requires Python 3, but Oil requires Python 2.
  pip3 install --user mypy
}

"$@"
