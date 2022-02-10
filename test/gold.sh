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

readonly GOLD_DIR='test/gold'

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

  $OSH "$@" >_tmp/osh.txt
  local osh_status=$?

  set -o errexit

  #md5sum _tmp/shebang.txt _tmp/osh.txt

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
  # BUG: in the devtools/release.sh process, there's nothing to summarize here
  # because _tmp/spec is deleted.
  _compare test/spec-runner.sh html-summary osh
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
configure-bug() { _compare $GOLD_DIR/configure-bug.sh; }
nix() { _compare $GOLD_DIR/nix.sh isElfSimpleWithStdin; }
and-or() { _compare $GOLD_DIR/and-or.sh test-simple; }

comments() { _compare $GOLD_DIR/comments.sh; }
readonly_() { _compare $GOLD_DIR/readonly.sh; }
export-case() { _compare $GOLD_DIR/export.sh; }
glob() { _compare $GOLD_DIR/glob.sh; }
no-op() { _compare metrics/source-code.sh; }
complex-here-docs() { _compare $GOLD_DIR/complex-here-docs.sh; }
big-here-doc() { _compare $GOLD_DIR/big-here-doc.sh; }
case-in-subshell() { _compare $GOLD_DIR/case-in-subshell.sh; }
command-sub() { _compare $GOLD_DIR/command-sub.sh; }
command-sub-2() { _compare $GOLD_DIR/command-sub-2.sh; }

char-class() { _compare $GOLD_DIR/char-class.sh demo; }
strip-op-char-class() { _compare $GOLD_DIR/strip-op-char-class.sh; }

# Similar tests for backslash escaping.
echo-e() { _compare $GOLD_DIR/echo-e.sh; }
dollar-sq() { _compare $GOLD_DIR/dollar-sq.sh; }
word-eval() { _compare $GOLD_DIR/word-eval.sh; }

abuild() {
  _compare $GOLD_DIR/abuild.sh is_function is_function
}

# Needs declare -p
declare() { _compare $GOLD_DIR/declare.sh demo; }

# Needs declare -p
scope() { _compare $GOLD_DIR/scope.sh; }

readlink-case() {
  $GOLD_DIR/readlink.sh compare
}

# Hm this isn't tickling the bug?
errexit-confusion() {
  _compare $GOLD_DIR/errexit-confusion.sh run-for-release-OLD
  _compare $GOLD_DIR/errexit-confusion.sh run-for-release-FIXED
}

parse-help() {
  local dir=benchmarks/parse-help

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

  # BUG IN OSH!
  # big-here-doc

  case-in-subshell
  command-sub
  command-sub-2

  echo-e
  dollar-sq
  word-eval

  char-class
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
