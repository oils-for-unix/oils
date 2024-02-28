#!/usr/bin/env bash
#
# A file that tickles many runtime errors, to see the error message.
#
# Usage:
#   test/runtime-errors.sh <function name>
#
# Note that 'test/spec.sh foo -v -d' can also show errors clearly.
#
# It's a mix of styles:
# - Sometimes we assert errors with _osh-error-1 etc., passing a shell string.
# - Sometimes we just write a function without a wrapper.
#
# It would be nice to clean this up.

source test/common.sh
source test/sh-assert.sh  # banner, _assert-sh-status

# Note: should run in bash/dash mode, where we don't check errors
OSH=${OSH:-bin/osh}
YSH=${YSH:-bin/ysh}


# TODO: get rid of _run-test-func

_run-test-func() {
  ### Run a function, and optionally assert status

  local test_func=$1
  local expected_status=${2:-}

  echo
  echo "===== TEST function: $test_func ====="
  echo

  $OSH $0 $test_func

  status=$?
  if test -n "$expected_status"; then
    if test $status != $expected_status; then
      die "*** Test $test_func -> status $status, expected $expected_status"
    fi
  fi

  echo "----- STATUS: $?"
  echo
}

test-FAIL() {
  ### Make sure the assertions work

  # Error string
  _osh-error-1 'echo hi > /zzz'

  return

  # doesn't fail
  _osh-error-2 'echo hi'

  echo nope
}

#
# PARSE ERRORS
#

test-source_bad_syntax() {
  cat >_tmp/bad-syntax.sh <<EOF
if foo; echo ls; fi
EOF
  _osh-error-2 '. _tmp/bad-syntax.sh'
}

# NOTE:
# - bash correctly reports line 25 (24 would be better)
# - mksh: no line number
# - zsh: line 2 of eval, which doesn't really help.
# - dash: ditto, line 2 of eval
test-eval_bad_syntax() {
  _osh-error-2 '
code="if foo; echo ls; fi"
eval "echo --
     $code"
'
}

#
# COMMAND ERRORS
#

test-no_such_command() {
  _osh-error-X 127 'set -o errexit; ZZZZZ; echo UNREACHABLE'
}

test-no_such_command_commandsub() {
  _osh-should-run 'set -o errexit; echo $(ZZZZZ); echo UNREACHABLE'
  _osh-error-X 127 'set -o errexit; shopt -s command_sub_errexit; echo $(ZZZZZ); echo UNREACHABLE'
}

no_such_command_heredoc() {
  set -o errexit

  # Note: bash gives the line of the beginning of the here doc!  Not the actual
  # line.
  cat <<EOF
one
$(ZZZZZ)
three
EOF
  echo 'SHOULD NOT GET HERE'
}

test-failed_command() {
  _osh-error-1 'set -o errexit; false; echo UNREACHABLE'
}

# This quotes the same line of code twice, but maybe that's OK.  At least there
# is different column information.
test-errexit_usage_error() {
  _osh-error-2 'set -o errexit; type -z'
}

test-errexit_subshell() {
  # Note: for loops, while loops don't trigger errexit; their components do
  _osh-error-X 42 'set -o errexit; ( echo subshell; exit 42; )'
}

TODO-BUG-test-errexit_pipeline() {
  # We don't blame the right location here

  # BUG: what happnened here?  Is there a race?
  local code='set -o errexit; set -o pipefail; echo subshell | cat | exit 42 | wc -l'

  #local code='set -o errexit; set -o pipefail; echo subshell | cat | exit 42'

  bash -c "$code"
  echo status=$?

  _osh-error-X 42 "$code"
}

test-errexit_dbracket() {
  _osh-error-1 'set -o errexit; [[ -n "" ]]; echo UNREACHABLE'
}

shopt -s expand_aliases
# Why can't this be in the function?
alias foo='echo hi; ls '

test-errexit_alias() {
  _osh-error-1 'set -o errexit; type foo; foo /nonexistent'
}

_sep() {
  echo
  echo '---------------------------'
}

test-errexit_one_process() {
  # two quotations of same location: not found then errexit
  _ysh-error-X 127 'zz'

  _sep

  # two quotations, different location
  _ysh-error-1 'echo hi > ""'

  _sep

  _ysh-error-1 'shopt -s failglob; echo *.ZZZZ'

  _sep

  _ysh-error-1 'cd /x'

  _sep

  # TODO: remove duplicate snippet
  _ysh-error-X 126 './README.md; echo hi'

  # one location
  _ysh-error-2 'ls /x; echo $?'

  _sep

  _ysh-error-2 'declare cmd=ls; $cmd /x; echo $?'

  _sep

  # one location
  _ysh-error-1 'echo $undef'

  _sep

  # Show multiple "nested" errors, and then errexit
  _osh-error-1 '
eval "("
echo status=$?

eval ")"
echo status=$?

set -e; shopt -s verbose_errexit
false
echo DONE
'

  _sep

  # Primitives
  _ysh-error-1 '[[ 0 -eq 1 ]]'

  _sep

  _ysh-error-2 '(( 0 ))'
}

test-errexit_multiple_processes() {
  ### A representative set of errors.  For consolidating code quotations

  # command_sub_errexit.  Hm this gives 2 errors as well, because of inherit_errexit
  _ysh-error-1 'echo t=$(true) f=$(false; true)'
  #return

  _sep

  # no pipefail
  _ysh-should-run 'ls | false | wc -l'

  _sep

  # note: need trailing echo to prevent pipeline optimization
  _ysh-error-X 42 'ls | { echo hi; ( exit 42 ); } | wc -l; echo'

  _sep

  # Showing errors for THREE PIDs here!  That is technically correct, but
  # noisy.
  _ysh-error-1 '{ echo one; ( exit 42 ); } |\
{ false; wc -l; }'

  _sep

  # realistic example
  _ysh-error-1 '{ ls; false; } \
| wc -l
'

  _sep

  # Three errors!
  _ysh-error-1 '{ ls; ( false; true ); } | wc -l; echo hi'

  _sep

  _ysh-error-X 127 'ls <(sort YY) <(zz); echo hi'

  # 2 kinds of errors
  _sep
  _ysh-error-X 127 'zz <(sort YY) <(sort ZZ); echo hi'

  # This one has badly interleaved errors!
  _sep
  _ysh-error-X 127 'yy | zz'

  _sep
  _ysh-error-1 'echo $([[ 0 -eq 1 ]])'

  _sep
  _ysh-error-1 'var y = $([[ 0 -eq 1 ]])'
}


_strict-errexit-case() {
  local code=$1

  case-banner "[strict_errexit] $code"

  _osh-error-1 \
    "set -o errexit; shopt -s strict_errexit; $code"
  echo
}

test-strict_errexit_1() {
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

  # Must be separate lines for parsing options to take effect
  _strict-errexit-case 'shopt -s oil:upgrade
                        proc p { echo p }
                        if p { echo hi }'
}

test-strict_errexit_conditionals() {
  # this works, even though this is a subshell
  _strict-errexit-case '
myfunc() { return 1; }

while ( myfunc )
do
  echo yes
done
'

  # Conditional - Proc - Child Interpreter Problem (command sub)
  # Same problem here.  A proc run in a command sub LOSES the exit code.
  _strict-errexit-case '
myfunc() { return 1; }

while test "$(myfunc)" != ""
do
  echo yes
done
'

  # Process Sub is be disallowed; it could invoke a proc!
  _strict-errexit-case '
myfunc() { return 1; }

if cat <(ls)
then
  echo yes
fi
'

  # Conditional - Proc - Child Interpreter Problem (pipeline)
  _strict-errexit-case '
myfunc() {
  return 1
}

set -o pipefail
while myfunc | cat
do
  echo yes
done
'

  # regression for issue #1107 bad error message
  # Also revealed #1113: the strict_errexit check was handled inside the
  # command sub process!
  _strict-errexit-case '
myfunc() {
  return 1
}

foo=$(true)

# test assignment without proc
while bar=$(false)
do
  echo yes
done

# issue 1007 was caused using command.ShAssignment, rather than the more common
# command.Sentence with ;
while spam=$(myfunc)
do
  echo yes
done
'
}

# OLD WAY OF BLAMING
# Note: most of these don't fail
test-strict_errexit_old() {
  # Test out all the location info

  # command.Pipeline.
  _strict-errexit-case 'if ls | wc -l; then echo Pipeline; fi'
  _strict-errexit-case 'if ! ls | wc -l; then echo Pipeline; fi'

  # This one is ALLOWED
  #_strict-errexit-case 'if ! ls; then echo Pipeline; fi'

  # command.AndOr
  _strict-errexit-case 'if echo a && echo b; then echo AndOr; fi'

  # command.DoGroup
  _strict-errexit-case '! for x in a; do echo $x; done'

  # command.BraceGroup
  _strict-errexit-case '_func() { echo; }; ! _func'
  _strict-errexit-case '! { echo brace; }; echo "should not get here"'

  # command.Subshell
  _strict-errexit-case '! ( echo subshell ); echo "should not get here"'

  # command.WhileUntil
  _strict-errexit-case '! while false; do echo while; done; echo "should not get here"'

  # command.If
  _strict-errexit-case '! if true; then false; fi; echo "should not get here"'

  # command.Case
  _strict-errexit-case '! case x in x) echo x;; esac; echo "should not get here"'

  # command.TimeBlock
  _strict-errexit-case '! time echo hi; echo "should not get here"'

  # Command Sub
  _strict-errexit-case '! echo $(echo hi); echo "should not get here"'
}

pipefail() {
  false | wc -l

  set -o errexit
  set -o pipefail
  false | wc -l

  echo 'SHOULD NOT GET HERE'
}

pipefail_no_words() {
  set -o errexit
  set -o pipefail

  # Make sure we can blame this
  seq 3 | wc -l | > /nonexistent

  echo done
}

pipefail_func() {
  set -o errexit -o pipefail
  f42() {
    cat
    # NOTE: If you call 'exit 42', there is no error message displayed!
    #exit 42
    return 42
  }

  # TODO: blame the right location
  echo hi | cat | f42 | wc

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

test-control_flow() {
  # This prints a WARNING in bash.  Not fatal in any shell except zsh.
  _osh-error-X 0 '
break
continue
echo UNREACHABLE
'

  _osh-error-X 1 '
shopt -s strict_control_flow
break
continue
echo UNREACHABLE
'
}

# Errors from core/process.py
core_process() {
  echo foo > not/a/file
  echo foo > /etc/no-perms-for-this

  # DISABLED!  This messes up the toil log file!
  # echo hi 1>&3
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

  # This is the issue addressed by command_sub_errexit!
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

bad_file_descriptor() {
  : 1>&7
}

command_sub_errexit() {
  #set -o errexit
  shopt -s command_sub_errexit || true
  shopt -s inherit_errexit || true

  echo t=$(true) f=$(false) 3=$(exit 3)
  echo 'SHOULD NOT GET HERE'
}

process_sub_fail() {
  shopt -s process_sub_fail || true
  shopt -s inherit_errexit || true
  set -o errexit

  cat <(echo a; exit 2) <(echo b; exit 3)
  echo 'SHOULD NOT GET HERE'
}

myproc() {
  echo ---
  grep pat BAD  # exits with code 2
  #grep pat file.txt
  echo ---
}

bool_status() {
  set -o errexit

  if try --allow-status-01 -- myproc; then
    echo 'match'
  else
    echo 'no match'
  fi
}

bool_status_simple() {
  set -o errexit

  if try --allow-status-01 -- grep pat BAD; then
    echo 'match'
  else
    echo 'no match'
  fi
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

test-divzero() {
  _osh-error-1 'echo $(( 1 / 0 ))'
  _osh-error-1 'echo $(( 1 % 0 ))'

  _osh-error-1 'zero=0; echo $(( 1 / zero ))'
  _osh-error-1 'zero=0; echo $(( 1 % zero ))'

  _osh-error-1 '(( a = 1 / 0 )); echo non-fatal; exit 1'
  _osh-error-1 '(( a = 1 % 0 )); echo non-fatal; exit 1'

  # fatal!
  _osh-error-1 'set -e; (( a = 1 / 0 ));'
  _osh-error-1 'set -e; (( a = 1 % 0 ));'
}

test-unsafe_arith_eval() {
  _osh-error-1 '
  local e1=1+
  local e2="e1 + 5"
  echo $(( e2 ))  # recursively references e1
  '
}

test-unset_expr() {
  _osh-error-1 'unset -v 1[1]'
  _osh-error-2 'unset -v 1+2'
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
  _osh-error-1 'readonly -a array=(1 2 3); array[0]=x'

  _osh-error-1 'readonly -a array=(1 2 3); export array'
}

readonly_assign() {
  _osh-error-1 'readonly x=1; x=2'

  _osh-error-1 'readonly x=2; y=3 x=99'

  _osh-error-1 'readonly x=2; declare x=99'
  _osh-error-1 'readonly x=2; export x=99'
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
  set +o errexit

  # xxx is not a valid file descriptor
  [ -t xxx ]
  [ -t '' ]

  [ zz -eq 0 ]

  # This is from a different evaluator
  #[ $((a/0)) -eq 0 ]
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

  # invalid width
  printf '%*d\n' foo foo
  echo status=$?

  # precision can't be specified
  printf '%.*d\n' foo foo
  echo status=$?

  # precision can't be specified
  printf '%.*s\n' foo foo
  echo status=$?

  # invalid time
  printf '%(%Y)T\n' z
  echo status=$?

  # invalid time with no SPID
  printf '%(%Y)T\n' 
  echo status=$?

  # invalid integer with no SPID
  printf '%d %d %d\n' 1 2 
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

control_flow_subshell() {
  set -o errexit
  for i in $(seq 2); do
    echo $i
    ( break; echo 'oops')
  done
}

fallback_locations() {
  # Redirect
  _osh-error-1 'echo hi > /'

  _osh-error-1 's=x; (( s[0] ))' 

  _osh-error-1 's=x; (( s[0] = 42 ))' 

  _osh-error-1 'set -u; (( undef ))'

  _osh-error-1 '(( 3 ** -2 ))'
  echo

  # DBracket
  _osh-error-1 'set -u; [[ $undef =~ . ]]'

  # No good fallback info here, we need it
  _osh-error-1 '[[ $x =~ $(( 3 ** -2 )) ]]'

  _osh-error-2 'type -x'  # correctly points to -x
  _osh-error-2 'use x'

  # Assign builtin
  _osh-error-2 'export -f'

  _osh-error-1 's=$(true) y=$(( 3 ** -2 ))'

  _osh-error-1 'if s=$(true) y=$(( 3 ** -2 )); then echo hi; fi'

  _osh-error-1 'shopt -s strict_arith; x=a; echo $(( x ))'
  _osh-error-1 'shopt -s strict_arith; x=a; echo $(( $x ))'
  _osh-error-1 'shopt -s strict_arith; x=a; [[ $x -gt 3 ]]'
  _osh-error-1 'shopt -s strict_arith; shopt -u eval_unsafe_arith; x=a; [[ $x -gt 3 ]]'

  _osh-error-1 'shopt -s strict_arith; x=0xgg; echo $(( x ))'


  echo done
}

#
# TEST DRIVER
#

all-tests() {
  run-test-funcs

  set -o
  # When did it get turned on???
  set +o errexit

  # No assertions.  Just showing the error.
  for t in \
    no_such_command_heredoc \
    errexit_usage_error errexit_subshell errexit_pipeline errexit_dbracket errexit_alias \
    errexit_one_process errexit_multiple_processes \
    command_sub_errexit process_sub_fail \
    pipefail pipefail_group pipefail_subshell pipefail_no_words pipefail_func \
    pipefail_while pipefail_multiple \
    core_process osh_state \
    ambiguous_redirect ambiguous_redirect_context \
    bad_file_descriptor \
    nounset bad_var_ref \
    nounset_arith \
    array_arith undef_arith undef_arith2 \
    undef_assoc_array \
    string_to_int_arith string_to_hex string_to_octal \
    string_to_intbase string_to_int_bool string_as_array \
    array_assign_1 array_assign_2 readonly_assign \
    multiple_assign multiple_assign_2 patsub_bad_glob \
    builtin_bracket builtin_builtin builtin_source builtin_cd builtin_pushd \
    builtin_popd builtin_unset builtin_alias_unalias builtin_help \
    builtin_trap builtin_getopts builtin_wait \
    builtin_exec \
    strict_word_eval_warnings strict_arith_warnings \
    control_flow_subshell \
    bool_status bool_status_simple \
    fallback_locations; do

    _run-test-func $t ''  # don't assert status
  done

  return 0
}

# TODO: could show these as separate text files in the CI

with-bash() {
  SH_ASSERT_DISABLE=1 OSH=bash YSH=bash run-test-funcs
}

with-dash() {
  SH_ASSERT_DISABLE=1 OSH=dash YSH=dash run-test-funcs
}

soil-run-py() {
  all-tests
}

soil-run-cpp() {
  # TODO: There are some UBSAN errors, like downcasting mylib::LineReader.
  # Is that a real problem?  Could be due to mylib::File.

  #local osh=_bin/cxx-ubsan/osh

  local osh=_bin/cxx-asan/osh

  ninja $osh
  OSH=$osh all-tests
}

run-for-release() {
  run-other-suite-for-release runtime-errors all-tests
}

"$@"
