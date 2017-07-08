#!/usr/bin/env bash
#
# Stats about build artifacts.
#
# Usage:
#   ./stats.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: Track these metrics over time.

# hello: 1.41 MB native + 145 KB = 1.56 MB bundle
# oil:   1.65 MB native + 642 KB = 2.30 MB bundle
bundle-size() {
  ls -l _build/*/bytecode.zip _build/*/ovm _bin/*.ovm
}

_tar-lines() {
  local app_name=$1
  find _tmp/$app_name-tar-test -name '*.[ch]' | xargs wc -l | sort -n

  awk '/\.py$/ { print $1 }' \
    _build/runpy-deps-py.txt _build/$app_name/app-deps-py.txt |
  sort | uniq | xargs wc -l | sort -n
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
