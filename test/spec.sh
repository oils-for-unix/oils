#!/usr/bin/env bash
#
# Usage:
#   test/spec.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh

readonly REPO_ROOT=$(cd $(dirname $0)/..; pwd)

# For now, fall back to the shell in $PATH.
shell-path() {
  local name=$1
  if test -f _tmp/spec-bin/$name; then
    echo $REPO_ROOT/_tmp/spec-bin/$name
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
  mkdir -p _tmp/shells
  ln -s -f --verbose "$(which busybox)" _tmp/shells/ash
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

oil-version-text() {
  date-and-git-info

  for bin in $OIL_LIST; do
    echo ---
    echo "\$ $bin --version"
    $bin --version
    echo
  done
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
  local my_busybox=_tmp/spec-bin/busybox-1.31.1/busybox
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

  local this_dir=$(cd $(dirname $0); pwd)

  local tmp_env=$this_dir/../_tmp/spec-tmp/$(basename $test_file)
  mkdir -p $tmp_env

  PYTHONPATH=. test/sh_spec.py \
      --tmp-env $tmp_env \
      --path-env "$this_dir/../spec/bin:/bin:/usr/bin" \
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
  PYTHONPATH=. python -m trace --trackcalls -C $out \
    test/sh_spec.py spec/var-sub.test.sh $DASH $BASH "$@"

  ls -l $out
  head $out/*.cover
}

#
# Run All tests
#

osh-all() {
  test/spec-runner.sh all-parallel osh "$@"
}

oil-all() {
  test/spec-runner.sh all-parallel oil "$@"
}

# Usgae: test/spec.sh dbg smoke, dbg-all
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

oil-bin() {
  sh-spec spec/oil-bin.test.sh $OIL_LIST "$@"
}

smoke() {
  sh-spec spec/smoke.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

interactive() {
  sh-spec spec/interactive.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

prompt() {
  sh-spec spec/prompt.test.sh --osh-failures-allowed 1 \
    $BASH $OSH_LIST "$@"
}

osh-only() {
  # 2 failures until we build in a JSON encoder.
  sh-spec spec/osh-only.test.sh --osh-failures-allowed 2  \
    $OSH_LIST "$@"
}

# Regress bugs
bugs() {
  sh-spec spec/bugs.test.sh ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
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
  sh-spec spec/word-split.test.sh --osh-failures-allowed 3 \
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
  sh-spec spec/builtins.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-eval-source() {
  sh-spec spec/builtin-eval-source.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-io() {
  sh-spec spec/builtin-io.test.sh \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

# Special bash printf things like -v and %q.  Portable stuff goes in builtin-io.
builtin-printf() {
  sh-spec spec/builtin-printf.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $BUSYBOX_ASH $OSH_LIST "$@"
}

builtins2() {
  sh-spec spec/builtins2.test.sh ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

# dash and mksh don't implement 'dirs'
builtin-dirs() {
  sh-spec spec/builtin-dirs.test.sh --osh-failures-allowed 1 \
    $BASH $ZSH $OSH_LIST "$@"
}

builtin-vars() {
  sh-spec spec/builtin-vars.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

builtin-getopts() {
  sh-spec spec/builtin-getopts.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

builtin-bracket() {
  sh-spec spec/builtin-bracket.test.sh \
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
  sh-spec spec/sh-func.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

glob() {
  sh-spec spec/glob.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

arith() {
  sh-spec spec/arith.test.sh --osh-failures-allowed 2 \
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
  sh-spec spec/redirect.test.sh --osh-failures-allowed 5 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

posix() {
  sh-spec spec/posix.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

special-vars() {
  sh-spec spec/special-vars.test.sh --cd-tmp --osh-failures-allowed 4 \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

introspect() {
  sh-spec spec/introspect.test.sh \
    $BASH $OSH_LIST "$@"
}

# DONE -- pysh is the most conformant!
tilde() {
  sh-spec spec/tilde.test.sh ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-op-test() {
  sh-spec spec/var-op-test.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-op-len() {
  sh-spec spec/var-op-len.test.sh \
    ${REF_SHELLS[@]} $ZSH $OSH_LIST "$@"
}

var-op-patsub() {
  # 1 unicode failure
  sh-spec spec/var-op-patsub.test.sh --osh-failures-allowed 1 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

var-op-other() {
  # dash doesn't support any of these operations
  sh-spec spec/var-op-other.test.sh --osh-failures-allowed 0 \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

var-op-bash() {
  sh-spec spec/var-op-bash.test.sh --osh-failures-allowed 2 \
    $BASH $OSH_LIST "$@"
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
  sh-spec spec/var-num.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

var-sub-quote() {
  sh-spec spec/var-sub-quote.test.sh --osh-failures-allowed 2 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

sh-usage() {
  sh-spec spec/sh-usage.test.sh \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

sh-options() {
  sh-spec spec/sh-options.test.sh --osh-failures-allowed 2 \
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

exit-status() {
  sh-spec spec/exit-status.test.sh --osh-failures-allowed 1 \
    ${REF_SHELLS[@]} $OSH_LIST "$@"
}

errexit() {
  sh-spec spec/errexit.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
}

errexit-oil() {
  sh-spec spec/errexit-oil.test.sh \
    ${REF_SHELLS[@]} $BUSYBOX_ASH $OSH_LIST "$@"
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
  sh-spec spec/type-compat.test.sh $BASH "$@"
}

# += is not POSIX and not in dash.
append() {
  sh-spec spec/append.test.sh \
    $BASH $MKSH $OSH_LIST "$@" 
}

# associative array -- mksh and zsh implement different associative arrays.
assoc() {
  sh-spec spec/assoc.test.sh --osh-failures-allowed 1 \
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
  sh-spec spec/brace-expansion.test.sh \
    $BASH $MKSH $ZSH $OSH_LIST "$@"
}

regex() {
  sh-spec spec/regex.test.sh --osh-failures-allowed 2 \
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
  sh-spec spec/extglob-match.test.sh \
    $BASH $MKSH $OSH_LIST "$@"
}

# ${!var} syntax -- oil should replace this with associative arrays.
# mksh has completely different behavior for this syntax.  Not worth testing.
var-ref() {
  sh-spec spec/var-ref.test.sh --osh-failures-allowed 4 \
    $BASH $OSH_LIST "$@"
}

# local -n
# mksh implements some of this.  OSH doesn't implement it at all.
named-ref() {
  sh-spec spec/named-ref.test.sh \
    $BASH $MKSH "$@"
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
    --cd-tmp \
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

  test/spec-runner.sh _test-to-html _tmp/${spec_name}.test.sh \
    > _tmp/spec/${spec_name}.test.html

  local out=_tmp/spec/${spec_name}.html
  set +o errexit
  time $spec_name --format html --trace "$@" > $out
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

oil-array() {
  sh-spec spec/oil-array.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-assign() {
  sh-spec spec/oil-assign.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-blocks() {
  sh-spec spec/oil-blocks.test.sh --cd-tmp \
    $OSH_LIST "$@"
}

oil-builtins() {
  sh-spec spec/oil-builtins.test.sh --cd-tmp \
    $OSH_LIST "$@"
}

oil-json() {
  sh-spec spec/oil-json.test.sh --cd-tmp --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-options() {
  sh-spec spec/oil-options.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-expr() {
  sh-spec spec/oil-expr.test.sh --cd-tmp --osh-failures-allowed 5 \
    $OSH_LIST "$@"
}

oil-expr-sub() {
  sh-spec spec/oil-expr-sub.test.sh --cd-tmp --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-slice-range() {
  sh-spec spec/oil-slice-range.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OSH_LIST "$@"
}

oil-regex() {
  sh-spec spec/oil-regex.test.sh --cd-tmp --osh-failures-allowed 2 \
    $OSH_LIST "$@"
}

oil-func-proc() {
  sh-spec spec/oil-func-proc.test.sh --cd-tmp --osh-failures-allowed 0 \
    $OSH_LIST "$@"
}

oil-builtin-funcs() {
  sh-spec spec/oil-builtin-funcs.test.sh --cd-tmp --osh-failures-allowed 2 \
    $OIL_LIST "$@"
}

# Use bin/oil

oil-keywords() {
  sh-spec spec/oil-keywords.test.sh --cd-tmp --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}

oil-tuple() {
  sh-spec spec/oil-tuple.test.sh --cd-tmp --osh-failures-allowed 1 \
    $OIL_LIST "$@"
}

oil-interactive() {
  sh-spec spec/oil-interactive.test.sh --cd-tmp --osh-failures-allowed 0 \
    $OIL_LIST "$@"
}


"$@"
