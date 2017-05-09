#!/bin/bash

set -o nounset
set -o pipefail
set -o errexit

readonly CLANG_DIR=~/install/clang+llvm-4.0.0-x86_64-linux-gnu-ubuntu-14.04
readonly CLANG=$CLANG_DIR/bin/clang

readonly CLANG_COV_FLAGS='-fprofile-instr-generate -fcoverage-mapping'
readonly CLANG_LINK_FLAGS=''

readonly PY27=Python-2.7.13
