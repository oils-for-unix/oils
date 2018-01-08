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
    exit 1
  fi

  if test $left_status != $right_status; then
    echo "FAIL: Got status $right_status but expected $left_status"
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


# Not implemented in osh.
dollar-sq() { _compare gold/dollar-sq.sh; }

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
  strip-op-char-class

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
  for t in "${PASSING[@]}"; do
    # fail calls 'exit 1'
    $t
    echo "OK  $t"
  done

  echo
  echo "All gold tests passed."
}

run-for-release() {
  local out_dir=_tmp/gold
  mkdir -p $out_dir

  all-passing | tee $out_dir/log.txt

  echo "Wrote $out_dir/log.txt"
}

"$@"
