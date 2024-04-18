#!/usr/bin/env bash
#
# Usage:
#   test/spec.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh
source test/spec-common.sh
source devtools/run-task.sh

if test -z "${IN_NIX_SHELL:-}"; then
  source build/dev-shell.sh  # to run 'dash', etc.
fi

# TODO: Just use 'dash bash' and $PATH
readonly DASH=dash
readonly BASH=bash
readonly MKSH=mksh
readonly ZSH=zsh
readonly BUSYBOX_ASH=ash

# ash and dash are similar, so not including ash by default.  zsh is not quite
# POSIX.
readonly REF_SHELLS=($DASH $BASH $MKSH)

check-survey-shells() {
  ### Make sure bash, zsh, OSH, etc. exist

  # Note: yash isn't here, but it is used in a couple tests

  test/spec-runner.sh shell-sanity-check "${REF_SHELLS[@]}" $ZSH $BUSYBOX_ASH $OSH_LIST
}

# TODO: remove this stub after we hollow out this file

run-file() { test/spec-py.sh run-file "$@"; }

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
# Individual tests.
#
# We configure the shells they run on and the number of allowed failures (to
# prevent regressions.)
#

interactive-parse() {
  run-file interactive-parse "$@"
}

smoke() {
  run-file smoke "$@"
}

interactive() {
  run-file interactive "$@"
}

prompt() {
  run-file prompt "$@"
}

bugs() {
  run-file bugs "$@"
}

TODO-deprecate() {
  run-file TODO-deprecate "$@"
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
  run-file alias "$@"
}

comments() {
  sh-spec spec/comments.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

word-split() {
  run-file word-split "$@"
}

word-eval() {
  sh-spec spec/word-eval.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

# These cases apply to many shells.
assign() {
  run-file assign "$@"
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
  run-file assign-dialects "$@"
}

background() {
  run-file background "$@"
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
  run-file case_ "$@"
}

if_() {
  sh-spec spec/if_.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtins() {
  run-file builtins "$@"
}

builtin-eval-source() {
  sh-spec spec/builtin-eval-source.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-echo() {
  run-file builtin-echo "$@"
}

builtin-read() {
  run-file builtin-read "$@"
}

nul-bytes() {
  run-file nul-bytes "$@"
}

whitespace() {
  run-file whitespace "$@"
}

# Special bash printf things like -v and %q.  Portable stuff goes in builtin-io.
builtin-printf() {
  run-file builtin-printf "$@"
}

builtins2() {
  run-file builtins2 "$@"
}

builtin-history() {
  run-file builtin-history "$@"
}

# dash and mksh don't implement 'dirs'
builtin-dirs() {
  sh-spec spec/builtin-dirs.test.sh \
    $BASH $ZSH $OSH_LIST "$@"
}

builtin-vars() {
  run-file builtin-vars "$@"
}

builtin-getopts() {
  run-file builtin-getopts "$@"
}

builtin-bracket() {
  run-file builtin-bracket "$@"
}

builtin-trap() {
  sh-spec spec/builtin-trap.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

builtin-trap-bash() {
  run-file builtin-trap-bash "$@"
}

# Bash implements type -t, but no other shell does.  For Nix.
# zsh/mksh/dash don't have the 'help' builtin.
builtin-bash() {
  run-file builtin-bash "$@"
}

builtin-type() {
  run-file builtin-type "$@"
}

builtin-type-bash() {
  run-file builtin-type-bash "$@"
}

vars-bash() {
  run-file vars-bash "$@"
}

vars-special() {
  run-file vars-special "$@"
}

builtin-completion() {
  run-file builtin-completion "$@"
}

builtin-special() {
  sh-spec spec/builtin-special.test.sh --oils-failures-allowed 4 \
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
  sh-spec spec/sh-func.test.sh --oils-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

glob() {
  # Note: can't pass because it assumes 'bin' exists, etc.
  sh-spec spec/glob.test.sh --oils-failures-allowed 3 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

globignore() {
  run-file globignore "$@"
}

arith() {
  run-file arith "$@"
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
  sh-spec spec/parse-errors.test.sh --oils-failures-allowed 3 \
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
  sh-spec spec/redirect.test.sh --oils-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

redirect-multi() {
  run-file redirect-multi "$@"
}

posix() {
  sh-spec spec/posix.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

introspect() {
  run-file introspect "$@"
}

tilde() {
  run-file tilde "$@"
}

var-op-test() {
  run-file var-op-test "$@"
}

var-op-len() {
  sh-spec spec/var-op-len.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

var-op-patsub() {
  # 1 unicode failure, and [^]] which is a parsing divergence
  sh-spec spec/var-op-patsub.test.sh --oils-failures-allowed 2 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
  # TODO: can add $BUSYBOX_ASH
}

var-op-slice() {
  # dash doesn't support any of these operations
  sh-spec spec/var-op-slice.test.sh --oils-failures-allowed 1 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

var-op-bash() {
  run-file var-op-bash "$@"
}

var-op-strip() {
  sh-spec spec/var-op-strip.test.sh \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

var-sub() {
  # NOTE: ZSH has interesting behavior, like echo hi > "$@" can write to TWO
  # FILES!  But ultimately we don't really care, so I disabled it.
  sh-spec spec/var-sub.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-num() {
  run-file var-num "$@"
}

var-sub-quote() {
  sh-spec spec/var-sub-quote.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

sh-usage() {
  run-file sh-usage "$@"
}

sh-options() {
  run-file sh-options "$@"
}

xtrace() {
  sh-spec spec/xtrace.test.sh --oils-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

strict-options() {
  sh-spec spec/strict-options.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

exit-status() {
  run-file exit-status "$@"
}

errexit() {
  sh-spec spec/errexit.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

errexit-osh() {
  run-file errexit-osh "$@"
}

fatal-errors() {
  sh-spec spec/fatal-errors.test.sh \
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
  run-file array-compat "$@"
}

type-compat() {
  run-file type-compat "$@"
}

# += is not POSIX and not in dash.
append() {
  run-file append "$@"
}

# associative array -- mksh and zsh implement different associative arrays.
assoc() {
  run-file assoc "$@"
}

# ZSH also has associative arrays
assoc-zsh() {
  sh-spec spec/assoc-zsh.test.sh $ZSH "$@"
}

dbracket() {
  run-file dbracket "$@"
}

dparen() {
  sh-spec spec/dparen.test.sh --oils-failures-allowed 1 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

brace-expansion() {
  run-file brace-expansion "$@"
}

regex() {
  run-file regex "$@"
}

process-sub() {
  # mksh and dash don't support it
  sh-spec spec/process-sub.test.sh \
    $BASH $ZSH $OSH_LIST "$@"
}

# This does file system globbing
extglob-files() {
  sh-spec spec/extglob-files.test.sh --oils-failures-allowed 1 \
    $BASH $MKSH $OSH_LIST "$@"
}

# This does string matching.
extglob-match() {
  sh-spec spec/extglob-match.test.sh \
    $BASH $MKSH $OSH_LIST "$@"
}

nocasematch-match() {
  run-file nocasematch-match "$@"
}

# ${!var} syntax -- oil should replace this with associative arrays.
# mksh has completely different behavior for this syntax.  Not worth testing.
var-ref() {
  run-file var-ref "$@"
}

# declare / local -n
# there is one divergence when combining -n and ${!ref}
nameref() {
  sh-spec spec/nameref.test.sh --oils-failures-allowed 7 \
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
  run-file serialize "$@"
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
    --env-pair "TEST_UTIL=$SMOOSH_REPO/tests/util" \
    --env-pair "LOGNAME=$LOGNAME" \
    --env-pair "HOME=$HOME" \
    --timeout 1 \
    --oils-bin-dir $REPO_ROOT/bin \
    --compare-shells \
    "$@"
}

# For speed, only run with one copy of OSH.
readonly smoosh_osh_list=$OSH_CPYTHON

smoosh() {
  ### Run case smoosh from the console

  # TODO: Use --oils-bin-dir
  # our_shells, etc.

  sh-spec-smoosh-env _tmp/smoosh.test.sh \
    ${REF_SHELLS[@]} $smoosh_osh_list \
    "$@"
}

smoosh-hang() {
  ### Run case smoosh-hang from the console

  # Need the smoosh timeout tool to run correctly.
  sh-spec-smoosh-env _tmp/smoosh-hang.test.sh \
    --timeout-bin "$SMOOSH_REPO/tests/util/timeout" \
    --timeout 1 \
    "$@"
}

_one-html() {
  local spec_name=$1
  shift

  local out_dir=_tmp/spec/smoosh
  local tmp_dir=_tmp/src-smoosh
  mkdir -p $out_dir $out_dir

  doctools/src_tree.py smoosh-file \
    _tmp/$spec_name.test.sh \
    $out_dir/$spec_name.test.html

  local out=$out_dir/${spec_name}.html
  set +o errexit
  # Shell function is smoosh or smoosh-hang
  time $spec_name --format html "$@" > $out
  set -o errexit

  echo
  echo "Wrote $out"

  # NOTE: This IGNORES the exit status.
}

# TODO:
# - Put these tests in the CI
# - Import smoosh spec tests into the repo, with 'test/smoosh.sh'

smoosh-html() {
  ### Run by devtools/release.sh
  _one-html smoosh "$@"
}

smoosh-hang-html() {
  ### Run by devtools/release.sh
  _one-html smoosh-hang "$@"
}

html-demo() {
  ### Test for --format html

  local out=_tmp/spec/demo.html
  builtin-special --format html "$@" > $out

  echo
  echo "Wrote $out"
}

#
# Hay is part of the YSH suite
#

hay() {
  run-file hay "$@"
}

hay-isolation() {
  run-file hay-isolation "$@"
}

hay-meta() {
  run-file hay-meta "$@"
}

#
# YSH
#

ysh-convert() {
  run-file ysh-convert "$@"
}

ysh-completion() {
  run-file ysh-completion "$@"
}

ysh-stdlib() {
  run-file ysh-stdlib "$@"
}

ysh-stdlib-2() {
  run-file ysh-stdlib-2 "$@"
}

ysh-stdlib-args() {
  run-file ysh-stdlib-args "$@"
}

ysh-stdlib-testing() {
  run-file ysh-stdlib-testing "$@"
}

ysh-stdlib-synch() {
  run-file ysh-stdlib-synch "$@"
}

ysh-source() {
  run-file ysh-source "$@"
}

ysh-usage() {
  run-file ysh-usage "$@"
}

ysh-unicode() {
  run-file ysh-unicode "$@"
}

ysh-bin() {
  run-file ysh-bin "$@"
}

ysh-dict() {
  run-file ysh-dict "$@"
}

ysh-list() {
  run-file ysh-list "$@"
}

ysh-place() {
  run-file ysh-place "$@"
}

ysh-prompt() {
  run-file ysh-prompt "$@"
}

ysh-assign() {
  run-file ysh-assign "$@"
}

ysh-augmented() {
  run-file ysh-augmented "$@"
}

ysh-blocks() {
  run-file ysh-blocks "$@"
}

ysh-bugs() {
  run-file ysh-bugs "$@"
}

ysh-builtins() {
  run-file ysh-builtins "$@"
}

ysh-builtin-module() {
  run-file ysh-builtin-module "$@"
}

ysh-builtin-eval() {
  run-file ysh-builtin-eval "$@"
}

# Related to errexit-oil
ysh-builtin-error() {
  run-file ysh-builtin-error "$@"
}

ysh-builtin-meta() {
  run-file ysh-builtin-meta "$@"
}

ysh-builtin-process() {
  run-file ysh-builtin-process "$@"
}

ysh-builtin-shopt() {
  run-file ysh-builtin-shopt "$@"
}

ysh-case() {
  run-file ysh-case "$@"
}

ysh-command-sub() {
  run-file ysh-command-sub "$@"
}

ysh-demo() {
  run-file ysh-demo "$@"
}

ysh-expr() {
  run-file ysh-expr "$@"
}

ysh-int-float() {
  run-file ysh-int-float "$@"
}

ysh-expr-bool() {
  run-file ysh-expr-bool "$@"
}

ysh-expr-arith() {
  run-file ysh-expr-arith "$@"
}

ysh-expr-compare() {
  run-file ysh-expr-compare "$@"
}

ysh-expr-sub() {
  run-file ysh-expr-sub "$@"
}

ysh-for() {
  run-file ysh-for "$@"
}

ysh-methods() {
  run-file ysh-methods "$@"
}

ysh-func() {
  run-file ysh-func "$@"
}

ysh-func-builtin() {
  run-file ysh-func-builtin "$@"
}

ysh-funcs-external() {
  run-file ysh-funcs-external "$@"
}

ysh-interactive() {
  run-file ysh-interactive "$@"
}

ysh-json() {
  run-file ysh-json "$@"
}

ysh-keywords() {
  run-file ysh-keywords "$@"
}

ysh-multiline() {
  run-file ysh-multiline "$@"
}

ysh-options() {
  run-file ysh-options "$@"
}

ysh-options-assign() {
  run-file ysh-options-assign "$@"
}

ysh-proc() {
  run-file ysh-proc "$@"
}

ysh-regex() {
  run-file ysh-regex "$@"
}

ysh-regex-api() {
  run-file ysh-regex-api "$@"
}

ysh-reserved() {
  run-file ysh-reserved "$@"
}

ysh-scope() {
  run-file ysh-scope "$@"
}

ysh-slice-range() {
  run-file ysh-slice-range "$@"
}

ysh-string() {
  run-file ysh-string "$@"
}

ysh-special-vars() {
  run-file ysh-special-vars "$@"
}

ysh-tuple() {
  run-file ysh-tuple "$@"
}

ysh-var-sub() {
  run-file ysh-var-sub "$@"
}

ysh-with-sh() {
  run-file ysh-with-sh "$@"
}

ysh-word-eval() {
  run-file ysh-word-eval "$@"
}

ysh-xtrace() {
  run-file ysh-xtrace "$@"
}

ysh-user-feedback() {
  run-file ysh-user-feedback "$@"
}

ysh-builtin-ctx() {
  run-file ysh-builtin-ctx "$@"
}

ysh-builtin-error() {
  run-file ysh-builtin-error "$@"
}

ysh-builtin-help() {
  run-file ysh-builtin-help "$@"
}

ysh-dev() {
  run-file ysh-dev "$@"
}


#
# More OSH
#

nix-idioms() {
  run-file nix-idioms "$@"
}

ble-idioms() {
  sh-spec spec/ble-idioms.test.sh \
    $BASH $ZSH $MKSH $BUSYBOX_ASH $OSH_LIST "$@"
}

ble-features() {
  sh-spec spec/ble-features.test.sh \
    $BASH $ZSH $MKSH $BUSYBOX_ASH $DASH yash $OSH_LIST "$@"
}

toysh() {
  sh-spec spec/toysh.test.sh --oils-failures-allowed 3 \
    $BASH $MKSH $OSH_LIST "$@"
}

toysh-posix() {
  sh-spec spec/toysh-posix.test.sh --oils-failures-allowed 3 \
    ${REF_SHELLS[@]} $ZSH yash $OSH_LIST "$@"
}

run-task "$@"
