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

source test/common.sh  # for $OSH

_compare() {
  set +o errexit

  "$@" >_tmp/shebang.txt
  local expected_status=$?

  $OSH "$@" >_tmp/osh.txt
  local osh_status=$?

  set -o errexit

  if ! diff -u _tmp/shebang.txt _tmp/osh.txt; then
    echo FAIL
    exit 1
  fi

  if test $expected_status != $osh_status; then
    echo "FAIL: Got status $osh_status but expected $expected_status"
    exit 1
  fi

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

gen-module-init() {
  local modules='time datetime'
  _compare build/actions.sh gen-module-init $modules
}

wild() {
  _compare test/wild.sh all '^distro/usr-bin'
}

# NOTE: zsh behaves differently under sh and bin/osh!  Looks like it is an
# inherited file descriptor issue.
#
# A bin/osh app bundle also behaves differently.  Maybe because of the internal
# environment variables.
startup-benchmark() {
  _compare benchmarks/startup.sh compare-strace
}

configure() { _compare ./configure; }
nix() { _compare gold/nix.sh isElfSimpleWithStdin; }
and-or() { _compare gold/and-or.sh test-simple; }

comments() { _compare gold/comments.sh; }
readonly_() { _compare gold/readonly.sh; }
export() { _compare gold/export.sh; }
glob() { _compare gold/glob.sh; }
no-op() { _compare scripts/count.sh; }
complex-here-docs() { _compare gold/complex-here-docs.sh; }

strip-op-char-class() { _compare gold/strip-op-char-class.sh; }

# Similar tests for backslash escaping.
echo-e() { _compare gold/echo-e.sh; }
dollar-sq() { _compare gold/dollar-sq.sh; }
word-eval() { _compare gold/word-eval.sh; }

abuild() {
  _compare gold/abuild.sh is_function is_function
}

# Needs declare -p
declare() { _compare gold/declare.sh demo; }

# Needs declare -p
scope() { _compare gold/scope.sh; }


readonly -a PASSING=(
  # FLAKY: This one differs by timestamp
  #version-text

  configure
  nix
  and-or

  comments
  readonly_
  export
  glob
  no-op
  complex-here-docs

  echo-e
  dollar-sq
  word-eval

  strip-op-char-class
  abuild

  count
  one-spec-test
  html-summary
  gen-module-init

  # This one takes a little long, but it's realistic.
  #wild

  # There are slight differences in the number of syscalls reported.  Not sure
  # of the cause.
  #startup-benchmark
)

all-passing() {
  run-all "${PASSING[@]}"
}

run-for-release() {
  local out_dir=_tmp/gold
  mkdir -p $out_dir

  all-passing | tee $out_dir/log.txt

  echo "Wrote $out_dir/log.txt"
}

"$@"
