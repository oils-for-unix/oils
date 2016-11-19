#!/bin/bash
#
# Run tests against multiple shells with the sh_spec framework.
#
# Usage:
#   ./spec.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly DASH=/bin/dash
readonly BASH=/bin/bash
readonly MKSH=/bin/mksh
readonly ZSH=/usr/bin/zsh  # Ubuntu puts it here
readonly BUSYBOX_ASH=_tmp/shells/ash 

readonly OSH=bin/osh

# dash and bash should be there by default on Ubuntu
install-shells() {
  sudo apt-get install busybox-static mksh zsh 
}

setup() {
  mkdir -p _tmp/shells
  ln -s -f --verbose /bin/busybox $BUSYBOX_ASH
}

#
# Helpers
#

sh-spec() {
  ./sh_spec.py "$@"
}

# ash and dash are similar, so not including it by default.
readonly REF_SHELLS=($DASH $BASH $MKSH)

ref-shells() {
  local test_script=$1
  shift
  sh-spec $test_script "${REF_SHELLS[@]}" "$@"
}

_run() {
  local name=$1
  echo 
  echo "--- Running '$name'"
  echo

  if ! "$@"; then
    echo
    echo "*** $name FAILED"
    echo
    return 1
  fi
}

#
# Tests
#

# This should be kept green.  Run before each commit.
# TODO: Put more tests here, maybe run in parallel.
osh() {
  _run smoke || true
  _run comments
}

# TODO: Fix all of these!
all() {
  _run smoke || true
  _run comments
  _run word-split || true
  _run assign || true
  _run append
  _run quote
  _run loop
  _run case_
  _run test-builtin
  _run builtins
  _run func
  _run glob
  _run extended-glob
  _run arith
  _run arith-context
  _run command-sub
  _run process-sub
  _run pipeline
  _run explore-parsing
  _run here-doc
  _run redirect
  _run posix
  _run tilde
  _run array
  _run assoc
  _run brace-expansion
  _run dbracket 
  _run dparen
  _run regex
  _run var-sub
  _run var-sub-quote
  _run var-ref
  _run for-let
}

# TODO:
# - Be consistent about order of shells.  Might want to use an ARRAY here 
# - make tests run on the maximal set of shells
# - maybe output summary of each shell
# - summary over ALL tests?  Does test_sh.py need a CSV output or something?
# - need a "nonzero" status

smoke() {
  sh-spec tests/smoke.test.sh $DASH $BASH $OSH "$@"
}

# Regress bugs
bugs() {
  sh-spec tests/bugs.test.sh $DASH $BASH $OSH "$@"
}

# Regress bugs
blog1() {
  sh-spec tests/blog1.test.sh $DASH $BASH $MKSH $ZSH "$@"
}

comments() {
  sh-spec tests/comments.test.sh $DASH $BASH $MKSH $OSH "$@"
}

# TODO(pysh): Implement ${foo:-a b c}
word-split() {
  sh-spec tests/word-split.test.sh $DASH $BASH $MKSH $OSH "$@"
}

# 'do' -- detected statically as syntax error?  hm.
assign() {
  ref-shells tests/assign.test.sh $OSH "$@" 
}

append() {
  sh-spec tests/append.test.sh $BASH $MKSH "$@" 
}

# Need to fix $ tokens, and $''
quote() {
  sh-spec tests/quote.test.sh $DASH $BASH $MKSH $OSH "$@"
}

loop() {
  ref-shells tests/loop.test.sh "$@"
}

case_() {
  ref-shells tests/case.test.sh "$@"
}

test-builtin() {
  ref-shells tests/test-builtin.test.sh "$@"
}

builtins() {
  ref-shells tests/builtins.test.sh "$@"
}

func() {
  ref-shells tests/func.test.sh $OSH "$@"
}

# pysh failures: because of Python glob library
glob() {
  sh-spec tests/glob.test.sh $DASH $BASH $MKSH $BUSYBOX_ASH $OSH "$@"
}

extended-glob() {
  # Do NOT use dash here.  Brace sub breaks things.
  sh-spec tests/extended-glob.test.sh $BASH $MKSH "$@"
}

arith() {
  ref-shells tests/arith.test.sh $ZSH $OSH "$@"
}

arith-context() {
  sh-spec tests/arith-context.test.sh $BASH $MKSH $ZSH $OSH "$@"
}

# pysh failures: case not implemented
command-sub() {
  ref-shells tests/command-sub.test.sh $OSH "$@"
}

process-sub() {
  # mksh and dash don't support it
  sh-spec tests/process-sub.test.sh $BASH $ZSH $OSH "$@"
}

pipeline() {
  ref-shells tests/pipeline.test.sh $ZSH $OSH "$@"
}

# TODO: pysh has infinite loop 
explore-parsing() {
  ref-shells tests/explore-parsing.test.sh "$@"
  #ref-shells tests/explore-parsing.test.sh $OSH "$@"
}

# TODO(pysh): Multiple here docs?
here-doc() {
  ref-shells tests/here-doc.test.sh "$@"
}

# Need to handle all kinds of redirects
redirect() {
  #ref-shells tests/redirect.test.sh $OSH "$@"
  ref-shells tests/redirect.test.sh "$@"
}

posix() {
  ref-shells tests/posix.test.sh "$@"
}

# DONE -- pysh is the most conformant!
tilde() {
  ref-shells tests/tilde.test.sh $OSH "$@"
}

# 
# Non-POSIX extensions: arrays, brace expansion, and [[.
#

# TODO: array= (a b c) vs array=(a b c).  I think LookAheadForOp might still be
# messed up.
array() {
  sh-spec tests/array.test.sh $BASH $MKSH $OSH "$@"
}

# associative array
assoc() {
  sh-spec tests/assoc.test.sh $BASH $MKSH "$@"
}

# ZSH also has associative arrays, which means we probably need them
zsh-assoc() {
  sh-spec tests/zsh-assoc.test.sh $ZSH "$@"
}

brace-expansion() {
  # NOTE: being a korn shell, mksh has brace expansion.  But dash doesn't!
  sh-spec tests/brace-expansion.test.sh $BASH $MKSH "$@"
}

# NOTE: zsh passes about half and fails about half.  It supports a subset of [[
# I guess.
dbracket() {
  sh-spec tests/dbracket.test.sh $BASH $MKSH $OSH "$@"
  #sh-spec tests/dbracket.test.sh $BASH $MKSH $OSH $ZSH "$@"
}

dparen() {
  sh-spec tests/dparen.test.sh $BASH $MKSH $ZSH $OSH "$@"
}

regex() {
  sh-spec tests/regex.test.sh $BASH $ZSH "$@"
}

var-sub() {
  ref-shells tests/var-sub.test.sh $ZSH "$@"
}

var-sub-quote() {
  ref-shells tests/var-sub-quote.test.sh $OSH "$@"
}

var-ref() {
  sh-spec tests/var-ref.test.sh $BASH $MKSH "$@"
}

for-let() {
  sh-spec tests/for-let.test.sh $BASH $MKSH $ZSH "$@"
}

# Really what I want is enter(func) and exit(func), and filter by regex?
trace-var-sub() {
  local out=_tmp/coverage
  mkdir -p $out

  # This creates *.cover files, with line counts.
  #python -m trace --count -C $out \

  # This prints trace with line numbers to stdout.
  #python -m trace --trace -C $out \
  python -m trace --trackcalls -C $out \
    sh-spec tests/var-sub.test.sh $DASH $BASH "$@"

  ls -l $out
  head $out/*.cover
}

"$@"
