#!/usr/bin/env bash
#
# Run real shell code with osh and bash, and compare the results.
#
# Limitation: If a script shells out to another bash script, osh won't be run.
# TODO: --hijack-shebang or just 'sed' all the scripts in a repo?
#
# Usage:
#   ./gold-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

_compare() {
  set +o errexit

  "$@" >_tmp/left.txt
  local left_status=$?

  bin/osh "$@" >_tmp/right.txt
  local right_status=$?

  set -o errexit

  if ! diff -u _tmp/left.txt _tmp/right.txt; then
    echo FAIL
    return 1
  fi

  if test $left_status != $right_status; then
    echo "FAIL: Got status $right_status but expected $left_status"
    return 1
  fi

  echo PASS
  return 0
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

configure() {
  _compare ./configure
}

no-op() {
  _compare scripts/count.sh
}

gen-module-init() {
  local modules='time datetime'
  _compare build/actions.sh gen-module-init $modules
}

wild() {
  _compare test/wild.sh parse-usr-bin
}

# NOTE: zsh behaves differently under sh and bin/osh!  Looks like it is an
# inherited file descriptor issue.
#
# A bin/osh app bundle also behaves differently.  Maybe because of the internal
# environment variables.
startup-benchmark() {
  _compare benchmarks/startup.sh compare-strace
}

03-glob() {
  _compare spec/03-glob.sh
}

all() {
  version-text
  count
  one-spec-test
  html-summary
  configure
  no-op
  gen-module-init
  wild
  startup-benchmark
  03-glob
}

"$@"
