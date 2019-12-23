#!/bin/bash
#
# Usage:
#   ./parse-errors.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# Run with SH=bash too
SH=${SH:-bin/osh}

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_error-case() {
  ### Assert that a parse error happens without running the program

  banner "$@"
  echo

  # TODO: Change when osh_parse supports -n -c.

  #$SH -n -c "$@"
  $SH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

_runtime-parse-error() {
  ### Assert that a parse error happens at runtime

  case $SH in
    *osh_parse.asan)
      echo 'skipping _runtime-parse-error'
      return
      ;;
  esac

  banner "$@"
  echo
  $SH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

_oil-parse-error() {
  ### Assert that a parse error happens with Oil options on

  case $SH in
    *osh_parse.asan)
      echo 'skipping _oil-parse-error'
      return
      ;;
  esac

  banner "$@"
  echo
  $SH -O oil:all -c "$@"

  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

# All in osh/word_parse.py
patsub() {
  set +o errexit

  _error-case 'echo ${x/}'  # pattern must not be empty

  # These are a little odd
  _error-case 'echo ${x//}'
  #_error-case 'echo ${x///}'

  #_error-case 'echo ${x/foo}'
  #_error-case 'echo ${x//foo}'

  # This should be a different error?  It should be an empty pattern?
  _error-case 'echo ${x///foo}'

  # Newline in replacement pattern
  #_error-case 'echo ${x//foo/replace
#}'
  #_error-case 'echo ${x//foo/replace$foo}'
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

  # Disable Oil stuff for osh_parse.asan
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

  # "Can't assign to None" is misleading.
  # From wild/src/distro/portage/bin/helper-functions.sh
  _error-case '$(( ${var} = fd ))'
}

command-sub() {
  set +o errexit
  _error-case ' 
    echo line 2
    echo $( echo '
  _error-case ' 
    echo line 2
    echo ` echo '
  # Both unclosed
  _error-case '
    echo line 2
    echo ` echo \` '

  # Only the inner one is unclosed
  _error-case '
    echo line 2
    echo ` echo \`unclosed ` '
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

  _runtime-parse-error 'repr foo a-x'

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
  _error-case 'break >out'

  _error-case 'for x in &'

  _error-case 'for (( i=0; i<10; i++ )) ls'

  _error-case 'for $x in 1 2 3; do echo $i; done'
  _error-case 'for x.y in 1 2 3; do echo $i; done'
  _error-case 'for x in 1 2 3; &'
  _error-case 'for foo BAD'

  _error-case 'x"y"() { echo hi; }'

  _error-case 'function x"y" { echo hi; }'

  _error-case '}'

  _error-case 'case foo in *) echo '

  _error-case 'ls foo|'
  _error-case 'ls foo&&'

  _error-case 'foo()'

  # Unquoted (.  What happened here?
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

  # TODO: opy/opy_main.py uses OilFlags, which has Go-like boolean syntax
}

strict_backslash_warnings() {
  echo $'\A'
  echo -e '\A'
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

oil-language() {
  set +o errexit

  # disabled until we port the parser
  case $SH in *osh_parse.asan) return ;; esac

  # Unterminated
  _error-case 'var x = 1 + '

  _error-case 'var x = * '

  _error-case 'var x = @($(cat <<EOF
here doc
EOF
))'

  _error-case 'var x = $(var x = 1))'
}

push-builtin() {
  set +o errexit

  # Unterminated
  _runtime-parse-error 'push'
  _runtime-parse-error 'push invalid-'
  #_error-case 'push notarray'  # returns status 1
}

blocks() {
  set +o errexit

  _oil-parse-error '>out { echo hi }'
  _oil-parse-error 'a=1 b=2 { echo hi }'
  _oil-parse-error 'break { echo hi }'
  # missing semicolon
  _oil-parse-error 'cd / { echo hi } cd /'
}

parse_brace() {
  # missing space
  _oil-parse-error 'if test -f foo{ echo hi }'

}

proc_sig() {
  set +o errexit
  _oil-parse-error 'proc f[] { echo hi }'
  _oil-parse-error 'proc : { echo hi }'
  _oil-parse-error 'proc foo::bar { echo hi }'
}

regex_literals() {
  set +o errexit

  # missing space between rangfes
  _oil-parse-error 'var x = /[a-zA-Z]/'
  _oil-parse-error 'var x = /[a-z0-9]/'

  _oil-parse-error 'var x = /[a-zz]/'

  # can't have multichar ranges
  _oil-parse-error "var x = /['ab'-'z']/"

  # range endpoints must be constants
  _oil-parse-error 'var x = /[$a-${z}]/'

  # These are too long too
  _oil-parse-error 'var x = /[abc]/'

  # Single chars not allowed, should be /['%_']/
  _oil-parse-error 'var x = /[% _]/'

}

oil_expr() {
  set +o errexit
  # % is not a token
  _oil-parse-error '= 5 % 3'
  _oil-parse-error '= >>='
  _oil-parse-error '= %('

  # Singleton tuples
  _oil-parse-error '= 42,'
  _oil-parse-error '= (42,)'

  # parse_equals
  _oil-parse-error '=a'
  _oil-parse-error 'name=val'
}


cases-in-strings() {
  set +o errexit

  cmd-parse
  simple-command
  command-sub
  redirect
  here-doc
  here-doc-delimiter
  append

  # Word
  word-parse
  array-literal
  patsub
  quoted-strings
  braced-var-sub

  # Arith
  arith-context
  arith-expr

  bool-expr
  test-builtin
  printf-builtin
  other-builtins

  # frontend/args.py
  args-parse-builtin
  args-parse-main

  invalid-brace-ranges  # osh/braces.py

  oil-language  # oil_lang/
  push-builtin
  blocks
  parse_brace
  regex_literals
  proc_sig
  oil_expr
}

# Cases in their own file
cases-in-files() {
  # Don't fail
  set +o errexit

  for t in test/parse-errors/*.sh; do
    banner $t
    $SH $t
  done
}

all() {
  cases-in-strings

  echo
  echo ----------------------
  echo

  cases-in-files

  # Always passes
  return 0
}

run-for-release() {
  ### Test with bin/osh and the ASAN binary.

  run-other-suite-for-release parse-errors all

  # Done in _oil-native-build
  #build/mycpp.sh compile-osh-parse-asan

  # TODO: osh_parse should accept -n -c
  local out=_tmp/other/parse-errors-oil-native.txt
  ASAN_OPTIONS=detect_leaks=0 SH=_bin/osh_parse.asan \
    run-other-suite-for-release parse-errors all $out
}

"$@"
