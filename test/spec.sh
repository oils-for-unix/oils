#!/usr/bin/env bash
#
# Usage:
#   test/spec.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source test/common.sh
source test/spec-common.sh

if test -z "${IN_NIX_SHELL:-}"; then
  source build/dev-shell.sh  # to run 'dash', etc.
fi

# TODO: remove this stub after we hollow out this file
run-file() { test/spec-py.sh run-file "$@"; }

here-doc() {
  run-file here-doc "$@"
}

OLD-here-doc() {
  # Old notes:
  # The last two tests, 31 and 32, have different behavior on my Ubuntu and
  # Debian machines.
  # - On Ubuntu, read_from_fd.py fails with Errno 9 -- bad file descriptor.
  # - On Debian, the whole process hangs.
  # Is this due to Python 3.2 vs 3.4?  Either way osh doesn't implement the
  # functionality, so it's probably best to just implement it.
  sh-spec spec/here-doc.test.sh --range 0-31 \
    dash bash mksh $OSH_LIST "$@"


  # 2025-02 update: why do these pass in CI?  But not on my local Debian
  # machine
  #
  # [??? no location ???] I/O error applying redirect: Bad file descriptor
  # close failed in file object destructor:
  # sys.excepthook is missing
  # lost sys.stderr
  #
  # read_from_fd.py gives that error somehow - because the FD isn't closed?
  #
  # - Could this be the descriptor 100 bug in the here doc process?
  #   https://github.com/oils-for-unix/oils/issues/2068
  # - Also look at [??? no location ???] issue

  #run-file here-doc "$@"
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

osh-bugs() {
  run-file osh-bugs "$@"
}

spec-harness-bug() {
  run-file spec-harness-bug "$@"
}

blog1() {
  run-file blog1 "$@"
}

blog2() {
  run-file blog2 "$@"
}

blog-other1() {
  run-file blog-other1 "$@"
}

alias() {
  run-file alias "$@"
}

comments() {
  run-file comments "$@"
}

word-split() {
  run-file word-split "$@"
}

word-eval() {
  run-file word-eval "$@"
}

# These cases apply to many shells.
assign() {
  run-file assign "$@"
}

# These cases apply to a few shells.
assign-extended() {
  run-file assign-extended "$@"
}

# Corner cases that OSH doesn't handle
assign-deferred() {
  run-file assign-deferred "$@"
}

# These test associative arrays
assign-dialects() {
  run-file assign-dialects "$@"
}

background() {
  run-file background "$@"
}

subshell() {
  run-file subshell "$@"
}

quote() {
  run-file quote "$@"
}

unicode() {
  run-file unicode "$@"
}

loop() {
  run-file loop "$@"
}

case_() {
  run-file case_ "$@"
}

if_() {
  run-file if_ "$@"
}

builtin-misc() {
  run-file builtin-misc "$@"
}

builtin-process() {
  run-file builtin-process "$@"
}

builtin-cd() {
  run-file builtin-cd "$@"
}

builtin-eval-source() {
  run-file builtin-eval-source "$@"
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

builtin-meta() {
  run-file builtin-meta  "$@"
}

builtin-history() {
  run-file builtin-history "$@"
}

builtin-dirs() {
  run-file builtin-dirs "$@"
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
  run-file builtin-trap "$@"
}

builtin-trap-err() {
  run-file builtin-trap-err "$@"
}

builtin-trap-bash() {
  run-file builtin-trap-bash "$@"
}

# Bash implements type -t, but no other shell does.  For Nix.
# zsh/mksh/dash don't have the 'help' builtin.
builtin-bash() {
  run-file builtin-bash "$@"
}

builtin-bind() {
  run-file builtin-bind "$@"
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
  run-file builtin-special "$@"
}

builtin-times() {
  run-file builtin-times "$@"
}

command-parsing() {
  run-file command-parsing "$@"
}

func-parsing() {
  run-file func-parsing "$@"
}

sh-func() {
  run-file sh-func "$@"
}

glob() {
  run-file glob "$@"
}

globignore() {
  run-file globignore "$@"
}

globstar() {
  run-file globstar "$@"
}

arith() {
  run-file arith "$@"
}

arith-dynamic() {
  run-file arith-dynamic "$@"
}

command-sub() {
  run-file command-sub "$@"
}

command-sub-ksh() {
  run-file command-sub-ksh "$@"
}

command_() {
  run-file command_ "$@"
}

pipeline() {
  run-file pipeline "$@"
}

explore-parsing() {
  run-file explore-parsing "$@"
}

parse-errors() {
  run-file parse-errors "$@"
}

redirect() {
  run-file redirect "$@"
}

redirect-command() {
  run-file redirect-command "$@"
}

redirect-multi() {
  run-file redirect-multi "$@"
}

posix() {
  run-file posix "$@"
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
  run-file var-op-len "$@"
}

var-op-patsub() {
  # 1 unicode failure, and [^]] which is a parsing divergence
  run-file var-op-patsub "$@"
}

var-op-slice() {
  run-file var-op-slice "$@"
}

var-op-bash() {
  run-file var-op-bash "$@"
}

var-op-strip() {
  run-file var-op-strip "$@"
}

var-sub() {
  # NOTE: ZSH has interesting behavior, like echo hi > "$@" can write to TWO
  # FILES!  But ultimately we don't really care, so I disabled it.
  run-file var-sub "$@"
}

var-num() {
  run-file var-num "$@"
}

var-sub-quote() {
  run-file var-sub-quote "$@"
}

sh-usage() {
  run-file sh-usage "$@"
}

sh-options() {
  run-file sh-options "$@"
}

xtrace() {
  run-file xtrace "$@"
}

strict-options() {
  run-file strict-options "$@"
}

exit-status() {
  run-file exit-status "$@"
}

errexit() {
  run-file errexit "$@"
}

errexit-osh() {
  run-file errexit-osh "$@"
}

fatal-errors() {
  run-file fatal-errors "$@"
}

# 
# Non-POSIX extensions: arrays, brace expansion, [[, ((, etc.
#

# There as many non-POSIX arithmetic contexts.
arith-context() {
  run-file arith-context "$@"
}

array() {
  run-file array "$@"
}

array-basic() {
  run-file array-basic "$@"
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
  run-file assoc-zsh "$@"
}

dbracket() {
  run-file dbracket "$@"
}

dparen() {
  run-file dparen "$@"
}

brace-expansion() {
  run-file brace-expansion "$@"
}

regex() {
  run-file regex "$@"
}

process-sub() {
  run-file process-sub "$@"
}

# This does file system globbing
extglob-files() {
  run-file extglob-files "$@"
}

# This does string matching.
extglob-match() {
  run-file extglob-match "$@"
}

nocasematch-match() {
  run-file nocasematch-match "$@"
}

# ${!var} syntax -- oil should replace this with associative arrays.
# mksh has completely different behavior for this syntax.  Not worth testing.
var-ref() {
  run-file var-ref "$@"
}

nameref() {
  ### declare -n / local -n
  run-file nameref "$@"
}

let() {
  run-file let "$@"
}

for-expr() {
  run-file for-expr "$@"
}

empty-bodies() {
  run-file empty-bodies "$@"
}

# Note: This was for the ANTLR grammars, in the oil-sketch repo.
# this is "suite: disabled"
shell-grammar() {
  run-file shell-grammar "$@"
}

serialize() {
  run-file serialize "$@"
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

ysh-TODO-deprecate() {
  run-file ysh-TODO-deprecate "$@"
}

ysh-convert() {
  run-file ysh-convert "$@"
}

ysh-completion() {
  run-file ysh-completion "$@"
}

ysh-introspect() {
  run-file ysh-introspect "$@"
}

ysh-stdlib() {
  run-file ysh-stdlib "$@"
}

ysh-stdlib-args() {
  run-file ysh-stdlib-args "$@"
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

ysh-control-flow() {
  run-file ysh-control-flow "$@"
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

ysh-env() {
  run-file ysh-env "$@"
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

ysh-cmd-lang() {
  run-file ysh-cmd-lang "$@"
}

ysh-for() {
  run-file ysh-for "$@"
}

ysh-methods() {
  run-file ysh-methods "$@"
}

ysh-method-io() {
  run-file ysh-method-io "$@"
}

ysh-namespaces() {
  run-file ysh-namespaces "$@"
}

ysh-object() {
  run-file ysh-object "$@"
}

ysh-closures() {
  run-file ysh-closures "$@"
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

ysh-proc-meta() {
  run-file ysh-proc-meta "$@"
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

ysh-printing() {
  run-file ysh-printing "$@"
}


#
# More OSH
#

nix-idioms() {
  run-file nix-idioms "$@"
}

zsh-idioms() {
  run-file zsh-idioms "$@"
}

ble-idioms() {
  run-file ble-idioms "$@"
}

ble-sparse() {
  run-file ble-sparse "$@"
}

ble-features() {
  run-file ble-features "$@"
}

toysh() {
  run-file toysh "$@"
}

toysh-posix() {
  run-file toysh-posix "$@"
}

task-five "$@"
