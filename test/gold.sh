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
  _compare test/spec.sh version-text
}

# Uses {core,osh}/*.py
count() {
  _compare scripts/count.sh all
  _compare scripts/count.sh parser
  _compare scripts/count.sh parser-port
  _compare scripts/count.sh runtime
}

# Uses $(cd $(dirname $0) && pwd)
one-spec-test() {
  _compare test/spec.sh builtins-special
}

# Uses redirect of functions.
html-summary() {
  _compare test/spec-runner.sh html-summary
}

# Fails because 'time' can't find _parse-many!  Gah it needs to be a builtin.
wild() {
  _compare test/wild.sh parse-j
}

all() {
  version-text
  count
  one-spec-test
  html-summary
}

"$@"
