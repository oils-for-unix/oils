#!/usr/bin/env bash
#
# Usage:
#   test/spec.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh
source test/spec-common.sh

if test -z "${IN_NIX_SHELL:-}"; then
  source build/dev-shell.sh  # to run 'dash', etc.
fi

REPO_ROOT=$(cd $(dirname $0)/.. ; pwd)
readonly REPO_ROOT

# TODO: Get rid of this indirection.
readonly DASH=dash
readonly BASH=bash
readonly MKSH=mksh
readonly ZSH=zsh
readonly BUSYBOX_ASH=ash

# Usage: callers can override OSH_LIST to test on more than one version.
#
# Example:
# OSH_LIST='bin/osh _bin/osh' test/spec.sh all

readonly OSH_CPYTHON="$REPO_ROOT/bin/osh"
readonly OSH_OVM=${OSH_OVM:-$REPO_ROOT/_bin/osh}

OSH_LIST=${OSH_LIST:-}  # A space-separated list.

if test -z "$OSH_LIST"; then
  # By default, run with both, unless $OSH_OVM isn't available.
  if test -e $OSH_OVM; then
    # TODO: Does it make sense to copy the binary to an unrelated to directory,
    # like /tmp?  /tmp/{oil.ovm,osh}.
    OSH_LIST="$OSH_CPYTHON $OSH_OVM"
  else
    OSH_LIST="$OSH_CPYTHON"
  fi
fi

readonly OIL_CPYTHON="$REPO_ROOT/bin/oil"
readonly OIL_OVM=${OIL_OVM:-$REPO_ROOT/_bin/oil}

OIL_LIST=${OIL_LIST:-}  # A space-separated list.

if test -z "$OIL_LIST"; then
  # By default, run with both, unless $OIL_OVM isn't available.
  if test -e $OIL_OVM; then
    OIL_LIST="$OIL_CPYTHON $OIL_OVM"
  else
    OIL_LIST="$OIL_CPYTHON"
  fi
fi

# ash and dash are similar, so not including ash by default.  zsh is not quite
# POSIX.
readonly REF_SHELLS=($DASH $BASH $MKSH)

#
# Setup (TODO: Delete this once test/spec-bin.sh binaries are deployed)
#

link-busybox-ash() {
  ### Non-hermetic ash only used for benchmarks / Soil dev-minimal

  # Could delete this at some point
  mkdir -p _tmp/shells
  ln -s -f --verbose "$(which busybox)" _tmp/shells/ash
}

# dash and bash should be there by default on Ubuntu.
install-shells-with-apt() {
  ### Non-hermetic shells; test/spec-bin.sh replaces this for most purposes

  set -x  # show what needs sudo
  sudo apt install busybox-static mksh zsh
  set +x
  link-busybox-ash
}

maybe-show() {
  local path=$1
  if test -f $path; then
    echo "--- $path ---"
    cat $path
    echo
  fi
}

oil-version-text() {
  date-and-git-info

  for bin in $OIL_LIST; do
    echo ---
    echo "\$ $bin --version"
    $bin --version
    echo
  done

  maybe-show /etc/alpine-release
  maybe-show /etc/debian_version
  maybe-show /etc/lsb-release
}

tea-version-text() {
  oil-version-text
}

# This has to be in test/spec because it uses $OSH_LIST, etc.
osh-version-text() {
  date-and-git-info

  for bin in $OSH_LIST; do
    echo ---
    echo "\$ $bin --version"
    $bin --version
    echo
  done

  # $BASH and $ZSH should exist

  echo ---
  bash --version | head -n 1
  ls -l $(type -p bash)
  echo

  echo ---
  zsh --version | head -n 1
  ls -l $(type -p zsh)
  echo

  # No -v or -V or --version.  TODO: Only use hermetic version on release.

  echo ---
  local my_dash
  my_dash=$(type -p dash)
  if test -f $my_dash; then
    ls -l $my_dash
  else
    dpkg -s dash | egrep '^Package|Version'
  fi
  echo

  echo ---
  local my_mksh
  my_mksh=$(type -p mksh)
  if test -f $my_mksh; then
    ls -l $my_mksh
  else
    dpkg -s mksh | egrep '^Package|Version'
  fi
  echo

  echo ---
  local my_busybox
  my_busybox=$(type -p busybox)
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
  maybe-show /etc/alpine-release
}

osh-minimal-version-text() {
  osh-version-text
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
  PYTHONPATH=. python -m trace --trackcalls -C $out \
    test/sh_spec.py spec/var-sub.test.sh $DASH $BASH "$@"

  ls -l $out
  head $out/*.cover
}

#
# Run All tests
#

osh-all() {
  check-survey-shells

  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel osh compare-py survey
}

oil-all() {
  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel oil compare-py oil-language
}

tea-all() {
  # $suite $compare_mode $spec_subdir
  test/spec-runner.sh all-parallel tea compare-py tea-language
}

check-survey-shells() {
  ### Make sure bash, zsh, OSH, etc. exist

  # Note: yash isn't here, but it is used in a couple tests

  test/spec-runner.sh shell-sanity-check "${REF_SHELLS[@]}" $ZSH $BUSYBOX_ASH $OSH_LIST
}

osh-minimal() {
  ### Some tests that work on the minimal build.  Run by Soil.

  # depends on link-busybox-ash, then source dev-shell.sh at the top of this
  # file
  check-survey-shells

  # oil-json: for testing yajl
  cat >_tmp/spec/SUITE-osh-minimal.txt <<EOF
smoke
oil-json
interactive
EOF
# this fails because the 'help' builtin doesn't have its data
# builtin-bash

  # suite compare_mode spec_subdir
  MAX_PROCS=1 test/spec-runner.sh all-parallel osh-minimal compare-py survey
}

osh-all-serial() { MAX_PROCS=1 $0 osh-all "$@"; }
oil-all-serial() { MAX_PROCS=1 $0 oil-all "$@"; }
tea-all-serial() { MAX_PROCS=1 $0 tea-all "$@"; }

soil-run-osh() {
  osh-all-serial
}


# Usage: test/spec.sh dbg smoke, dbg-all
dbg() {
  OSH_LIST='_bin/osh-dbg' $0 "$@"
}

# For completion
dbg-all() {
  $0 dbg all
}

#
# Individual tests.
#
# We configure the shells they run on and the number of allowed failures (to
# prevent regressions.)
#

smoke() {
  sh-spec spec/smoke.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

interactive() {
  sh-spec spec/interactive.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

prompt() {
  sh-spec spec/prompt.test.sh --osh-failures-allowed 0 \
    $BASH $OSH_LIST "$@"
}

osh-only() {
  sh-spec spec/osh-only.test.sh --osh-failures-allowed 0  \
    $OSH_LIST "$@"
}

# Regress bugs
bugs() {
  sh-spec spec/bugs.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

TODO-deprecate() {
  sh-spec spec/TODO-deprecate.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
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
  sh-spec spec/alias.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

comments() {
  sh-spec spec/comments.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

word-split() {
  sh-spec spec/word-split.test.sh --osh-failures-allowed 7 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

word-eval() {
  sh-spec spec/word-eval.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

# These cases apply to many shells.
assign() {
  sh-spec spec/assign.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@" 
}

# These cases apply to a few shells.
assign-extended() {
  sh-spec spec/assign-extended.test.sh \
    $BASH $MKSH $OSH_LIST "$@" 
}

# Corner cases that OSH doesn't handle
assign-deferred() {
  sh-spec spec/assign-deferred.test.sh \
    $BASH $MKSH "$@" 
}

# These test associative arrays
assign-dialects() {
  sh-spec spec/assign-dialects.test.sh --osh-failures-allowed 1 \
    $BASH $MKSH $OSH_LIST "$@" 
}

background() {
  sh-spec spec/background.test.sh --osh-failures-allowed 2 \
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
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

case_() {
  sh-spec spec/case_.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

if_() {
  sh-spec spec/if_.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtins() {
  sh-spec spec/builtins.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-eval-source() {
  sh-spec spec/builtin-eval-source.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-io() {
  sh-spec spec/builtin-io.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

nul-bytes() {
  sh-spec spec/nul-bytes.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

# Special bash printf things like -v and %q.  Portable stuff goes in builtin-io.
builtin-printf() {
  sh-spec spec/builtin-printf.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

builtins2() {
  sh-spec spec/builtins2.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

# dash and mksh don't implement 'dirs'
builtin-dirs() {
  sh-spec spec/builtin-dirs.test.sh \
    $BASH $ZSH $OSH_LIST "$@"
}

builtin-vars() {
  sh-spec spec/builtin-vars.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-getopts() {
  sh-spec spec/builtin-getopts.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

builtin-bracket() {
  sh-spec spec/builtin-bracket.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

builtin-trap() {
  sh-spec spec/builtin-trap.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

# Bash implements type -t, but no other shell does.  For Nix.
# zsh/mksh/dash don't have the 'help' builtin.
builtin-bash() {
  sh-spec spec/builtin-bash.test.sh --osh-failures-allowed 4 \
    $BASH $OSH_LIST "$@"
}

vars-bash() {
  sh-spec spec/vars-bash.test.sh --osh-failures-allowed 1 \
    $BASH $OSH_LIST "$@"
}

vars-special() {
  sh-spec spec/vars-special.test.sh --osh-failures-allowed 6 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

# This is bash/OSH only
builtin-completion() {
  sh-spec spec/builtin-completion.test.sh --osh-failures-allowed 1 \
    $BASH $OSH_LIST "$@"
}

builtin-special() {
  sh-spec spec/builtin-special.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-times() {
  sh-spec spec/builtin-times.test.sh $BASH $ZSH $OSH_LIST "$@"
}

command-parsing() {
  sh-spec spec/command-parsing.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

func-parsing() {
  sh-spec spec/func-parsing.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

sh-func() {
  sh-spec spec/sh-func.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

glob() {
  # Note: can't pass because it assumes 'bin' exists, etc.
  sh-spec spec/glob.test.sh --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

arith() {
  sh-spec spec/arith.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

command-sub() {
  sh-spec spec/command-sub.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

command_() {
  sh-spec spec/command_.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

pipeline() {
  sh-spec spec/pipeline.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

explore-parsing() {
  sh-spec spec/explore-parsing.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

parse-errors() {
  sh-spec spec/parse-errors.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
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
  sh-spec spec/redirect.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

posix() {
  sh-spec spec/posix.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

introspect() {
  sh-spec spec/introspect.test.sh --osh-failures-allowed 0 \
    $BASH $OSH_LIST "$@"
}

tilde() {
  sh-spec spec/tilde.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

var-op-test() {
  sh-spec spec/var-op-test.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-op-len() {
  sh-spec spec/var-op-len.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

var-op-patsub() {
  # 1 unicode failure, and [^]] which is a parsing divergence
  sh-spec spec/var-op-patsub.test.sh --osh-failures-allowed 2 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

var-op-slice() {
  # dash doesn't support any of these operations
  sh-spec spec/var-op-slice.test.sh --osh-failures-allowed 1 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

var-op-bash() {
  sh-spec spec/var-op-bash.test.sh --osh-failures-allowed 5 \
    $BASH $OSH_LIST "$@"
}

var-op-strip() {
  sh-spec spec/var-op-strip.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
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
  sh-spec spec/var-sub-quote.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

sh-usage() {
  sh-spec spec/sh-usage.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

sh-options() {
  sh-spec spec/sh-options.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

xtrace() {
  sh-spec spec/xtrace.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

strict-options() {
  sh-spec spec/strict-options.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

exit-status() {
  sh-spec spec/exit-status.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

errexit() {
  sh-spec spec/errexit.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

errexit-oil() {
  sh-spec spec/errexit-oil.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

fatal-errors() {
  sh-spec spec/fatal-errors.test.sh --osh-failures-allowed 0 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

# 
# Non-POSIX extensions: arrays, brace expansion, [[, ((, etc.
#

# There as many non-POSIX arithmetic contexts.
arith-context() {
  sh-spec spec/arith-context.test.sh \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

array() {
  sh-spec spec/array.test.sh \
    $BASH $MKSH $OSH_LIST "$@"
}

array-compat() {
  sh-spec spec/array-compat.test.sh \
    $BASH $MKSH $OSH_LIST "$@"
}

type-compat() {
  sh-spec spec/type-compat.test.sh $BASH $OSH_LIST "$@"
}

# += is not POSIX and not in dash.
append() {
  sh-spec spec/append.test.sh --osh-failures-allowed 0 \
    $BASH $MKSH $ZSH $OSH_LIST "$@" 
}

# associative array -- mksh and zsh implement different associative arrays.
assoc() {
  sh-spec spec/assoc.test.sh --osh-failures-allowed 3 \
    $BASH $OSH_LIST "$@"
}

# ZSH also has associative arrays
assoc-zsh() {
  sh-spec spec/assoc-zsh.test.sh $ZSH "$@"
}

# NOTE: zsh passes about half and fails about half.  It supports a subset of [[
# I guess.
dbracket() {
  sh-spec spec/dbracket.test.sh --osh-failures-allowed 0 \
    $BASH $MKSH $OSH_LIST "$@"
  #sh-spec spec/dbracket.test.sh $BASH $MKSH $OSH_LIST $ZSH "$@"
}

dparen() {
  sh-spec spec/dparen.test.sh \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

brace-expansion() {
  sh-spec spec/brace-expansion.test.sh \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

regex() {
  sh-spec spec/regex.test.sh --osh-failures-allowed 2 \
    $BASH $ZSH $OSH_LIST "$@"
}

process-sub() {
  # mksh and dash don't support it
  sh-spec spec/process-sub.test.sh --osh-failures-allowed 0 \
    $BASH $ZSH $OSH_LIST "$@"
}

# This does file system globbing
extglob-files() {
  sh-spec spec/extglob-files.test.sh --osh-failures-allowed 1 \
    $BASH $MKSH $OSH_LIST "$@"
}

# This does string matching.
extglob-match() {
  sh-spec spec/extglob-match.test.sh --osh-failures-allowed 0 \
    $BASH $MKSH $OSH_LIST "$@"
}

nocasematch-match() {
  sh-spec spec/nocasematch-match.test.sh --osh-failures-allowed 3 \
    $BASH $OSH_LIST "$@"
}

# ${!var} syntax -- oil should replace this with associative arrays.
# mksh has completely different behavior for this syntax.  Not worth testing.
var-ref() {
  sh-spec spec/var-ref.test.sh --osh-failures-allowed 0 \
    $BASH $OSH_LIST "$@"
}

# declare / local -n
# there is one divergence when combining -n and ${!ref}
nameref() {
  sh-spec spec/nameref.test.sh --osh-failures-allowed 7 \
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

serialize() {
  # dash doesn't have echo -e, $'', etc.
  sh-spec spec/serialize.test.sh --osh-failures-allowed 0 \
    $BASH $MKSH $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

#
# Smoosh
#

readonly SMOOSH_REPO=~/git/languages/smoosh

sh-spec-smoosh-env() {
  local test_file=$1
  shift

  # - smoosh tests use $TEST_SHELL instead of $SH
  # - cd $TMP to avoid littering repo
  # - pass -o posix
  # - timeout of 1 second
  # - Some tests in smoosh use $HOME and $LOGNAME

  sh-spec $test_file \
    --sh-env-var-name TEST_SHELL \
    --posix \
    --rm-tmp \
    --env-pair "TEST_UTIL=$SMOOSH_REPO/tests/util" \
    --env-pair "LOGNAME=$LOGNAME" \
    --env-pair "HOME=$HOME" \
    --timeout 1 \
    "$@"
}

# For speed, only run with one copy of OSH.
readonly smoosh_osh_list=$OSH_CPYTHON

smoosh() {
  ### Run case smoosh from the console

  sh-spec-smoosh-env _tmp/smoosh.test.sh \
    ${REF_SHELLS[@]} $smoosh_osh_list "$@"
}

smoosh-hang() {
  ### Run case smoosh-hang from the console

  # Need the smoosh timeout tool to run correctly.
  sh-spec-smoosh-env _tmp/smoosh-hang.test.sh \
    --timeout-bin "$SMOOSH_REPO/tests/util/timeout" \
    --timeout 1 \
    ${REF_SHELLS[@]} $smoosh_osh_list "$@"
}

_one-html() {
  local spec_name=$1
  shift

  # TODO:
  # - Smooth tests be in _tmp/spec/smoosh ?
  # - They could go in the CI

  local spec_subdir='survey'
  local base_dir=_tmp/spec/$spec_subdir

  test/spec-runner.sh _test-to-html _tmp/${spec_name}.test.sh \
    > $base_dir/${spec_name}.test.html

  local out=$base_dir/${spec_name}.html
  set +o errexit
  time $spec_name --format html "$@" > $out
  set -o errexit

  echo
  echo "Wrote $out"

  # NOTE: This IGNORES the exit status.
}

smoosh-html() {
  _one-html smoosh
}

smoosh-hang-html() {
  _one-html smoosh-hang
}

html-demo() {
  ### Test for --format html

  local out=_tmp/spec/demo.html
  builtin-special --format html "$@" > $out

  echo
  echo "Wrote $out"
}

all-and-smoosh() {
  ### Run everything that we can publish

  osh-all
  oil-all

  # These aren't all green/yellow yet, and are slow.
  smoosh-html
  smoosh-hang-html
}

#
# Oil Language
#

oil-usage() {
  sh-spec spec/oil-usage.test.sh $OIL_LIST "$@"
}

oil-bin() {
  sh-spec spec/oil-bin.test.sh $OIL_LIST "$@"
}

oil-array() {
  sh-spec spec/oil-array.test.sh --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

oil-assign() {
  sh-spec spec/oil-assign.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-blocks() {
  sh-spec spec/oil-blocks.test.sh --osh-failures-allowed 4 \
    $OSH_LIST "$@"
}

hay() {
  sh-spec spec/hay.test.sh --osh-failures-allowed 2 \
    $OSH_LIST "$@"
}

hay-isolation() {
  sh-spec spec/hay-isolation.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

hay-meta() {
  sh-spec spec/hay-meta.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-builtins() {
  sh-spec spec/oil-builtins.test.sh --osh-failures-allowed 4 \
    $OSH_LIST "$@"
}

oil-builtin-argparse() {
  sh-spec spec/oil-builtin-argparse.test.sh --osh-failures-allowed 2 \
    $OIL_LIST "$@"
}

oil-builtin-describe() {
  sh-spec spec/oil-builtin-describe.test.sh --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

oil-builtin-pp() {
  sh-spec spec/oil-builtin-pp.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-builtin-process() {
  sh-spec spec/oil-builtin-process.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-builtin-shopt() {
  sh-spec spec/oil-builtin-shopt.test.sh --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-command-sub() {
  sh-spec spec/oil-command-sub.test.sh $OSH_LIST "$@"
}

oil-json() {
  sh-spec spec/oil-json.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

# Related to errexit-oil
oil-builtin-error() {
  sh-spec spec/oil-builtin-error.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-multiline() {
  sh-spec spec/oil-multiline.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-options() {
  sh-spec spec/oil-options.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-options-assign() {
  sh-spec spec/oil-options-assign.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-word-eval() {
  sh-spec spec/oil-word-eval.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-expr() {
  sh-spec spec/oil-expr.test.sh --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-expr-arith() {
  sh-spec spec/oil-expr-arith.test.sh --osh-failures-allowed 2 \
    $OSH_LIST "$@"
}

oil-expr-compare() {
  sh-spec spec/oil-expr-compare.test.sh --osh-failures-allowed 2 \
    $OSH_LIST "$@"
}

oil-expr-sub() {
  sh-spec spec/oil-expr-sub.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-string() {
  sh-spec spec/oil-string.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-slice-range() {
  sh-spec spec/oil-slice-range.test.sh --osh-failures-allowed 2 \
    $OSH_LIST "$@"
}

oil-regex() {
  sh-spec spec/oil-regex.test.sh --osh-failures-allowed 4 \
    $OSH_LIST "$@"
}

oil-proc() {
  sh-spec spec/oil-proc.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-case() {
  sh-spec spec/oil-case.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-for() {
  sh-spec spec/oil-for.test.sh --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

oil-funcs-builtin() {
  sh-spec spec/oil-funcs-builtin.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-funcs-external() {
  sh-spec spec/oil-funcs-external.test.sh --osh-failures-allowed 3 \
    $OIL_LIST "$@"
}

oil-special-vars() {
  sh-spec spec/oil-special-vars.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-demo() {
  # Using OSH for minimalism
  sh-spec spec/oil-demo.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-scope() {
  sh-spec spec/oil-scope.test.sh --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-var-sub() {
  sh-spec spec/oil-var-sub.test.sh --osh-failures-allowed 4 \
    $OSH_LIST "$@"
}

oil-xtrace() {
  sh-spec spec/oil-xtrace.test.sh --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

# Use bin/oil

oil-keywords() {
  sh-spec spec/oil-keywords.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-tuple() {
  sh-spec spec/oil-tuple.test.sh --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

oil-interactive() {
  sh-spec spec/oil-interactive.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-user-feedback() {
  sh-spec spec/oil-user-feedback.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-bugs() {
  sh-spec spec/oil-bugs.test.sh --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

oil-reserved() {
  sh-spec spec/oil-reserved.test.sh --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-with-sh() {
  sh-spec spec/oil-with-sh.test.sh --osh-failures-allowed 6 \
    $OIL_LIST "$@"
}

nix-idioms() {
  sh-spec spec/nix-idioms.test.sh --osh-failures-allowed 1 \
    $BASH $OSH_LIST "$@"
}

ble-idioms() {
  sh-spec spec/ble-idioms.test.sh --osh-failures-allowed 0 \
    $BASH $ZSH $MKSH $BUSYBOX_ASH $OSH_LIST "$@"
}

ble-features() {
  sh-spec spec/ble-features.test.sh --osh-failures-allowed 0 \
    $BASH $ZSH $MKSH $BUSYBOX_ASH $DASH yash $OSH_LIST "$@"
}

toysh() {
  sh-spec spec/toysh.test.sh --osh-failures-allowed 3 \
    $BASH $MKSH $OSH_LIST "$@"
}

toysh-posix() {
  sh-spec spec/toysh-posix.test.sh --osh-failures-allowed 3 \
    ${REF_SHELLS[@]} $ZSH yash $OSH_LIST "$@"
}

#
# Tea Language
#

tea-func() {
  # all of these were broken by the new grammar!
  sh-spec spec/tea-func.test.sh --osh-failures-allowed 15 \
    $OSH_LIST "$@"
}


#
# Convenience for fixing specific bugs
#

one-off() {
  set +o errexit

  test/spec.sh array -r 16-17
  test/spec.sh builtin-vars -r 39-40
}

"$@"
