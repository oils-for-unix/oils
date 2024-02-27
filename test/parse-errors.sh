#!/usr/bin/env bash
#
# Usage:
#   test/parse-errors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh
source test/sh-assert.sh  # banner, _assert-sh-status

# Run with SH=bash too
SH=${SH:-bin/osh}
YSH=${YSH:-bin/ysh}

#
# Assertions
#

_should-parse() {
  ### Pass a string that should parse as $1

  local message='Should parse under OSH'
  _assert-sh-status 0 $SH "$message" \
    -n -c "$@"
}

_should-parse-here() {
  ### Take stdin a here doc, pass it as first argument
  _should-parse "$(cat)"
}

_error-case() {
  ### Pass a string that should NOT parse as $1
  local message='Should NOT parse under OSH'
  _assert-sh-status 2 $SH "$message" \
    -n -c "$@"
}

_error-case-here() {
  ### Take stdin a here doc, pass it as first argument
  _error-case "$(cat)";
}

# YSH assertions

_ysh-should-parse() {
  local message='Should parse under YSH'
  _assert-sh-status 0 $YSH "$message" \
    -n -c "$@"
}

# So we can write single quoted strings in an easier way
_ysh-should-parse-here() {
  _ysh-should-parse "$(cat)"
}

_ysh-parse-error() {
  ### Assert that a parse error happens with Oil options on
  local message='Should NOT parse under YSH'
  _assert-sh-status 2 $YSH "$message" \
    -n -c "$@"
}

# So we can write single quoted strings in an easier way
_ysh-parse-error-here() {
  _ysh-parse-error "$(cat)"
}

# More detailed assertions

_assert-status-2() {
  ### An interface where you can pass flags like -O parse_backslash

  local message=$0
  _assert-sh-status 2 $SH $message "$@"
}

_assert-status-2-here() {
  _assert-status-2 "$@" -c "$(cat)"
}

_runtime-parse-error() {
  ### Assert that a parse error happens at runtime, e.g. for [ z z ]

  banner "$@"
  echo
  $SH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

#
# Cases
#

# All in osh/word_parse.py
patsub() {
  set +o errexit

  _should-parse 'echo ${x/}'
  _should-parse 'echo ${x//}'

  _should-parse 'echo ${x/foo}'  # pat 'foo', no mode, replace empty

  _should-parse 'echo ${x//foo}'  # pat 'foo', replace mode '/', replace empty
  _should-parse 'echo ${x/%foo}'  # same as above

  _should-parse 'echo ${x///foo}'

  _should-parse 'echo ${x///}'   # found and fixed bug
  _should-parse 'echo ${x/%/}'   # pat '', replace mode '%', replace ''

  _should-parse 'echo ${x////}'  # pat '/', replace mode '/', replace empty
  _should-parse 'echo ${x/%//}'  # pat '', replace mode '%', replace '/'

  # Newline in replacement pattern
  _should-parse 'echo ${x//foo/replace
}'
  _should-parse 'echo ${x//foo/replace$foo}'
}

# osh/word_parse.py
word-parse() {
  set +o errexit

  _error-case 'echo ${'

  # This parses like a slice, but that's OK.  Maybe talk about arithmetic
  # expression.  Maybe say where it started?
  _error-case '${foo:}'

  _error-case 'echo ${a[@Z'

  _error-case 'echo ${x.}'
  _error-case 'echo ${!x.}'

  # Slicing
  _error-case 'echo ${a:1;}'
  _error-case 'echo ${a:1:2;}'

  # I don't seem to be able to tickle errors here
  #_error-case 'echo ${a:-}'
  #_error-case 'echo ${a#}'

  _error-case 'echo ${#a.'

  # for (( ))
  _error-case 'for (( i = 0; i < 10; i++ ;'
  # Hm not sure about this
  _error-case 'for (( i = 0; i < 10; i++ /'

  _error-case 'echo @(extglob|foo'

  # Copied from osh/word_parse_test.py.  Bugs were found while writing
  # core/completion_test.py.

  _error-case '${undef:-'
  _error-case '${undef:-$'
  _error-case '${undef:-$F'

  _error-case '${x@'
  _error-case '${x@Q'

  _error-case '${x%'

  _error-case '${x/'
  _error-case '${x/a/'
  _error-case '${x/a/b'
  _error-case '${x:'
}

array-literal() {
  set +o errexit

  # Array literal with invalid TokenWord.
  _error-case 'a=(1 & 2)'
  _error-case 'a= (1 2)'
  _error-case 'a=(1 2'
  _error-case 'a=(1 ${2@} )'  # error in word inside array literal
}

arith-context() {
  set +o errexit

  # $(( ))
  _error-case 'echo $(( 1 + 2 ;'
  _error-case 'echo $(( 1 + 2 );'
  _error-case 'echo $(( '
  _error-case 'echo $(( 1'

  # Disable Oil stuff for osh_{parse,eval}.asan
  if false; then
    # Non-standard arith sub $[1 + 2]
    _error-case 'echo $[ 1 + 2 ;'

    # What's going on here?   No location info?
    _error-case 'echo $[ 1 + 2 /'

    _error-case 'echo $[ 1 + 2 / 3'
    _error-case 'echo $['
  fi

  # (( ))
  _error-case '(( 1 + 2 /'
  _error-case '(( 1 + 2 )/'
  _error-case '(( 1'
  _error-case '(('

  # Should be an error
  _error-case 'a[x+]=1'

  _error-case 'a[]=1'

  _error-case 'a[*]=1'

  # These errors are different because the arithmetic lexer mode has } but not
  # {.  May be changed later.
  _error-case '(( a + { ))'
  _error-case '(( a + } ))'

}

arith-integration() {
  set +o errexit

  # Regression: these were not parse errors, but should be!
  _error-case 'echo $((a b))'
  _error-case '((a b))'

  # Empty arithmetic expressions
  _should-parse 'for ((x=0; x<5; x++)); do echo $x; done'
  _should-parse 'for ((; x<5; x++)); do echo $x; done'
  _should-parse 'for ((; ; x++)); do echo $x; done'
  _should-parse 'for ((; ;)); do echo $x; done'

  # Extra tokens on the end of each expression
  _error-case 'for ((x=0; x<5; x++ b)); do echo $x; done'

  _error-case 'for ((x=0 b; x<5; x++)); do echo $x; done'
  _error-case 'for ((x=0; x<5 b; x++)); do echo $x; done'

  _error-case '${a:1+2 b}'
  _error-case '${a:1+2:3+4 b}'

  _error-case '${a[1+2 b]}'
}

arith-expr() {
  set +o errexit

  # BUG: the token is off here
  _error-case '$(( 1 + + ))'

  # BUG: not a great error either
  _error-case '$(( 1 2 ))'

  # Triggered a crash!
  _error-case '$(( - ; ))'

  # NOTE: This is confusing, should point to ` for command context?
  _error-case '$(( ` ))'

  _error-case '$(( $ ))'

  # Invalid assignments
  _error-case '$(( x+1 = 42 ))'
  _error-case '$(( (x+42)++ ))'
  _error-case '$(( ++(x+42) ))'

  # Note these aren't caught because '1' is an ArithWord like 0x$x
  #_error-case '$(( 1 = foo ))'
  #_error-case '$(( 1++ ))'
  #_error-case '$(( ++1 ))'
}

command-sub() {
  set +o errexit
  _error-case ' 
    echo line 2
    echo $( echo '
  _error-case ' 
    echo line 2
    echo ` echo '

  # This is source.Reparsed('backticks', ...)

  # Both unclosed
  _error-case '
    echo line 2
    echo ` echo \` '

  # Only the inner one is unclosed
  _error-case '
    echo line 2
    echo ` echo \`unclosed ` '

  _error-case 'echo `for x in`'
}

bool-expr() {
  set +o errexit

  # Extra word
  _error-case '[[ a b ]]'
  _error-case '[[ a "a"$(echo hi)"b" ]]'

  # Wrong error message
  _error-case '[[ a == ]]'

  if false; then
    # Invalid regex
    # These are currently only detected at runtime.
    _error-case '[[ $var =~ * ]]'
    _error-case '[[ $var =~ + ]]'
  fi

  # Unbalanced parens
  _error-case '[[ ( 1 == 2 - ]]'

  _error-case '[[ == ]]'
  _error-case '[[ ) ]]'
  _error-case '[[ ( ]]'

  _error-case '[[ ;;; ]]'
  _error-case '[['

  # Expected right )
  _error-case '[[ ( a == b foo${var} ]]'
}

# These don't have any location information.
test-builtin() {
  set +o errexit

  # Some of these come from osh/bool_parse.py, and some from
  # osh/builtin_bracket.py.

  # Extra token
  _runtime-parse-error '[ x -a y f ]'
  _runtime-parse-error 'test x -a y f'

  # Missing closing ]
  _runtime-parse-error '[ x '

  # Hm some of these errors are wonky.  Need positions.
  _runtime-parse-error '[ x x ]'

  _runtime-parse-error '[ x x "a b" ]'

  # This is a runtime error but is handled similarly
  _runtime-parse-error '[ -t xxx ]'

  _runtime-parse-error '[ \( x -a -y -a z ]'

  # -o tests if an option is enabled.
  #_error-case '[ -o x ]'
}

printf-builtin() {
  set +o errexit
  _runtime-parse-error 'printf %'
  _runtime-parse-error 'printf [%Z]'

  _runtime-parse-error 'printf -v "-invalid-" %s foo'
}

other-builtins() {
  set +o errexit

  _runtime-parse-error 'shift 1 2'
  _runtime-parse-error 'shift zzz'

  _runtime-parse-error 'pushd x y'
  _runtime-parse-error 'pwd -x'

  _runtime-parse-error 'pp x foo a-x'

  _runtime-parse-error 'wait zzz'
  _runtime-parse-error 'wait %jobspec-not-supported'

  _runtime-parse-error 'unset invalid-var-name'
  _runtime-parse-error 'getopts 'hc:' invalid-var-name'
}

quoted-strings() {
  set +o errexit

  _error-case '"unterminated double'

  _error-case "'unterminated single"

  _error-case '
  "unterminated double multiline
  line 1
  line 2'

  _error-case "
  'unterminated single multiline
  line 1
  line 2"
}

braced-var-sub() {
  set +o errexit

  # These should have ! for a prefix query
  _error-case 'echo ${x*}'
  _error-case 'echo ${x@}'

  _error-case 'echo ${x.}'
}

cmd-parse() {
  set +o errexit

  _error-case 'FOO=1 break'
  _error-case 'break 1 2'

  _error-case 'x"y"() { echo hi; }'

  _error-case 'function x"y" { echo hi; }'

  _error-case '}'

  _error-case 'case foo in *) echo '
  _error-case 'case foo in x|) echo '

  _error-case 'ls foo|'
  _error-case 'ls foo&&'

  _error-case 'foo()'

  # parse_ignored
  _should-parse 'break >out'
  _ysh-parse-error 'break >out'

  # Unquoted (
  _error-case '[ ( x ]'
}

append() {
  # from spec/append.test.sh.  bash treats this as a runtime error, but it's a
  # parse error in OSH.
  _error-case 'a[-1]+=(4 5)'
}

redirect() {
  set +o errexit

  _error-case 'echo < <<'
  _error-case 'echo $( echo > >>  )'
}

simple-command() {
  set +o errexit

  _error-case 'PYTHONPATH=. FOO=(1 2) python'
  # not statically detected after dynamic assignment
  #_error-case 'echo foo FOO=(1 2)'

  _error-case 'PYTHONPATH+=1 python'

  # Space sensitivity: disallow =
  _error-case '=var'
  _error-case '=f(x)'

  _ysh-parse-error '=var'
  _ysh-parse-error '=f(x)'
}

assign() {
  set +o errexit
  _error-case 'local name$x'
  _error-case 'local "ab"'
  _error-case 'local a.b'

  _error-case 'FOO=1 local foo=1'

}

# I can't think of any other here doc error conditions except arith/var/command
# substitution, and unterminated.
here-doc() {
  set +o errexit

  # Arith in here doc
  _error-case 'cat <<EOF
$(( 1 * ))  
EOF
'

  # Varsub in here doc
  _error-case 'cat <<EOF
invalid: ${a!}
EOF
'

  _error-case 'cat <<EOF
$(for x in )
EOF
'
}

here-doc-delimiter() {
  set +o errexit

  # NOTE: This is more like the case where.
  _error-case 'cat << $(invalid here end)'

  # TODO: Arith parser doesn't have location information
  _error-case 'cat << $((1+2))'
  _error-case 'cat << a=(1 2 3)'
  _error-case 'cat << \a$(invalid)'

  # Actually the $invalid part should be highlighted... yeah an individual
  # part is the problem.
  #"cat << 'single'$(invalid)"
  _error-case 'cat << "double"$(invalid)'
  _error-case 'cat << ~foo/$(invalid)'
  _error-case 'cat << $var/$(invalid)'
}

args-parse-builtin() {
  set +o errexit
  _runtime-parse-error 'read -x'  # invalid
  _runtime-parse-error 'builtin read -x'  # ditto

  _runtime-parse-error 'read -n'  # expected argument for -n
  _runtime-parse-error 'read -n x'  # expected integer

  _runtime-parse-error 'set -o errexit +o oops'

  # not implemented yet
  #_error-case 'read -t x'  # expected floating point number

  # TODO:
  # - invalid choice
  # - Oil flags: invalid long flag, boolean argument, etc.
}

# aiding the transition
args-parse-more() {
  set +o errexit
  _runtime-parse-error 'set -z'
  _runtime-parse-error 'shopt -s foo'
  _runtime-parse-error 'shopt -z'
}

args-parse-main() {
  set +o errexit
  bin/osh --ast-format x

  bin/osh -o errexit +o oops
}

invalid-brace-ranges() {
  set +o errexit

  _error-case 'echo {1..3..-1}'
  _error-case 'echo {1..3..0}'
  _error-case 'echo {3..1..1}'
  _error-case 'echo {3..1..0}'
  _error-case 'echo {a..Z}'
  _error-case 'echo {a..z..0}'
  _error-case 'echo {a..z..-1}'
  _error-case 'echo {z..a..1}'
}

extra-newlines() {
  set +o errexit

  _error-case '
  for
  do
  done
  '

  _error-case '
  case
  in esac
  '

  _error-case '
  while
  do
  done
  '

  _error-case '
  if
  then
  fi
  '

  _error-case '
  if true
  then
  elif
  then
  fi
  '

  _error-case '
  case |
  in
  esac
  '

  _error-case '
  case ;
  in
  esac
  '

  _should-parse '
  if
  true
  then
  fi
  '

  _should-parse '
  while
  false
  do
  done
  '

  _should-parse '
  while
  true;
  false
  do
  done
  '

  _should-parse '
  if true
  then
  fi
  '

  _should-parse '
  while true;
        false
  do
  done
  '
}

ysh_string_literals() {
  set +o errexit

  # bash syntax
  _should-parse-here <<'EOF'
echo $'\u03bc'
EOF

  # Extension not allowed
  _ysh-parse-error-here <<'EOF'
echo $'\u{03bc}'
EOF

  # Bad syntax
  _ysh-parse-error-here <<'EOF'
echo $'\u{03bc'
EOF

  # Expression mode
  _ysh-parse-error-here <<'EOF'
const bad = $'\u{03bc'
EOF

  # Test single quoted
  _should-parse-here <<'EOF'
echo $'\z'
EOF
  _ysh-parse-error-here <<'EOF'
const bad = $'\z'
EOF

  # Octal not allowed
  _should-parse-here <<'EOF'
echo $'\101'
EOF
  _ysh-parse-error-here <<'EOF'
const bad = $'\101'
EOF

  # \xH not allowed
  _ysh-parse-error-here <<'EOF'
const bad = c'\xf'
EOF

  _should-parse 'echo "\z"'
  # Double quoted is an error
  _assert-status-2 +O parse_backslash -n -c 'echo parse_backslash "\z"'
  _ysh-parse-error 'echo "\z"'  # not in Oil
  _ysh-parse-error 'const bad = "\z"'  # not in expression mode

  # C style escapes not respected
  _should-parse 'echo "\u1234"'  # ok in OSH
  _ysh-parse-error 'echo "\u1234"'  # not in Oil
  _ysh-parse-error 'const bad = "\u1234"'

  _should-parse 'echo "`echo hi`"'
  _ysh-parse-error 'echo "`echo hi`"'
  _ysh-parse-error 'const bad = "`echo hi`"'

  _ysh-parse-error 'setvar x = "\z"'

  _ysh-parse-error-here <<'EOF'
setvar x = $'\z'
EOF
}

test_bug_1825_backslashes() {
  set +o errexit

  # Single backslash is accepted in OSH
  _should-parse-here <<'EOF'
echo $'trailing\
'
EOF

  # Double backslash is right in YSH
  _ysh-should-parse-here <<'EOF'
echo $'trailing\\
'
EOF

  # Single backslash is wrong in YSH
  _ysh-parse-error-here <<'EOF'
echo $'trailing\
'
EOF

  # Also in expression mode
  _ysh-parse-error-here <<'EOF'
setvar x = $'trailing\
'
EOF

}

parse_backticks() {
  set +o errexit

  # These are allowed
  _should-parse 'echo `echo hi`'
  _should-parse 'echo "foo = `echo hi`"'

  _assert-status-2 +O parse_backticks -n -c 'echo `echo hi`'
  _assert-status-2 +O parse_backticks -n -c 'echo "foo = `echo hi`"'
}

parse_dollar() {
  set +o errexit

  # The right way:
  #   echo \$
  #   echo \$:

  CASES=(
    'echo $'          # lex_mode_e.ShCommand
    'echo $:'

    'echo "$"'        # lex_mode_e.DQ
    'echo "$:"'

    'echo ${x:-$}'    # lex_mode_e.VSub_ArgUnquoted
    'echo ${x:-$:}'

    'echo "${x:-$}"'  # lex_mode_e.VSub_DQ
    'echo "${x:-$:}"'
  )
  for c in "${CASES[@]}"; do
    _should-parse "$c"
    _assert-status-2 +O parse_dollar -n -c "$c"
    _ysh-parse-error "$c"
  done
}

parse_dparen() {
  set +o errexit

  # Bash (( construct
  local bad

  bad='((1 > 0 && 43 > 42))'
  _should-parse "$bad"
  _ysh-parse-error "$bad"

  bad='if ((1 > 0 && 43 > 42)); then echo yes; fi'
  _should-parse "$bad"
  _ysh-parse-error "$bad"

  bad='for ((x = 1; x < 5; ++x)); do echo $x; done'
  _should-parse "$bad"
  _ysh-parse-error "$bad"

  _ysh-should-parse 'if (1 > 0 and 43 > 42) { echo yes }'

  # Accepted workaround: add space
  _ysh-should-parse 'if ( (1 > 0 and 43 > 42) ) { echo yes }'
}

invalid_parens() {
  set +o errexit

  # removed function sub syntax
  local s='write -- $f(x)'
  _parse-error "$s"
  _ysh-parse-error "$s"

  # requires parse_at
  local s='write -- @[sorted(x)]'
  _error-case "$s"  # this is a parse error, but BAD message!
  _ysh-should-parse "$s"

  local s='
f() {
  write -- @[sorted(x)]
}
'
  _error-case "$s"
  _ysh-should-parse "$s"

  # Analogous bad bug
  local s='
f() {
  write -- @sorted (( z ))
}
'
  _error-case "$s"
}

shell_for() {
  set +o errexit

  _error-case 'for x in &'

  _error-case 'for (( i=0; i<10; i++ )) ls'

  # ( is invalid
  _error-case 'for ( i=0; i<10; i++ )'

  _error-case 'for $x in 1 2 3; do echo $i; done'
  _error-case 'for x.y in 1 2 3; do echo $i; done'
  _error-case 'for x in 1 2 3; &'
  _error-case 'for foo BAD'

  # BUG fix: var is a valid name
  _should-parse 'for var in x; do echo $var; done'
}

#
# Different source_t variants
#

nested_source_argvword() {
  # source.ArgvWord
  _runtime-parse-error '
  code="printf % x"
  eval $code
  '
}

eval_parse_error() {
  _runtime-parse-error '
  x="echo )"
  eval $x
  '
}

trap_parse_error() {
  _runtime-parse-error '
  trap "echo )" EXIT
  '
}

proc_func_reserved() {
  ### Prevents confusion

  set +o errexit

  _error-case 'proc p (x) { echo hi }'
  _error-case 'func f (x) { return (x) }'
}

# Note: PROMPT_COMMAND and PS1 are hard to trigger in this framework

cases-in-strings() {
  set +o errexit

  cmd-parse
  simple-command
  command-sub
  redirect
  here-doc
  here-doc-delimiter
  append
  extra-newlines

  # Word
  word-parse
  array-literal
  patsub
  quoted-strings
  braced-var-sub

  # Arith
  arith-context
  arith-integration
  arith-expr

  bool-expr
  test-builtin
  printf-builtin
  other-builtins

  # frontend/args.py
  args-parse-builtin
  args-parse-main

  invalid-brace-ranges  # osh/braces.py

  append-builtin
  blocks
  parse_brace
  regex_literals
  proc_sig
  proc_arg_list
  ysh_string_literals
  test_bug_1825_backslashes

  parse_backticks
  parse_dollar
  parse_backslash
  parse_dparen

  shell_for
  parse_at
  invalid_parens
  nested_source_argvword

  eval_parse_error
  # should be status 2?
  #trap_parse_error

  proc_func_reserved
}

# Cases in their own file
cases-in-files() {
  # Don't fail
  set +o errexit

  for t in test/parse-errors/*.sh; do
    banner $t

    $SH $t

    local status=$?
    if test $status != 2; then
      die "Expected status 2, got $status"
    fi
  done

}

all() {
  cases-in-strings

  echo
  echo ----------------------
  echo

  cases-in-files
}

soil-run-py() {
  ### run with Python. output _tmp/other/parse-errors.txt

  all
}

soil-run-cpp() {
  ### Run with oils-for-unix

  ninja _bin/cxx-asan/osh
  SH=_bin/cxx-asan/osh all
}

release-oils-for-unix() {
  readonly OIL_VERSION=$(head -n 1 oil-version.txt)
  local dir="../benchmark-data/src/oils-for-unix-$OIL_VERSION"

  # Maybe rebuild it
  pushd $dir
  _build/oils.sh '' '' SKIP_REBUILD
  popd

  local suite_name=parse-errors-osh-cpp
  SH=$dir/_bin/cxx-opt-sh/osh \
    run-other-suite-for-release $suite_name all
}

run-for-release() {
  ### Test with bin/osh and the ASAN binary.

  run-other-suite-for-release parse-errors all

  release-oils-for-unix
}

"$@"
