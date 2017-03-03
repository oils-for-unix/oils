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

# ash and dash are similar, so not including ash by default.  zsh is not quite
# POSIX.
readonly REF_SHELLS=($DASH $BASH $MKSH)

#
# Setup
#

# dash and bash should be there by default on Ubuntu.
install-shells() {
  # NOTE: gawk is used by spec-runner.sh for the special match() function.
  sudo apt-get install busybox-static mksh zsh gawk
  mkdir -p _tmp/shells
  ln -s -f --verbose /bin/busybox $BUSYBOX_ASH
}

version-text() {
  # TODO: Only use Python 3
  python --version
  echo

  python3 --version
  echo

  $BASH --version | head -n 1
  echo

  $ZSH --version | head -n 1
  echo

  # These don't have versions
  dpkg -s dash | egrep '^Package|Version'
  echo

  dpkg -s mksh | egrep '^Package|Version'
  echo

  busybox | head -n 1
  echo

  cat /etc/lsb-release
  echo
}

#
# Helpers
#

sh-spec() {
  local this_dir=$(cd $(dirname $0) && pwd)

  local tmp_env=$this_dir/_tmp/spec-tmp
  mkdir -p $tmp_env

  ./sh_spec.py \
      --tmp-env $tmp_env \
      --path-env "$this_dir/tests/bin:$PATH" \
      "$@"
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
# Run All tests
#

all() {
  ./spec-runner.sh all-parallel "$@"
}


#
# Invidual tests.
#
# We configure the shells they run on and the number of allowed failures (to
# prevent regressions.)
#

smoke() {
  sh-spec tests/smoke.test.sh ${REF_SHELLS[@]} $OSH "$@"
}

# Regress bugs
bugs() {
  sh-spec tests/bugs.test.sh ${REF_SHELLS[@]} $OSH "$@"
}

# Regress bugs
blog1() {
  sh-spec tests/blog1.test.sh --osh-failures-allowed 6 \
    ${REF_SHELLS[@]} $ZSH $OSH "$@"
}

comments() {
  sh-spec tests/comments.test.sh ${REF_SHELLS[@]} $OSH "$@"
}

# TODO(pysh): Implement ${foo:-a b c}
word-split() {
  sh-spec tests/word-split.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH "$@"
}

# 'do' -- detected statically as syntax error?  hm.
assign() {
  sh-spec tests/assign.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $OSH "$@" 
}

# Need to fix $ tokens, and $''
quote() {
  sh-spec tests/quote.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH "$@"
}

loop() {
  sh-spec tests/loop.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH "$@"
}

# Not implemented in osh at all.  Need glob matching of words.
case_() {
  sh-spec tests/case_.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $OSH "$@"
}

if_() {
  sh-spec tests/if_.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $OSH "$@"
}

# NOTE: osh uses external test!  But that's OK for now.
test-builtin() {
  sh-spec tests/test-builtin.test.sh ${REF_SHELLS[@]} $OSH "$@"
}

builtins() {
  sh-spec tests/builtins.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH "$@"
}

func() {
  sh-spec tests/func.test.sh ${REF_SHELLS[@]} $OSH "$@"
}

glob() {
  sh-spec tests/glob.test.sh ${REF_SHELLS[@]} --osh-failures-allowed 6 \
    $BUSYBOX_ASH $OSH "$@"
}

arith() {
  sh-spec tests/arith.test.sh --osh-failures-allowed 9 \
    ${REF_SHELLS[@]} $ZSH $OSH "$@"
}

# pysh failures: case not implemented
command-sub() {
  sh-spec tests/command-sub.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH "$@"
}

pipeline() {
  sh-spec tests/pipeline.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH "$@"
}

explore-parsing() {
  sh-spec tests/explore-parsing.test.sh --osh-failures-allowed 6 \
    ${REF_SHELLS[@]} $OSH "$@"
}

here-doc() {
  # NOTE: The last two tests, 28 and 29, have different behavior on my Ubuntu
  # and Debian machines.
  # - On Ubuntu, read_from_fd.py fails with Errno 9 -- bad file descriptor.
  # - On Debian, the whole process hangs.
  # Is this due to Python 3.2 vs 3.4?  Either way osh doesn't implement the
  # functionality, so it's probably best to just implement it.
  sh-spec tests/here-doc.test.sh --osh-failures-allowed 10 --range 1-27 \
    ${REF_SHELLS[@]} $OSH "$@"
}

redirect() {
  # BUG: osh treats stdin as stdout!  Fix this.
  sh-spec tests/redirect.test.sh --osh-failures-allowed 12 \
    ${REF_SHELLS[@]} $OSH "$@"
}

posix() {
  sh-spec tests/posix.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $OSH "$@"
}

# DONE -- pysh is the most conformant!
tilde() {
  sh-spec tests/tilde.test.sh ${REF_SHELLS[@]} $OSH "$@"
}

var-sub() {
  # NOTE: ZSH has interesting behavior, like echo hi > "$@" can write to TWO
  # FILES!  But ultimately we don't really care, so I disabled it.
  sh-spec tests/var-sub.test.sh --osh-failures-allowed 23 \
    ${REF_SHELLS[@]} $OSH "$@"
}

var-sub-quote() {
  sh-spec tests/var-sub-quote.test.sh --osh-failures-allowed 11 \
    ${REF_SHELLS[@]} $OSH "$@"
}


# 
# Non-POSIX extensions: arrays, brace expansion, [[, ((, etc.
#

# There as many non-POSIX arithmetic contexts.
arith-context() {
  sh-spec tests/arith-context.test.sh --osh-failures-allowed 10 \
    $BASH $MKSH $ZSH $OSH "$@"
}

# TODO: array= (a b c) vs array=(a b c).  I think LookAheadForOp might still be
# messed up.
array() {
  sh-spec tests/array.test.sh --osh-failures-allowed 31 \
    $BASH $MKSH $OSH "$@"
}

# += is not POSIX and not in dash.
append() {
  sh-spec tests/append.test.sh $BASH $MKSH "$@" 
}

# associative array -- mksh implements different associative arrays.
assoc() {
  sh-spec tests/assoc.test.sh $BASH "$@"
}

# ZSH also has associative arrays, which means we probably need them
assoc-zsh() {
  sh-spec tests/assoc-zsh.test.sh $ZSH "$@"
}

# NOTE: zsh passes about half and fails about half.  It supports a subset of [[
# I guess.
dbracket() {
  sh-spec tests/dbracket.test.sh --osh-failures-allowed 7 \
    $BASH $MKSH $OSH "$@"
  #sh-spec tests/dbracket.test.sh $BASH $MKSH $OSH $ZSH "$@"
}

dparen() {
  sh-spec tests/dparen.test.sh --osh-failures-allowed 4 \
    $BASH $MKSH $ZSH $OSH "$@"
}

brace-expansion() {
  # NOTE: being a korn shell, mksh has brace expansion.  But dash doesn't!
  sh-spec tests/brace-expansion.test.sh $BASH $MKSH "$@"
}

regex() {
  sh-spec tests/regex.test.sh $BASH $ZSH "$@"
}

process-sub() {
  # mksh and dash don't support it
  sh-spec tests/process-sub.test.sh --osh-failures-allowed 1 \
    $BASH $ZSH $OSH "$@"
}

extended-glob() {
  # Do NOT use dash here.  Brace sub breaks things.
  sh-spec tests/extended-glob.test.sh $BASH $MKSH "$@"
}

# ${!var} syntax -- oil should replace this with associative arrays.
var-ref() {
  sh-spec tests/var-ref.test.sh $BASH $MKSH "$@"
}

let() {
  sh-spec tests/let.test.sh $BASH $MKSH $ZSH "$@"
}

for-expr() {
  sh-spec tests/for-expr.test.sh --osh-failures-allowed 2 \
    $MKSH $BASH $OSH "$@"
}

# TODO: This is for the ANTLR grammars, in the oil-sketch repo.
# osh has infinite loop?
shell-grammar() {
  sh-spec tests/shell-grammar.test.sh $BASH $MKSH $ZSH "$@"
}

"$@"
