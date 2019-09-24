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
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh  # for $OSH

# Runs an command (argv) the normal way (with its shebang) and then with
# OSH, and compares the stdout and exit code.
#
# Also puts $PWD/bin on the front of $PATH, in order to read bin/readlink
# and so forth.
_compare() {
  set +o errexit

  # NOTE: This will be wrong with OSH_HIJACK_SHEBANG!

  "$@" >_tmp/shebang.txt
  local expected_status=$?

  PATH="$PWD/bin:$PATH" $OSH "$@" >_tmp/osh.txt
  local osh_status=$?

  set -o errexit

  if ! diff -u _tmp/shebang.txt _tmp/osh.txt; then
    echo FAIL
    exit 1
  fi

  if test $expected_status != $osh_status; then
    echo "FAIL: Got status $osh_status but expected $expected_status"
    echo "in test case: $@"
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
  _compare metrics/source-code.sh all
}

# Uses $(cd $(dirname $0) && pwd)
one-spec-test() {
  _compare test/spec.sh builtin-special
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
configure-bug() { _compare gold/configure-bug.sh; }
nix() { _compare gold/nix.sh isElfSimpleWithStdin; }
and-or() { _compare gold/and-or.sh test-simple; }

comments() { _compare gold/comments.sh; }
readonly_() { _compare gold/readonly.sh; }
export-case() { _compare gold/export.sh; }
glob() { _compare gold/glob.sh; }
no-op() { _compare metrics/source-code.sh; }
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

readlink-case() {
  gold/readlink.sh compare
}

# Hm this isn't tickling the bug?
errexit-confusion() {
  _compare gold/errexit-confusion.sh run-for-release-OLD
  _compare gold/errexit-confusion.sh run-for-release-FIXED
}

parse-help() {
  local dir=testdata/parse-help

  # This is not hermetic since it calls 'ls'
  _compare $dir/excerpt.sh _parse_help ls
}

# Gah, bash gets this from compile-time configuration generated with autoconf,
# not uname().  It looks like 'linux-gnu' on Ubuntu.  In Alpine, it's
# 'linux-musl'.
_ostype() {
  echo $OSTYPE
}

ostype() {
  _compare $0 _ostype
}

readonly -a PASSING=(
  # FLAKY: This one differs by timestamp
  #version-text

  configure
  configure-bug
  nix
  and-or

  comments
  readonly_
  export-case
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
  readlink-case

  errexit-confusion

  parse-help

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
  run-other-suite-for-release gold all-passing
}

"$@"
