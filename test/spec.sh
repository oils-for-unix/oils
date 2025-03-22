#!/usr/bin/env bash
#
# This file is GENERATED -- DO NOT EDIT.
#
# Update it with:
#   test/spec-runner.sh gen-task-file
#
# Usage:
#   test/spec.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source build/dev-shell.sh

alias() {
  test/spec-py.sh run-file alias "$@"
}

append() {
  test/spec-py.sh run-file append "$@"
}

arith-context() {
  test/spec-py.sh run-file arith-context "$@"
}

arith-dynamic() {
  test/spec-py.sh run-file arith-dynamic "$@"
}

arith() {
  test/spec-py.sh run-file arith "$@"
}

array-assoc() {
  test/spec-py.sh run-file array-assoc "$@"
}

array-basic() {
  test/spec-py.sh run-file array-basic "$@"
}

array-compat() {
  test/spec-py.sh run-file array-compat "$@"
}

array-literal() {
  test/spec-py.sh run-file array-literal "$@"
}

array-sparse() {
  test/spec-py.sh run-file array-sparse "$@"
}

array() {
  test/spec-py.sh run-file array "$@"
}

assign-deferred() {
  test/spec-py.sh run-file assign-deferred "$@"
}

assign-dialects() {
  test/spec-py.sh run-file assign-dialects "$@"
}

assign-extended() {
  test/spec-py.sh run-file assign-extended "$@"
}

assign() {
  test/spec-py.sh run-file assign "$@"
}

background() {
  test/spec-py.sh run-file background "$@"
}

ble-features() {
  test/spec-py.sh run-file ble-features "$@"
}

ble-idioms() {
  test/spec-py.sh run-file ble-idioms "$@"
}

ble-unset() {
  test/spec-py.sh run-file ble-unset "$@"
}

blog1() {
  test/spec-py.sh run-file blog1 "$@"
}

blog2() {
  test/spec-py.sh run-file blog2 "$@"
}

blog-other1() {
  test/spec-py.sh run-file blog-other1 "$@"
}

brace-expansion() {
  test/spec-py.sh run-file brace-expansion "$@"
}

bugs() {
  test/spec-py.sh run-file bugs "$@"
}

builtin-bash() {
  test/spec-py.sh run-file builtin-bash "$@"
}

builtin-bind() {
  test/spec-py.sh run-file builtin-bind "$@"
}

builtin-bracket() {
  test/spec-py.sh run-file builtin-bracket "$@"
}

builtin-cd() {
  test/spec-py.sh run-file builtin-cd "$@"
}

builtin-completion() {
  test/spec-py.sh run-file builtin-completion "$@"
}

builtin-dirs() {
  test/spec-py.sh run-file builtin-dirs "$@"
}

builtin-echo() {
  test/spec-py.sh run-file builtin-echo "$@"
}

builtin-eval-source() {
  test/spec-py.sh run-file builtin-eval-source "$@"
}

builtin-getopts() {
  test/spec-py.sh run-file builtin-getopts "$@"
}

builtin-history() {
  test/spec-py.sh run-file builtin-history "$@"
}

builtin-meta-assign() {
  test/spec-py.sh run-file builtin-meta-assign "$@"
}

builtin-meta() {
  test/spec-py.sh run-file builtin-meta "$@"
}

builtin-misc() {
  test/spec-py.sh run-file builtin-misc "$@"
}

builtin-printf() {
  test/spec-py.sh run-file builtin-printf "$@"
}

builtin-process() {
  test/spec-py.sh run-file builtin-process "$@"
}

builtin-read() {
  test/spec-py.sh run-file builtin-read "$@"
}

builtin-special() {
  test/spec-py.sh run-file builtin-special "$@"
}

builtin-times() {
  test/spec-py.sh run-file builtin-times "$@"
}

builtin-trap-bash() {
  test/spec-py.sh run-file builtin-trap-bash "$@"
}

builtin-trap-err() {
  test/spec-py.sh run-file builtin-trap-err "$@"
}

builtin-trap() {
  test/spec-py.sh run-file builtin-trap "$@"
}

builtin-type-bash() {
  test/spec-py.sh run-file builtin-type-bash "$@"
}

builtin-type() {
  test/spec-py.sh run-file builtin-type "$@"
}

builtin-vars() {
  test/spec-py.sh run-file builtin-vars "$@"
}

case_() {
  test/spec-py.sh run-file case_ "$@"
}

command-parsing() {
  test/spec-py.sh run-file command-parsing "$@"
}

command-sub-ksh() {
  test/spec-py.sh run-file command-sub-ksh "$@"
}

command-sub() {
  test/spec-py.sh run-file command-sub "$@"
}

command_() {
  test/spec-py.sh run-file command_ "$@"
}

comments() {
  test/spec-py.sh run-file comments "$@"
}

dbracket() {
  test/spec-py.sh run-file dbracket "$@"
}

dparen() {
  test/spec-py.sh run-file dparen "$@"
}

empty-bodies() {
  test/spec-py.sh run-file empty-bodies "$@"
}

errexit-osh() {
  test/spec-py.sh run-file errexit-osh "$@"
}

errexit() {
  test/spec-py.sh run-file errexit "$@"
}

exit-status() {
  test/spec-py.sh run-file exit-status "$@"
}

explore-parsing() {
  test/spec-py.sh run-file explore-parsing "$@"
}

extglob-files() {
  test/spec-py.sh run-file extglob-files "$@"
}

extglob-match() {
  test/spec-py.sh run-file extglob-match "$@"
}

fatal-errors() {
  test/spec-py.sh run-file fatal-errors "$@"
}

for-expr() {
  test/spec-py.sh run-file for-expr "$@"
}

func-parsing() {
  test/spec-py.sh run-file func-parsing "$@"
}

globignore() {
  test/spec-py.sh run-file globignore "$@"
}

globstar() {
  test/spec-py.sh run-file globstar "$@"
}

glob() {
  test/spec-py.sh run-file glob "$@"
}

hay-isolation() {
  test/spec-py.sh run-file hay-isolation "$@"
}

hay-meta() {
  test/spec-py.sh run-file hay-meta "$@"
}

hay() {
  test/spec-py.sh run-file hay "$@"
}

here-doc() {
  test/spec-py.sh run-file here-doc "$@"
}

if_() {
  test/spec-py.sh run-file if_ "$@"
}

interactive-parse() {
  test/spec-py.sh run-file interactive-parse "$@"
}

interactive() {
  test/spec-py.sh run-file interactive "$@"
}

introspect() {
  test/spec-py.sh run-file introspect "$@"
}

let() {
  test/spec-py.sh run-file let "$@"
}

loop() {
  test/spec-py.sh run-file loop "$@"
}

nameref() {
  test/spec-py.sh run-file nameref "$@"
}

nix-idioms() {
  test/spec-py.sh run-file nix-idioms "$@"
}

nocasematch-match() {
  test/spec-py.sh run-file nocasematch-match "$@"
}

nul-bytes() {
  test/spec-py.sh run-file nul-bytes "$@"
}

osh-bugs() {
  test/spec-py.sh run-file osh-bugs "$@"
}

parse-errors() {
  test/spec-py.sh run-file parse-errors "$@"
}

pipeline() {
  test/spec-py.sh run-file pipeline "$@"
}

posix() {
  test/spec-py.sh run-file posix "$@"
}

process-sub() {
  test/spec-py.sh run-file process-sub "$@"
}

prompt() {
  test/spec-py.sh run-file prompt "$@"
}

quote() {
  test/spec-py.sh run-file quote "$@"
}

redirect-command() {
  test/spec-py.sh run-file redirect-command "$@"
}

redirect-multi() {
  test/spec-py.sh run-file redirect-multi "$@"
}

redirect() {
  test/spec-py.sh run-file redirect "$@"
}

regex() {
  test/spec-py.sh run-file regex "$@"
}

serialize() {
  test/spec-py.sh run-file serialize "$@"
}

shell-grammar() {
  test/spec-py.sh run-file shell-grammar "$@"
}

sh-func() {
  test/spec-py.sh run-file sh-func "$@"
}

sh-options() {
  test/spec-py.sh run-file sh-options "$@"
}

sh-usage() {
  test/spec-py.sh run-file sh-usage "$@"
}

smoke() {
  test/spec-py.sh run-file smoke "$@"
}

spec-harness-bug() {
  test/spec-py.sh run-file spec-harness-bug "$@"
}

strict-options() {
  test/spec-py.sh run-file strict-options "$@"
}

subshell() {
  test/spec-py.sh run-file subshell "$@"
}

temp-binding() {
  test/spec-py.sh run-file temp-binding "$@"
}

tilde() {
  test/spec-py.sh run-file tilde "$@"
}

toysh-posix() {
  test/spec-py.sh run-file toysh-posix "$@"
}

toysh() {
  test/spec-py.sh run-file toysh "$@"
}

type-compat() {
  test/spec-py.sh run-file type-compat "$@"
}

unicode() {
  test/spec-py.sh run-file unicode "$@"
}

var-num() {
  test/spec-py.sh run-file var-num "$@"
}

var-op-bash() {
  test/spec-py.sh run-file var-op-bash "$@"
}

var-op-len() {
  test/spec-py.sh run-file var-op-len "$@"
}

var-op-patsub() {
  test/spec-py.sh run-file var-op-patsub "$@"
}

var-op-slice() {
  test/spec-py.sh run-file var-op-slice "$@"
}

var-op-strip() {
  test/spec-py.sh run-file var-op-strip "$@"
}

var-op-test() {
  test/spec-py.sh run-file var-op-test "$@"
}

var-ref() {
  test/spec-py.sh run-file var-ref "$@"
}

vars-bash() {
  test/spec-py.sh run-file vars-bash "$@"
}

vars-special() {
  test/spec-py.sh run-file vars-special "$@"
}

var-sub-quote() {
  test/spec-py.sh run-file var-sub-quote "$@"
}

var-sub() {
  test/spec-py.sh run-file var-sub "$@"
}

whitespace() {
  test/spec-py.sh run-file whitespace "$@"
}

word-eval() {
  test/spec-py.sh run-file word-eval "$@"
}

word-split() {
  test/spec-py.sh run-file word-split "$@"
}

xtrace() {
  test/spec-py.sh run-file xtrace "$@"
}

ysh-assign() {
  test/spec-py.sh run-file ysh-assign "$@"
}

ysh-augmented() {
  test/spec-py.sh run-file ysh-augmented "$@"
}

ysh-bin() {
  test/spec-py.sh run-file ysh-bin "$@"
}

ysh-blocks() {
  test/spec-py.sh run-file ysh-blocks "$@"
}

ysh-bugs() {
  test/spec-py.sh run-file ysh-bugs "$@"
}

ysh-builtin-ctx() {
  test/spec-py.sh run-file ysh-builtin-ctx "$@"
}

ysh-builtin-error() {
  test/spec-py.sh run-file ysh-builtin-error "$@"
}

ysh-builtin-eval() {
  test/spec-py.sh run-file ysh-builtin-eval "$@"
}

ysh-builtin-help() {
  test/spec-py.sh run-file ysh-builtin-help "$@"
}

ysh-builtin-meta() {
  test/spec-py.sh run-file ysh-builtin-meta "$@"
}

ysh-builtin-module() {
  test/spec-py.sh run-file ysh-builtin-module "$@"
}

ysh-builtin-process() {
  test/spec-py.sh run-file ysh-builtin-process "$@"
}

ysh-builtin-shopt() {
  test/spec-py.sh run-file ysh-builtin-shopt "$@"
}

ysh-builtins() {
  test/spec-py.sh run-file ysh-builtins "$@"
}

ysh-case() {
  test/spec-py.sh run-file ysh-case "$@"
}

ysh-closures() {
  test/spec-py.sh run-file ysh-closures "$@"
}

ysh-cmd-lang() {
  test/spec-py.sh run-file ysh-cmd-lang "$@"
}

ysh-command-sub() {
  test/spec-py.sh run-file ysh-command-sub "$@"
}

ysh-completion() {
  test/spec-py.sh run-file ysh-completion "$@"
}

ysh-control-flow() {
  test/spec-py.sh run-file ysh-control-flow "$@"
}

ysh-convert() {
  test/spec-py.sh run-file ysh-convert "$@"
}

ysh-demo() {
  test/spec-py.sh run-file ysh-demo "$@"
}

ysh-dev() {
  test/spec-py.sh run-file ysh-dev "$@"
}

ysh-dict() {
  test/spec-py.sh run-file ysh-dict "$@"
}

ysh-env() {
  test/spec-py.sh run-file ysh-env "$@"
}

ysh-expr-arith() {
  test/spec-py.sh run-file ysh-expr-arith "$@"
}

ysh-expr-bool() {
  test/spec-py.sh run-file ysh-expr-bool "$@"
}

ysh-expr-compare() {
  test/spec-py.sh run-file ysh-expr-compare "$@"
}

ysh-expr-sub() {
  test/spec-py.sh run-file ysh-expr-sub "$@"
}

ysh-expr() {
  test/spec-py.sh run-file ysh-expr "$@"
}

ysh-for() {
  test/spec-py.sh run-file ysh-for "$@"
}

ysh-func-builtin() {
  test/spec-py.sh run-file ysh-func-builtin "$@"
}

ysh-funcs-external() {
  test/spec-py.sh run-file ysh-funcs-external "$@"
}

ysh-func() {
  test/spec-py.sh run-file ysh-func "$@"
}

ysh-interactive() {
  test/spec-py.sh run-file ysh-interactive "$@"
}

ysh-int-float() {
  test/spec-py.sh run-file ysh-int-float "$@"
}

ysh-introspect() {
  test/spec-py.sh run-file ysh-introspect "$@"
}

ysh-json() {
  test/spec-py.sh run-file ysh-json "$@"
}

ysh-keywords() {
  test/spec-py.sh run-file ysh-keywords "$@"
}

ysh-list() {
  test/spec-py.sh run-file ysh-list "$@"
}

ysh-method-io() {
  test/spec-py.sh run-file ysh-method-io "$@"
}

ysh-method-other() {
  test/spec-py.sh run-file ysh-method-other "$@"
}

ysh-methods() {
  test/spec-py.sh run-file ysh-methods "$@"
}

ysh-multiline() {
  test/spec-py.sh run-file ysh-multiline "$@"
}

ysh-namespaces() {
  test/spec-py.sh run-file ysh-namespaces "$@"
}

ysh-object() {
  test/spec-py.sh run-file ysh-object "$@"
}

ysh-options-assign() {
  test/spec-py.sh run-file ysh-options-assign "$@"
}

ysh-options() {
  test/spec-py.sh run-file ysh-options "$@"
}

ysh-place() {
  test/spec-py.sh run-file ysh-place "$@"
}

ysh-printing() {
  test/spec-py.sh run-file ysh-printing "$@"
}

ysh-proc-meta() {
  test/spec-py.sh run-file ysh-proc-meta "$@"
}

ysh-proc() {
  test/spec-py.sh run-file ysh-proc "$@"
}

ysh-prompt() {
  test/spec-py.sh run-file ysh-prompt "$@"
}

ysh-purity() {
  test/spec-py.sh run-file ysh-purity "$@"
}

ysh-regex-api() {
  test/spec-py.sh run-file ysh-regex-api "$@"
}

ysh-regex() {
  test/spec-py.sh run-file ysh-regex "$@"
}

ysh-reserved() {
  test/spec-py.sh run-file ysh-reserved "$@"
}

ysh-scope() {
  test/spec-py.sh run-file ysh-scope "$@"
}

ysh-slice-range() {
  test/spec-py.sh run-file ysh-slice-range "$@"
}

ysh-source() {
  test/spec-py.sh run-file ysh-source "$@"
}

ysh-special-vars() {
  test/spec-py.sh run-file ysh-special-vars "$@"
}

ysh-stdlib-args() {
  test/spec-py.sh run-file ysh-stdlib-args "$@"
}

ysh-stdlib() {
  test/spec-py.sh run-file ysh-stdlib "$@"
}

ysh-string() {
  test/spec-py.sh run-file ysh-string "$@"
}

ysh-TODO-deprecate() {
  test/spec-py.sh run-file ysh-TODO-deprecate "$@"
}

ysh-tuple() {
  test/spec-py.sh run-file ysh-tuple "$@"
}

ysh-unicode() {
  test/spec-py.sh run-file ysh-unicode "$@"
}

ysh-usage() {
  test/spec-py.sh run-file ysh-usage "$@"
}

ysh-user-feedback() {
  test/spec-py.sh run-file ysh-user-feedback "$@"
}

ysh-var-sub() {
  test/spec-py.sh run-file ysh-var-sub "$@"
}

ysh-with-sh() {
  test/spec-py.sh run-file ysh-with-sh "$@"
}

ysh-word-eval() {
  test/spec-py.sh run-file ysh-word-eval "$@"
}

ysh-xtrace() {
  test/spec-py.sh run-file ysh-xtrace "$@"
}

zsh-assoc() {
  test/spec-py.sh run-file zsh-assoc "$@"
}

zsh-idioms() {
  test/spec-py.sh run-file zsh-idioms "$@"
}

task-five "$@"
