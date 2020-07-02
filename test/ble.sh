#!/bin/bash
#
# Run ble.sh unit tests in Travis.
#
# Usage:
#   ./ble.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_clone/ble.sh

clone() {
  local out=$BASE_DIR
  mkdir -p $out
  git clone --recursive --depth=50 --branch=osh \
    https://github.com/akinomyoga/ble.sh $out
}

# TODO: What version of osh
build() {
  make  # make osh

  # make _bin/osh
  devtools/bin.sh make-bin-links

  # make ble.sh
  cd $BASE_DIR
  make
}

run-tests() {
  cd $BASE_DIR

  #wc -l oshrc.test-util
  #wc -l out/ble.osh
  #wc -l lib/test-util.sh

  # Force interactive shell on Travis.
  ../../_bin/osh -i --rcfile oshrc.test-util

  echo DONE
}

travis() {
  clone
  build
  run-tests
}

"$@"
