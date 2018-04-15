#!/bin/bash
#
# Test stdlib dependencies
#
# Usage:
#   ./stdlib.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO:
# - Test under CPython (need in-tree build)
# - Under OVM?  How?
# - Under byterun
#   - although I won't use all of every module

# Lib/test/regrtest.py gets ImportError?  How are you supposed to run this?
# - I think the out of tree build is fucking things up?    You need an
# in-tree build?

oil-deps() {
  grep Python _build/oil/opy-app-deps.txt
}

opy-deps() {
  #make _bin/opy.ovm
  grep Python _build/opy/opy-app-deps.txt
  #grep Python _build/opy/app-deps-cpython.txt
}

"$@"
