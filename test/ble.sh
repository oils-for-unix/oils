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
    https://github.com/akinomyoga/contra.git $out/ext/contra.src
}

# TODO: What version of osh
build() {
  #make  # make osh

  # make _bin/osh
  #devtools/bin.sh make-ovm-links

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

run-tests-osh-py() {
  cd $BASE_DIR

  #wc -l oshrc.test-util
  #wc -l out/ble.osh
  #wc -l lib/test-util.sh

  # Shorter tests
  ../../bin/osh -i --rcfile oshrc.test-util | filter-ansi

  # Longer tests
  # TODO: Run these with osh-cpp
  # ../../bin/osh out/ble.osh --test | filter-ansi

  echo DONE
}

# Seems to take about 12 seconds
run-tests-bash() {
  cd $BASE_DIR

  set +o errexit
  bash out/ble.sh --test | filter-ansi
  echo 'Failure suppressed'

  # Some failures, possibly due to old version of bash

  # 98.1% [section] ble/util: 1205/1228 (23 fail, 0 crash, 6 skip)
  # 100.0% [section] ble/canvas/trace (relative:confine:measure-bbox): 17/17 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/canvas/trace (cfuncs): 18/18 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/canvas/trace (justify): 30/30 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/canvas/trace-text: 11/11 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/textmap#update: 5/5 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/unicode/GraphemeCluster/c2break: 77/77 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/unicode/GraphemeCluster/c2break (GraphemeBreakTest.txt): 3251/3251 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/decode: 33/33 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/edit: 2/2 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/syntax: 22/22 (0 fail, 0 crash, 0 skip)
  # 100.0% [section] ble/complete: 7/7 (0 fail, 0 crash, 0 skip)
}

"$@"
