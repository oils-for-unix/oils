#!/usr/bin/env bash
#
# Stats about build artifacts.
#
# Usage:
#   ./metrics.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: Track these metrics over time.

# hello: 1.41 MB native + 145 KB = 1.56 MB bundle
# oil:   1.65 MB native + 642 KB = 2.30 MB bundle
bundle-size() {
  ls -l _build/*/bytecode-*.zip _build/*/ovm _bin/*.ovm
}

linecount-nativedeps() {
  local app_name=${1:-oil}
  find _tmp/${app_name}-tar-test -name '*.[ch]' | xargs wc -l | sort -n
}

readonly BYTECODE='bytecode-opy'

linecount-pydeps() {
  local app_name=${1:-oil}

  awk '/\.py$/ { print $1 }' _build/$app_name/${BYTECODE}-manifest.txt |
    sort | uniq | xargs wc -l | sort -n
}

# Print table of [num_bytes pyc path]
pyc-bytes() {
  local app_name=${1:-oil}

  awk '/\.pyc$/ { print $1 }' _build/$app_name/${BYTECODE}-manifest.txt |
    sort | uniq | xargs wc --bytes | sort -n
}

_tar-lines() {
  linecount-nativedeps "$@"
  echo
  linecount-pydeps "$@"
}

# 144.6 K lines of C
# 6.4 K lines Python.
hello-tar-lines() {
  _tar-lines hello
}

# 165.8 K lines of C (biggest: posixmodule.c, unicodeobject.c)
# 30.8 K lines Python (biggest:
oil-tar-lines() {
  _tar-lines oil
}

"$@"
