#!/usr/bin/env bash
#
# Usage:
#   $SH ./runtime-errors.sh <function name>
#
# Run with bash/dash/mksh/zsh.

source test/common.sh

# Run with SH=bash too
SH=${SH:-bin/osh}

banner() {
  echo
  echo ===== "$@" =====
  echo
}

_error-case() {
  $SH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 1; then
    die "Expected status 1, got $status"
  fi
}

#
# PARSE ERRORS
#

source_bad_syntax() {
  cat >_tmp/bad-syntax.sh <<EOF
if foo; echo ls; fi
EOF
  . _tmp/bad-syntax.sh
}

# NOTE:
# - bash correctly reports line 25 (24 would be better)
# - mksh: no line number
# - zsh: line 2 of eval, which doesn't really help.
# - dash: ditto, line 2 of eval
eval_bad_syntax() {
  local code='if foo; echo ls; fi'
  eval "echo --
        $code"
}

#
# COMMAND ERRORS
#

no_such_command() {
  set -o errexit
  ZZZZZ

  echo 'SHOULD NOT GET HERE'
}

no_such_command_commandsub() {
  set -o errexit
  echo $(ZZZZZ)
  echo 'SHOULD NOT GET HERE'
}

no_such_command_heredoc() {
  set -o errexit

  # Note: bash gives the line of the beginning of the here doc!  Not the actual
  # line.
  # TODO: osh doesn't give any psition info.
  cat <<EOF
one
$(ZZZZZ)
three
EOF
  echo 'SHOULD NOT GET HERE'
}

failed_command() {
  set -o errexit
  false

  echo 'SHOULD NOT GET HERE'
}

# This quotes the same line of code twice, but maybe that's OK.  At least there
# is different column information.
errexit_usage_error() {
  set -o errexit
  type -z
}

errexit_subshell() {
  set -o errexit

  # Note: for loops, while loops don't trigger errexit; their components do
  ( echo subshell; exit 42; )
}

errexit_dbracket() {
  set -o errexit
  [[ -n '' ]]
  echo 'SHOULD NOT GET HERE'
}

shopt -s expand_aliases
# Why can't this be in the function?
alias foo='echo hi; ls '

errexit_alias() {
  set -o errexit

  type foo

  foo /nonexistent
}

_strict-errexit-case() {
  local code=$1
  banner "[strict_errexit] $code"
  _error-case \
    "set -o errexit; shopt -s strict_errexit; $code"
  echo
}

strict_errexit_1() {
  # Test out all the location info

  _strict-errexit-case '! { echo 1; echo 2; }'

  _strict-errexit-case '{ echo 1; echo 2; } && true'
  _strict-errexit-case '{ echo 1; echo 2; } || true'

  # More chains
  _strict-errexit-case '{ echo 1; echo 2; } && true && true'
  _strict-errexit-case 'true && { echo 1; echo 2; } || true || true'
  _strict-errexit-case 'true && true && { echo 1; echo 2; } || true || true'

  _strict-errexit-case 'if { echo 1; echo 2; }; then echo IF; fi'
  _strict-errexit-case 'while { echo 1; echo 2; }; do echo WHILE; done'
  _strict-errexit-case 'until { echo 1; echo 2; }; do echo UNTIL; done'
}

# OLD WAY OF BLAMING
strict_errexit_2() {
  # Test out all the location info

  # command.Pipeline.
  _strict-errexit-case 'if ls | wc -l; then echo Pipeline; fi'
  _strict-errexit-case 'if ! ls | wc -l; then echo Pipeline; fi'

  # This one is logical
  #_strict-errexit-case 'if ! ls; then echo Pipeline; fi'

  # command.AndOr
  #_strict-errexit-case 'if echo a && echo b; then echo AndOr; fi'

  # command.DoGroup
  _strict-errexit-case '! for x in a; do echo $x; done'

  # command.BraceGroup
  _strict-errexit-case '_func() { echo; }; ! _func'
  _strict-errexit-case '! { echo brace; }'

  # command.Subshell
  _strict-errexit-case '! ( echo subshell )'

  # command.WhileUntil
  _strict-errexit-case '! while false; do echo while; done'

  # command.If
  _strict-errexit-case '! if true; then false; fi'

  # command.Case
  _strict-errexit-case '! case x in x) echo x;; esac'

  # command.TimeBlock
  _strict-errexit-case '! time echo hi'

  _strict-errexit-case '! echo $(echo hi)'
}

pipefail() {
  false | wc -l

  set -o errexit
  set -o pipefail
  false | wc -l

  echo 'SHOULD NOT GET HERE'
}

pipefail_func() {
  set -o errexit -o pipefail
  f() {
    cat
    # NOTE: If you call 'exit 42', there is no error message displayed!
    #exit 42
    return 42
  }
  echo hi | f | wc

  echo 'SHOULD NOT GET HERE'
}

# TODO: point to {.  It's the same sas a subshell so you don't know exactly
# which command failed.
pipefail_group() {
  set -o errexit -o pipefail
  echo hi | { cat; sh -c 'exit 42'; } | wc

  echo 'SHOULD NOT GET HERE'
}

# TODO: point to (
pipefail_subshell() {
  set -o errexit -o pipefail
  echo hi | (cat; sh -c 'exit 42') | wc

  echo 'SHOULD NOT GET HERE'
}

# TODO: point to 'while'
pipefail_while() {
  set -o errexit -o pipefail
  seq 3 | while true; do
    read line
    echo X $line X
    if test "$line" = 2; then
      sh -c 'exit 42'
    fi
  done | wc

  echo 'SHOULD NOT GET HERE'
}

# Multiple errors from multiple processes
# TODO: These errors get interleaved and messed up.  Maybe we should always
# print a single line from pipeline processes?  We should set their
# ErrorFormatter?
pipefail_multiple() {
  set -o errexit -o pipefail
  { echo 'four'; sh -c 'exit 4'; } |
  { echo 'five'; sh -c 'exit 5'; } |
  { echo 'six'; sh -c 'exit 6'; }
}

# NOTE: This prints a WARNING in bash.  Not fatal in any shell except zsh.
control_flow() {
  break
  continue

  echo 'SHOULD NOT GET HERE'
}

# Errors from core/process.py
core_process() {
  echo foo > not/a/file
  echo foo > /etc/no-perms-for-this
  echo hi 1>&3
}

# Errors from osh/state.py
osh_state() {
  # $HOME is exported so it can't be an array
  HOME=(a b)
}

ambiguous_redirect() {
  echo foo > "$@"
  echo 'ambiguous redirect not fatal unless errexit'

  set -o errexit
  echo foo > "$@"
  echo 'should not get here'
}

# bash semantics.
ambiguous_redirect_context() {
  # Problem: A WORD cannot fail.  Only a COMMAND can fail.

  # http://stackoverflow.com/questions/29532904/bash-subshell-errexit-semantics
  # https://groups.google.com/forum/?fromgroups=#!topic/gnu.bash.bug/NCK_0GmIv2M

  # http://unix.stackexchange.com/questions/23026/how-can-i-get-bash-to-exit-on-backtick-failure-in-a-similar-way-to-pipefail

  echo $(echo hi > "$@")
  echo 'ambiguous is NOT FATAL in command sub'
  echo

  foo=$(echo hi > "$@")
  echo $foo
  echo 'ambiguous is NOT FATAL in assignment in command sub'
  echo

  set -o errexit

  # This is the issue addressed by more_errexit!
  echo $(echo hi > "$@")
  echo 'ambiguous is NOT FATAL in command sub, even if errexit'
  echo

  # OK this one works.  Because the exit code of the assignment is the exit
  # code of the RHS?
  echo 'But when the command sub is in an assignment, it is fatal'
  foo=$(echo hi > "$@")
  echo $foo
  echo 'SHOULD NOT REACH HERE'
}

#
# WORD ERRORS
#

nounset() {
  set -o nounset
  echo $x

  echo 'SHOULD NOT GET HERE'
}

bad_var_ref() {
  name='bad var name'
  echo ${!name}
}

#
# ARITHMETIC ERRORS
#

nounset_arith() {
  set -o nounset
  echo $(( x ))

  echo 'SHOULD NOT GET HERE'
}

divzero() {
  _error-case 'echo $(( 1 / 0 ))'
  _error-case 'echo $(( 1 % 0 ))'

  _error-case 'zero=0; echo $(( 1 / zero ))'
  _error-case 'zero=0; echo $(( 1 % zero ))'

  _error-case '(( a = 1 / 0 )); echo non-fatal; exit 1'
  _error-case '(( a = 1 % 0 )); echo non-fatal; exit 1'

  # fatal!
  _error-case 'set -e; (( a = 1 / 0 ));'
  _error-case 'set -e; (( a = 1 % 0 ));'
}

unsafe_arith_eval() {
  shopt -s unsafe_arith_eval

  local e1='1+'
  local e2='e1 + 5'
  echo $(( e2 ))
}

unset_expr() {
  shopt -s unsafe_arith_eval

  _error-case 'unset -v 1[1]'
  _error-case 'unset -v 1+2'
}

# Only dash flags this as an error.
string_to_int_arith() {
  local x='ZZZ'
  echo $(( x + 5 ))

  shopt -s strict_arith

  echo $(( x + 5 ))

  echo 'SHOULD NOT GET HERE'
}

# Hm bash treats this as a fatal error
string_to_hex() {
  echo $(( 0xGG + 1 ))

  echo 'SHOULD NOT GET HERE'
}

# Hm bash treats this as a fatal error
string_to_octal() {
  echo $(( 018 + 1 ))

  echo 'SHOULD NOT GET HERE'
}

# Hm bash treats this as a fatal error
string_to_intbase() {
  echo $(( 16#GG ))

  echo 'SHOULD NOT GET HERE'
}

undef_arith() {
  (( undef++ ))  # doesn't make sense

  # Can't assign to characters of string?  Is that strong?
  (( undef[42]++ ))
}

undef_arith2() {
  a=()

  # undefined cell: This is kind of what happens in awk / "wok"
  (( a[42]++ ))
  (( a[42]++ ))
  spec/bin/argv.py "${a[@]}"
}

array_arith() {
  a=(1 2)
  (( a++ ))  # doesn't make sense
  echo "${a[@]}"
}

undef_assoc_array() {
  declare -A A
  A['foo']=bar
  echo "${A['foo']}"

  # TODO: none of this is implemented!
  if false; then
    A['spam']+=1
    A['spam']+=1

    spec/bin/argv.py "${A[@]}"

    (( A['spam']++ ))
    (( A['spam']++ ))

    spec/bin/argv.py "${A[@]}"
  fi
}

patsub_bad_glob() {
  local x='abc'
  # inspired by git-completion.bash
  echo ${x//[^]}
}


#
# BOOLEAN ERRORS
#

# Only osh cares about this.
string_to_int_bool() {
  [[ a -eq 0 ]]

  shopt -s strict_arith

  [[ a -eq 0 ]]
  echo 'SHOULD NOT GET HERE'
}

strict_array() {
  set -- 1 2
  echo foo > _tmp/"$@"
  shopt -s strict_array
  echo foo > _tmp/"$@"
}

strict_array_2() {
  local foo="$@"
  shopt -s strict_array
  local foo="$@"
}

strict_array_3() {
  local foo=${1:- "[$@]" }
  shopt -s strict_array
  local foo=${1:- "[$@]" }
}

strict_array_4() {
  local -a x
  x[42]=99
  echo "x[42] = ${x[42]}"

  # Not implemented yet
  shopt -s strict_array
  local -a y
  y[42]=99
}

array_assign_1() {
  s=1
  s[0]=x  # can't assign value
}

array_assign_2() {
  readonly -a array=(1 2 3)
  array[0]=x
}

readonly_assign() {
  readonly x=1
  x=2
}

multiple_assign() {
  readonly x=1
  # It blames x, not a!
  a=1 b=2 x=42
}

multiple_assign_2() {
  readonly y
  local x=1 y=$(( x ))
  echo $y
}

string_as_array() {
  local str='foo'
  echo $str
  echo "${str[@]}"
}

#
# BUILTINS
#

builtin_bracket() {
  # xxx is not a valid file descriptor
  [ -t xxx ]
}

builtin_builtin() {
  set +o errexit
  builtin ls
}

builtin_source() {
  source

  bad=/nonexistent/path
  source $bad
}

builtin_cd() {
  ( unset HOME
    cd
  )

  # TODO: Hm this gives a different useful error without location info
  ( unset HOME
    HOME=(a b)
    cd
  )

  # TODO: Hm this gives a different useful error without location info
  ( unset OLDPWD
    cd -
  )

  ( cd /nonexistent
  )
}

builtin_pushd() {
  pushd /nonexistent
}

builtin_popd() {
  popd  # empty dir stack

  (
    local dir=$PWD/_tmp/runtime-error-popd
    mkdir -p $dir
    pushd $dir
    pushd /
    rmdir $dir
    popd
  )
}

builtin_unset() {
  local x=x
  readonly a

  unset x a
  unset -v x a
}

builtin_alias_unalias() {
  alias zzz
  unalias zzz
}

builtin_help() {
  help zzz
}

builtin_trap() {
  trap 
  trap EXIT

  trap zzz yyy
}

builtin_getopts() {
  getopts
  getopts 'a:' 

  # TODO: It would be nice to put this in a loop and use it properly
  set -- -a
  getopts 'a:' varname
}

builtin_printf() {
  printf '%s %d\n' foo not_a_number
  echo status=$?

  # bad arg recycling.  This is really a runtime error.
  printf '%s %d\n' foo 3 bar
  echo status=$?
}


builtin_wait() {
  wait 1234578
}

builtin_exec() {
  exec nonexistent-command 1 2 3
  echo $?
}

#
# Strict options (see spec/strict_options.sh)
#

strict_word_eval_warnings() {
  # Warnings when 'set +o strict_word_eval' is OFF

  echo slice start negative
  s='abc'
  echo -${s: -2}-

  echo slice length negative
  s='abc'
  echo -${s: 1: -2}-

  # TODO: These need span IDs.
  # - invalid utf-8 and also invalid backslash escape

  echo slice bad utf-8
  s=$(echo -e "\xFF")bcdef
  echo -${s:1:3}-

  echo length bad utf-8
  echo ${#s}
}

strict_arith_warnings() {
  local x='xx'
  echo $(( x + 1 ))

  # TODO: OSH is more lenient here actually
  local y='-yy-'
  echo $(( y + 1 ))

  [[ $y -eq 0 ]]

  echo 'done'
}

strict_control_flow_warnings() {
  break
}

control_flow_subshell() {
  set -o errexit
  for i in $(seq 2); do
    echo $i
    ( break; echo 'oops')
  done
}

#
# TEST DRIVER
#

_run_test() {
  local t=$1

  echo "--------"
  echo "    CASE: $t"
  # Run in subshell so the whole thing doesn't exit
  ( $t )
  echo "    STATUS: $?"
  echo
}

all() {
  # Can't be done inside a loop!
  _run_test control_flow 

  for t in \
    no_such_command no_such_command_commandsub no_such_command_heredoc \
    failed_command errexit_usage_error errexit_subshell errexit_dbracket \
    errexit_alias strict_errexit_1 strict_errexit_2 \
    pipefail pipefail_group pipefail_subshell pipefail_func \
    pipefail_while pipefail_multiple \
    core_process osh_state \
    nounset bad_var_ref \
    nounset_arith divzero \
    array_arith undef_arith undef_arith2 \
    undef_assoc_array \
    unsafe_arith_eval unset_expr \
    string_to_int_arith string_to_hex string_to_octal \
    string_to_intbase string_to_int_bool string_as_array \
    array_assign_1 array_assign_2 readonly_assign \
    multiple_assign multiple_assign_2 patsub_bad_glob \
    builtin_bracket builtin_builtin builtin_source builtin_cd builtin_pushd \
    builtin_popd builtin_unset builtin_alias_unalias builtin_help \
    builtin_trap builtin_getopts builtin_wait \
    builtin_exec \
    strict_word_eval_warnings strict_arith_warnings \
    strict_control_flow_warnings control_flow_subshell; do
    _run_test $t
  done
}

run-all-with-osh() {
  bin/osh $0 all
}

run-for-release() {
  run-other-suite-for-release runtime-errors run-all-with-osh
}

"$@"
