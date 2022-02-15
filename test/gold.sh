#!/usr/bin/env bash
#
# Run real shell code with osh and bash, and compare the results.
#
# Usage:
#   test/gold.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh  # $OSH, run-all

readonly GOLD_DIR='test/gold'

# Runs an command (argv) the normal way (with its shebang) and then with
# OSH, and compares the stdout and exit code.
#
# Also puts $PWD/bin on the front of $PATH, in order to read bin/readlink
# and so forth.
_compare() {
  set +o errexit

  "$@" >_tmp/shebang.txt
  local expected_status=$?

  export OSH_HIJACK_SHEBANG=$OSH
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

# Uses {core,osh}/*.py
test-count() {
  _compare metrics/source-code.sh for-translation
  _compare metrics/source-code.sh overview
}

# Uses $(cd $(dirname $0) && pwd)
test-spec-file() {
  _compare test/spec.sh builtin-special
}

# Uses redirect of functions.
test-html-summary() {
  # BUG: in the devtools/release.sh process, there's nothing to summarize here
  # because _tmp/spec is deleted.
  _compare test/spec-runner.sh html-summary osh
}

test-gen-module-init() {
  local modules='time datetime'
  _compare build/actions.sh gen-module-init $modules
}

test-wild() {
  _compare test/wild.sh all '^distro/usr-bin'
}

# NOTE: zsh behaves differently under sh and bin/osh!  Looks like it is an
# inherited file descriptor issue.
#
# A bin/osh app bundle also behaves differently.  Maybe because of the internal
# environment variables.
# FAILS

FAIL-test-startup-benchmark() {
  _compare benchmarks/startup.sh compare-strace
}

test-configure() { _compare ./configure; }
test-configure-bug() { _compare $GOLD_DIR/configure-bug.sh; }
test-nix() { _compare $GOLD_DIR/nix.sh isElfSimpleWithStdin; }
test-and-or() { _compare $GOLD_DIR/and-or.sh test-simple; }

test-comments() { _compare $GOLD_DIR/comments.sh; }
test-readonly_() { _compare $GOLD_DIR/readonly.sh; }
test-export-case() { _compare $GOLD_DIR/export.sh; }
test-glob() { _compare $GOLD_DIR/glob.sh; }
test-no-op() { _compare metrics/source-code.sh; }
test-complex-here-docs() { _compare $GOLD_DIR/complex-here-docs.sh; }

# FAILS
FAIL-test-big-here-doc() { _compare $GOLD_DIR/big-here-doc.sh; }

test-case-in-subshell() { _compare $GOLD_DIR/case-in-subshell.sh; }
test-command-sub() { _compare $GOLD_DIR/command-sub.sh; }
test-command-sub-2() { _compare $GOLD_DIR/command-sub-2.sh; }

char-class() { _compare $GOLD_DIR/char-class.sh demo; }
strip-op-char-class() { _compare $GOLD_DIR/strip-op-char-class.sh; }

# Similar tests for backslash escaping.
FAIL-test-echo-e() { _compare $GOLD_DIR/echo-e.sh; }

test-dollar-sq() { _compare $GOLD_DIR/dollar-sq.sh; }
test-word-eval() { _compare $GOLD_DIR/word-eval.sh; }

test-abuild() {
  _compare $GOLD_DIR/abuild.sh is_function is_function
}

# Needs declare -p
FAIL-test-declare() { _compare $GOLD_DIR/declare.sh demo; }

# Needs declare -p
FAIL-test-scope() { _compare $GOLD_DIR/scope.sh; }

FAIL-test-readlink() { $GOLD_DIR/readlink.sh compare; }

test-errexit() { _compare $GOLD_DIR/errexit.sh all; }

# Hm this isn't tickling the bug?
test-errexit-confusion() {
  _compare $GOLD_DIR/errexit-confusion.sh run-for-release-OLD
  _compare $GOLD_DIR/errexit-confusion.sh run-for-release-FIXED
}

test-parse-help() {
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

FAIL-test-ostype() {
  _compare $0 _ostype
}

# TODO:
# - Add --allowed-failures mechanism
#   - and maybe a timeout
#
# Does it make sense to have some sort of TAP-like test protocol?
# - Probably not when it's one test cases per process
# - But spec/ and spec/stateful have multiple test cases per file

manifest() {
  compgen -A function | egrep '^test-' 
}

all-passing() {
  manifest | xargs --verbose -- $0 run-all
}

# TODO: Turn it into a table?
run-for-release() {
  run-other-suite-for-release gold all-passing
}

"$@"
