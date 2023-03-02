#!/usr/bin/env bash
#
# Script for contributors to quickly set up:
#
# - re2c
# - re2c
#
# Usage:
#   build/deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

fetch() {
  # _build/deps-source/
  #   re2c/
  #     WEDGE
  #     re2c-3.0/  expanded

  echo 'Hello from deps.sh'

  # TODO:
  #
  # wget --no-clobber
  # tar -x -z < on all the tar files

}

install() {

  # Note: not specifying versions
  # The versions go with the repo

  deps/wedge.sh unboxed-build _build/deps-source/re2c/
  deps/wedge.sh unboxed-build _build/deps-source/cmark/
  deps/wedge.sh unboxed-build _build/deps-source/python3/
}

"$@"
