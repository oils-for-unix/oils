#!/usr/bin/env bash
#
# Run ble.sh unit tests in Travis.
#
# Usage:
#   test/ble.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_clone/ble.sh

clone() {
  local out=$BASE_DIR
  mkdir -p $out
  git clone --recursive --depth=50 --branch=osh \
    https://github.com/akinomyoga/ble.sh $out
  git clone --depth=50 \
    https://github.com/akinomyoga/contra.git "$out"/ext/contra.src
}

# TODO: What version of osh
build() {
  make  # make osh

  # make _bin/osh
  devtools/bin.sh make-ovm-links

  # make ble.sh
  cd $BASE_DIR
  make

  # make contra for test
  cd ext/contra.src
  make
  cp src/contra ..
}

# https://superuser.com/questions/380772/removing-ansi-color-codes-from-text-stream
filter-ansi() {
  sed 's/\x1b\[[0-9;]*m//g'
}

run-tests() {
  cd $BASE_DIR

  #wc -l out/ble.osh
  #wc -l lib/test-*.sh

  # Force interactive shell on Travis, but remove color.
  ../../_bin/osh out/ble.osh --test | filter-ansi

  echo DONE
}

"$@"
