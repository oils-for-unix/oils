#!/bin/bash
#
# Usage:
#   ./spec-file.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly DASH=/bin/dash
readonly BASH=/bin/bash
readonly MKSH=/bin/mksh
readonly ZSH=/usr/bin/zsh  # Ubuntu puts it here
readonly BUSYBOX_ASH=_tmp/shells/ash 

readonly OSH=bin/osh

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

#
# Misc
#

# Really what I want is enter(func) and exit(func), and filter by regex?
trace-var-sub() {
  local out=_tmp/coverage
  mkdir -p $out

  # This creates *.cover files, with line counts.
  #python -m trace --count -C $out \

  # This prints trace with line numbers to stdout.
  #python -m trace --trace -C $out \
  python3 -m trace --trackcalls -C $out \
    ./sh_spec.py tests/var-sub.test.sh $DASH $BASH "$@"

  ls -l $out
  head $out/*.cover
}

#
# Run tests
#

# TODO:
# - Be consistent about order of shells.  Might want to use an ARRAY here 
# - make tests run on the maximal set of shells
# - maybe output summary of each shell
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
  ref-shells tests/loop.test.sh $OSH "$@"
}

# Not implemented in osh at all.  Need glob matching of words.
case_() {
  ref-shells tests/case_.test.sh $OSH "$@"
}

if_() {
  ref-shells tests/if_.test.sh $ZSH $OSH "$@"
}

# NOTE: osh uses external test!  But that's OK for now.
test-builtin() {
  ref-shells tests/test-builtin.test.sh $OSH "$@"
}

builtins() {
  ref-shells tests/builtins.test.sh $OSH "$@"
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

explore-parsing() {
  ref-shells tests/explore-parsing.test.sh $OSH "$@"
}

here-doc() {
  ref-shells tests/here-doc.test.sh $OSH "$@"
}

# Need to handle all kinds of redirects
redirect() {
  # BUG: osh treats stdin as stdout!  Fix this.
  ref-shells tests/redirect.test.sh $OSH "$@"
}

posix() {
  ref-shells tests/posix.test.sh $OSH "$@"
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
assoc-zsh() {
  sh-spec tests/assoc-zsh.test.sh $ZSH "$@"
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
  ref-shells tests/var-sub.test.sh $ZSH $OSH "$@"
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

# TODO: This is for the ANTLR grammars, in the oil-sketch repo.
# osh has infinite loop?
shell-grammar() {
  sh-spec tests/shell-grammar.test.sh $BASH $MKSH $ZSH "$@"
}

"$@"
