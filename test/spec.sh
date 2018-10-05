#!/usr/bin/env bash
#
# Usage:
#   test/spec.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# For now, fall back to the shell in $PATH.
shell-path() {
  local name=$1
  if test -f _tmp/spec-bin/$name; then
    echo _tmp/spec-bin/$name
  else
    which $name
  fi
}

readonly DASH=$(shell-path dash)
readonly BASH=$(shell-path bash)
readonly MKSH=$(shell-path mksh)
readonly ZSH=$(shell-path zsh)

if test -f _tmp/spec-bin/ash; then
  readonly BUSYBOX_ASH=_tmp/spec-bin/ash
else
  readonly BUSYBOX_ASH=_tmp/shells/ash
fi

# Usage: callers can override OSH_LIST to test on more than one version.
#
# Example:
# OSH_LIST='bin/osh _bin/osh' test/spec.sh all

readonly OSH_CPYTHON='bin/osh'
readonly OSH_OVM=${OSH_OVM:-_bin/osh}

OSH_LIST=${OSH_LIST:-}  # A space-separated list.

if test -z "$OSH_LIST"; then
  if test -e $OSH_OVM; then
    # TODO: Does it make sense to copy the binary to an unrelated to directory,
    # like /tmp?  /tmp/{oil.ovm,osh}.
    OSH_LIST="$OSH_CPYTHON $OSH_OVM"
  else
    OSH_LIST="$OSH_CPYTHON"
  fi
fi


# ash and dash are similar, so not including ash by default.  zsh is not quite
# POSIX.
readonly REF_SHELLS=($DASH $BASH $MKSH)

#
# Setup (TODO: Delete this once test/spec-bin.sh binaries are deployed)
#

link-busybox-ash() {
  mkdir -p $(dirname $BUSYBOX_ASH)
  ln -s -f --verbose "$(which busybox)" $BUSYBOX_ASH
}

# dash and bash should be there by default on Ubuntu.
install-shells() {
  sudo apt-get install busybox-static mksh zsh
  link-busybox-ash
}

# TODO: Maybe do this before running all tests.
check-shells() {
  for sh in "${REF_SHELLS[@]}" $ZSH $OSH_LIST; do
    test -e $sh || { echo "ERROR: $sh does not exist"; break; }
    test -x $sh || { echo "ERROR: $sh isn't executable"; break; }
  done
}

maybe-show() {
  local path=$1
  if test -e $path; then
    echo "--- $path ---"
    cat $path
    echo
  fi
}

version-text() {
  date-and-git-info

  for bin in $OSH_LIST; do
    echo ---
    echo "\$ $bin --version"
    $bin --version
    echo
  done

  echo ---
  $BASH --version | head -n 1
  ls -l $BASH
  echo

  echo ---
  $ZSH --version | head -n 1
  ls -l $ZSH
  echo

  # No -v or -V or --version.  TODO: Only use hermetic version on release.

  echo ---
  local my_dash=_tmp/spec-bin/dash
  if test -f $my_dash; then
    ls -l $my_dash
  else
    dpkg -s dash | egrep '^Package|Version'
  fi
  echo

  echo ---
  local my_mksh=_tmp/spec-bin/mksh
  if test -f $my_mksh; then
    ls -l $my_mksh
  else
    dpkg -s mksh | egrep '^Package|Version'
  fi
  echo

  echo ---
  local my_busybox=_tmp/spec-bin/busybox-1.22.0/busybox
  if test -f $my_busybox; then
    { $my_busybox || true; } | head -n 1
    ls -l $my_busybox
  else
    # Need || true because of pipefail
    { busybox || true; } | head -n 1
  fi
  echo

  maybe-show /etc/debian_version
  maybe-show /etc/lsb-release
}

#
# Helpers
#

sh-spec() {
  local test_file=$1
  shift

  if [[ $test_file != *.test.sh ]]; then
    die "Test file should end with .test.sh"
  fi

  local this_dir=$(cd $(dirname $0) && pwd)

  local tmp_env=$this_dir/../_tmp/spec-tmp/$(basename $test_file)
  mkdir -p $tmp_env

  test/sh_spec.py \
      --tmp-env $tmp_env \
      --path-env "$this_dir/../spec/bin:$PATH" \
      "$test_file" \
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
  python -m trace --trackcalls -C $out \
    test/sh_spec.py spec/var-sub.test.sh $DASH $BASH "$@"

  ls -l $out
  head $out/*.cover
}

#
# Run All tests
#

all() {
  test/spec-runner.sh all-parallel "$@"
}


#
# Invidual tests.
#
# We configure the shells they run on and the number of allowed failures (to
# prevent regressions.)
#

smoke() {
  sh-spec spec/smoke.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

osh-only() {
  sh-spec spec/osh-only.test.sh $OSH_LIST "$@"
}

# Regress bugs
bugs() {
  sh-spec spec/bugs.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

blog1() {
  sh-spec spec/blog1.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

blog2() {
  sh-spec spec/blog2.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

blog-other1() {
  sh-spec spec/blog-other1.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

alias() {
  sh-spec spec/alias.test.sh --osh-failures-allowed 6 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

comments() {
  sh-spec spec/comments.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

word-split() {
  sh-spec spec/word-split.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

word-eval() {
  sh-spec spec/word-eval.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

assign() {
  sh-spec spec/assign.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@" 
}

background() {
  sh-spec spec/background.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@" 
}

subshell() {
  sh-spec spec/subshell.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@" 
}

quote() {
  sh-spec spec/quote.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

loop() {
  sh-spec spec/loop.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

case_() {
  sh-spec spec/case_.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

if_() {
  sh-spec spec/if_.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtins() {
  sh-spec spec/builtins.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

builtin-eval-source() {
  sh-spec spec/builtin-eval-source.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-io() {
  sh-spec spec/builtin-io.test.sh \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

builtin-printf() {
  sh-spec spec/builtin-printf.test.sh $BASH $OSH_LIST "$@"
}

builtins2() {
  sh-spec spec/builtins2.test.sh ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

# dash and mksh don't implement 'dirs'
builtin-dirs() {
  sh-spec spec/builtin-dirs.test.sh $BASH $ZSH $OSH_LIST "$@"
}

builtin-vars() {
  sh-spec spec/builtin-vars.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

builtin-getopts() {
  sh-spec spec/builtin-getopts.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

builtin-test() {
  sh-spec spec/builtin-test.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

builtin-trap() {
  sh-spec spec/builtin-trap.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

# Bash implements type -t, but no other shell does.  For Nix.
# zsh/mksh/dash don't have the 'help' builtin.
builtin-bash() {
  sh-spec spec/builtin-bash.test.sh $BASH $OSH_LIST "$@"
}

# This is bash/OSH only
builtin-completion() {
  sh-spec spec/builtin-completion.test.sh --osh-failures-allowed 1 \
    $BASH $OSH_LIST "$@"
}

builtins-special() {
  sh-spec spec/builtins-special.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

command-parsing() {
  sh-spec spec/command-parsing.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

func-parsing() {
  sh-spec spec/func-parsing.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

func() {
  sh-spec spec/func.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

glob() {
  sh-spec spec/glob.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

arith() {
  sh-spec spec/arith.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

command-sub() {
  sh-spec spec/command-sub.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

command_() {
  sh-spec spec/command_.test.sh ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

pipeline() {
  sh-spec spec/pipeline.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

explore-parsing() {
  sh-spec spec/explore-parsing.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

parse-errors() {
  sh-spec spec/parse-errors.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

here-doc() {
  # NOTE: The last two tests, 31 and 32, have different behavior on my Ubuntu
  # and Debian machines.
  # - On Ubuntu, read_from_fd.py fails with Errno 9 -- bad file descriptor.
  # - On Debian, the whole process hangs.
  # Is this due to Python 3.2 vs 3.4?  Either way osh doesn't implement the
  # functionality, so it's probably best to just implement it.
  sh-spec spec/here-doc.test.sh --range 0-31 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

redirect() {
  sh-spec spec/redirect.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

posix() {
  sh-spec spec/posix.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

special-vars() {
  sh-spec spec/special-vars.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

# dash/mksh don't implement this.
introspect() {
  sh-spec spec/introspect.test.sh --osh-failures-allowed 1 \
    $BASH $OSH_LIST "$@"
}

# DONE -- pysh is the most conformant!
tilde() {
  sh-spec spec/tilde.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-op-test() {
  sh-spec spec/var-op-test.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-op-other() {
  sh-spec spec/var-op-other.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

var-op-strip() {
  sh-spec spec/var-op-strip.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

var-sub() {
  # NOTE: ZSH has interesting behavior, like echo hi > "$@" can write to TWO
  # FILES!  But ultimately we don't really care, so I disabled it.
  sh-spec spec/var-sub.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-num() {
  sh-spec spec/var-num.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-sub-quote() {
  sh-spec spec/var-sub-quote.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

sh-options() {
  sh-spec spec/sh-options.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

xtrace() {
  sh-spec spec/xtrace.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

strict-options() {
  sh-spec spec/strict-options.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

errexit() {
  sh-spec spec/errexit.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

errexit-strict() {
  sh-spec spec/errexit-strict.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

# 
# Non-POSIX extensions: arrays, brace expansion, [[, ((, etc.
#

# There as many non-POSIX arithmetic contexts.
arith-context() {
  sh-spec spec/arith-context.test.sh --osh-failures-allowed 1 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

array() {
  sh-spec spec/array.test.sh --osh-failures-allowed 3 \
    $BASH $MKSH $OSH_LIST "$@"
}

array-compat() {
  sh-spec spec/array-compat.test.sh --osh-failures-allowed 4 \
    $BASH $MKSH $OSH_LIST "$@"
}

type-compat() {
  sh-spec spec/type-compat.test.sh $BASH "$@"
}

# += is not POSIX and not in dash.
append() {
  sh-spec spec/append.test.sh --osh-failures-allowed 2 \
    $BASH $MKSH $OSH_LIST "$@" 
}

# associative array -- mksh and zsh implement different associative arrays.
assoc() {
  sh-spec spec/assoc.test.sh --osh-failures-allowed 11 \
    $BASH $OSH_LIST "$@"
}

# ZSH also has associative arrays
assoc-zsh() {
  sh-spec spec/assoc-zsh.test.sh $ZSH "$@"
}

# NOTE: zsh passes about half and fails about half.  It supports a subset of [[
# I guess.
dbracket() {
  sh-spec spec/dbracket.test.sh --osh-failures-allowed 1 \
    $BASH $MKSH $OSH_LIST "$@"
  #sh-spec spec/dbracket.test.sh $BASH $MKSH $OSH_LIST $ZSH "$@"
}

dparen() {
  sh-spec spec/dparen.test.sh \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

brace-expansion() {
  # TODO for osh: implement num ranges, mark char ranges unimplemented?
  sh-spec spec/brace-expansion.test.sh --osh-failures-allowed 12 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

regex() {
  sh-spec spec/regex.test.sh --osh-failures-allowed 3 \
    $BASH $ZSH $OSH_LIST "$@"
}

process-sub() {
  # mksh and dash don't support it
  sh-spec spec/process-sub.test.sh \
    $BASH $ZSH $OSH_LIST "$@"
}

# This does file globbing
extended-glob() {
  # Do NOT use dash here.  Lack of brace sub means it leaves bad files on the
  # file system.
  sh-spec spec/extended-glob.test.sh $BASH $MKSH $OSH_LIST "$@"
}

# This does string matching.
extglob-match() {
  sh-spec spec/extglob-match.test.sh $BASH $MKSH $OSH_LIST "$@"
}

# ${!var} syntax -- oil should replace this with associative arrays.
var-ref() {
  sh-spec spec/var-ref.test.sh --osh-failures-allowed 6 \
    $BASH $MKSH $OSH_LIST "$@"
}

let() {
  sh-spec spec/let.test.sh $BASH $MKSH $ZSH "$@"
}

for-expr() {
  sh-spec spec/for-expr.test.sh \
    $BASH $ZSH $OSH_LIST "$@"
}

empty-bodies() {
  sh-spec spec/empty-bodies.test.sh "${REF_SHELLS[@]}" $ZSH $OSH_LIST "$@"
}

# TODO: This is for the ANTLR grammars, in the oil-sketch repo.
# osh has infinite loop?
shell-grammar() {
  sh-spec spec/shell-grammar.test.sh $BASH $MKSH $ZSH "$@"
}

"$@"
