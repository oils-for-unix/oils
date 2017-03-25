#!/bin/bash
#
# Run real shell code with osh and bash, and compare the results.
#
# Usage:
#   ./gold-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_compare() {
  "$@" >_tmp/left.txt || true
  bin/osh "$@" >_tmp/right.txt || true
  if diff -u _tmp/left.txt _tmp/right.txt; then
    echo PASS
  else
    echo FAIL
  fi
}

# Uses
# - { busybox || true; } | head
# - $1
version-text() {
  _compare ./spec.sh version-text
}

# Uses {core,osh}/*.py
count() {
  _compare ./count.sh all
  _compare ./count.sh parser
  _compare ./count.sh parser-port
  _compare ./count.sh runtime
}

# Uses $(cd $(dirname $0) && pwd)
one-spec-test() {
  _compare ./spec.sh builtins-special
}

# Fails because of redirect of function stdout!
# Oh because it should be run in a  separate process?
html-summary() {
  _compare ./spec-runner.sh html-summary
}

# Fails because 'time' can't find _parse-many!  Gah it needs to be a builtin.
wild() {
  _compare ./wild.sh parse-j
}

"$@"
