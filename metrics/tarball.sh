#!/usr/bin/env bash
#
# Stats about build artifacts.
#
# Usage:
#   ./metrics.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_banner() {
  echo
  echo "$@"
  echo
}

_cloc-header() {
  _banner 'SIGNIFICANT LINES OF CODE'
}

_wc-header() {
  _banner 'PHYSICAL LINES OF CODE'
}

_native-deps() {
  local app_name=${1:-oil}
  find _tmp/${app_name}-tar-test -type f -a -name '*.[ch]'
}

linecount-nativedeps() {
  _cloc-header
  _native-deps | xargs cloc
  echo

  _wc-header
  _native-deps | xargs wc -l | sort -n
}

readonly BYTECODE='bytecode-opy'

_py-deps() {
  local app_name=${1:-oil}
  awk '/\.py$/ { print $1 }' _build/$app_name/${BYTECODE}-manifest.txt
}

linecount-pydeps() {
  _cloc-header
  _py-deps | xargs cloc
  echo

  _wc-header
  _py-deps | sort | uniq | xargs wc -l | sort -n
}

# hello: 1.41 MB native + 145 KB = 1.56 MB bundle
# oil:   1.65 MB native + 642 KB = 2.30 MB bundle
bundle-size() {
  ls -l _build/*/bytecode-*.zip _build/*/ovm _bin/*.ovm
}

pyc-files() {
  local app_name=${1:-oil}
  awk '/\.pyc$/ { print $1 }' _build/$app_name/${BYTECODE}-manifest.txt
}

# Print table of [md5 pyc path]
pyc-md5() {
  pyc-files "$@" | xargs bin/opyc dis-md5
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
