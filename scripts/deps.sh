#!/bin/bash
#
# Find dependencies of shell scripts in this repo.
# This is a good set of repos for oilshell.org/src.
#
# Usage:
#   ./deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_this-repo() {
  # NOTE: copied from test/wild.sh oil-manifest.
  for name in \
    configure install *.sh {benchmarks,build,test,scripts,opy}/*.sh; do
    bin/oilc deps $name
  done
}

# Top:
# mkdir, cat, xargs, basename, wc.
#
# There are some errors due to separate modules too, like csv2html, fail, etc.

this-repo() {
  local tmp=_tmp/this-repo-deps.txt
  _this-repo > $tmp
  sort $tmp | uniq -c | sort -n
}

"$@"
