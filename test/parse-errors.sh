#!/usr/bin/env bash
#
# Usage:
#   test/parse-errors.sh <function name>

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

is-oils-cpp() {
  case $SH in
    *_bin/*/osh)
      return 0
      ;;
  esac

  return 1
}

_error-case() {
  ### Assert that a parse error happens without running the program

  banner "$@"
  echo

  $SH -n -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

_error-case-here() { _error-case "$(cat)"; }

_error-case2() {
  ### An interface where you can pass flags like -O parse_backslash

  banner "$@"
  echo

  $SH "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

_error-case2-here() { _error-case2 "$@" -c "$(cat)"; }

_should-parse() {
  banner "$@"
  echo
  $SH -n -c "$@"

  local status=$?
  if test $status != 0; then
    die "Expected it to parse"
  fi
}

_should-parse-here() { _should-parse "$(cat)"; }

_runtime-parse-error() {
  ### Assert that a parse error happens at runtime

  if is-oils-cpp; then
    echo 'skipping _runtime-parse-error'
    return
  fi

  banner "$@"
  echo
  $SH -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

_oil-should-parse() {
  banner "$@"
  echo
  $SH -O oil:all -n -c "$@"

  local status=$?
  if test $status != 0; then
    die "Expected it to parse"
  fi
}

_oil-parse-error() {
  ### Assert that a parse error happens with Oil options on

  if is-oils-cpp; then
    echo 'skipping _oil-parse-error'
    return
  fi
   
  banner "$@"
  echo
  $SH -O oil:all -c "$@"

  local status=$?
  if test $status != 2; then
    die "Expected status 2, got $status"
  fi
}

# So we can write single quoted strings in an easier way
_oil-parse-error-here() { _oil-parse-error "$(cat)"; }

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

  # From wild/src/distro/portage/bin/helper-functions.sh
  _error-case '$(( ${var} = fd ))'

  # Invalid assignments
  _error-case '$(( x+1 = 42 ))'
  _error-case '$(( (x+42)++ ))'
  _error-case '$(( ++(x+42) ))'

  # Note these aren't caught because '1' is an ArithWord like 0x$x
  _error-case '$(( 1 = foo ))'
  _error-case '$(( 1++ ))'
  _error-case '$(( ++1 ))'
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

  _error-case 'ls foo|'
  _error-case 'ls foo&&'

  _error-case 'foo()'

  # parse_ignored
  _should-parse 'break >out'
  _oil-parse-error 'break >out'

  if is-oils-cpp; then
    echo 'Skipping some cmd-parse cases on oils_cpp'
    return
  fi

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

oil-language() {
  set +o errexit

  if is-oils-cpp; then
    echo 'Skipping oil-language'
    return
  fi

  # Unterminated
  _oil-parse-error 'var x = 1 + '

  _oil-parse-error 'var x = * '

  _oil-parse-error 'var x = @($(cat <<EOF
here doc
EOF
))'

  _oil-parse-error 'var x = $(var x = 1))'
}

append-builtin() {
  set +o errexit

  # Unterminated
  _runtime-parse-error 'append'
  _runtime-parse-error 'append invalid-'
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

proc_arg_list() {
  set +o errexit

  if is-oils-cpp; then
    echo 'Skipping proc_arg_list cases on oils_cpp'
    return
  fi

  _should-parse 'json write (x)'

  _should-parse 'echo $(json write (x))'  # relies on lexer.PushHint()

  # nested expr -> command -> expr
  _should-parse 'var result = $(json write (x))'

  _should-parse 'json write (x, y); echo hi'

  # named arg
  _should-parse '
json write (x, name = "value")
echo hi
'

  # with block on same line
  _oil-should-parse 'json write (x) { echo hi }'

  # with block
  _oil-should-parse '
json write (x) {
  echo hi
}'

  # multiple lines
  _should-parse 'json write (
    x,
    y,
    z
  )'


  # can't be empty
  _oil-parse-error 'json write ()'
  _oil-parse-error 'json write ( )'

  # should have a space
  _oil-parse-error 'json write(x)'
  _oil-parse-error 'json write()'
  _oil-parse-error 'f(x)'  # test short name
}

regex_literals() {
  set +o errexit

  if is-oils-cpp; then
    return
  fi

  _oil-parse-error 'var x = / ! /'
  _oil-should-parse 'var x = / ![a-z] /'
  _oil-should-parse 'var x = / !d /'

  _oil-parse-error 'var x = / !! /'

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
  # old syntax
  _oil-parse-error '= 5 mod 3'

  _oil-parse-error '= >>='
  _oil-parse-error '= %('

  # Singleton tuples
  _oil-parse-error '= 42,'
  _oil-parse-error '= (42,)'

  # Disallowed unconditionally
  _oil-parse-error '=a'

}

oil_expr_more() {
  set +o errexit

  # user must choose === or ~==
  _oil-parse-error 'if (5 == 5) { echo yes }'
}

oil_hay_assign() {
  set +o errexit

  if is-oils-cpp; then
    return
  fi

  _oil-parse-error '
name=val
'

  _oil-parse-error '
name = val
'

  _oil-parse-error '
rule {
  x = 42
}
'

  _oil-parse-error '
RULE {
  x = 42
}
'

  _oil-should-parse '
Rule {
  x = 42
}
'

  _oil-should-parse '
Rule X Y {
  x = 42
}
'

  _oil-should-parse '
RULe {   # inconsistent but OK
  x = 42
}
'

  _oil-parse-error '
hay eval :result {

  Rule {
    foo = 42
  }

  bar = 43   # parse error here
}
'

  _oil-parse-error '
hay define TASK

TASK build {
  foo = 42
}
'

  # CODE node nested inside Attr node.
  _oil-parse-error '
hay define Package/TASK

Package libc {
  TASK build {
    foo = 42
  }
}
'
}


oil_string_literals() {
  set +o errexit

  # OK in OSH
  _should-parse-here <<'EOF'
echo $'\u{03bc'
EOF
  # Not with parse_backslash
  _error-case2-here +O parse_backslash -n <<EOF
echo parse_backslash $'\u{03bc'
EOF
  # Not in Oil
  _oil-parse-error-here <<'EOF'
const bad = $'\u{03bc'
EOF

  # Test single quoted
  _should-parse-here <<'EOF'
echo $'\z'
EOF
  _oil-parse-error-here <<'EOF'
const bad = $'\z'
EOF

  # Octal not allowed
  _should-parse-here <<'EOF'
echo $'\101'
EOF
  _oil-parse-error-here <<'EOF'
const bad = $'\101'
EOF

  # \xH not allowed
  _oil-parse-error-here <<'EOF'
const bad = c'\xf'
EOF

  _should-parse 'echo "\z"'
  # Double quoted is an error
  _error-case2 +O parse_backslash -n -c 'echo parse_backslash "\z"'
  _oil-parse-error 'echo "\z"'  # not in Oil
  _oil-parse-error 'const bad = "\z"'  # not in expression mode

  # C style escapes not respected
  _should-parse 'echo "\u1234"'  # ok in OSH
  _oil-parse-error 'echo "\u1234"'  # not in Oil
  _oil-parse-error 'const bad = "\u1234"'

  _should-parse 'echo "`echo hi`"'
  _oil-parse-error 'echo "`echo hi`"'
  _oil-parse-error 'const bad = "`echo hi`"'

  # We want these to be tested under OSH, but they won't work under Oil native!
  if is-oils-cpp; then
    echo 'Skipping some oil_string_literals cases on oils_cpp'
    return
  fi

  _oil-parse-error 'setvar x = "\z"'

  _oil-parse-error <<'EOF'
setvar x = $'\z'
EOF

}

parse_backticks() {
  set +o errexit

  # These are allowed
  _should-parse 'echo `echo hi`'
  _should-parse 'echo "foo = `echo hi`"'

  _error-case2 +O parse_backticks -n -c 'echo `echo hi`'
  _error-case2 +O parse_backticks -n -c 'echo "foo = `echo hi`"'
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
    _error-case2 +O parse_dollar -n -c "$c"
    _oil-parse-error "$c"
  done
}

# Backslash in UNQUOTED context
parse_backslash() {
  set +o errexit

  _oil-should-parse 'echo \('
  _oil-should-parse 'echo \;'
  _oil-should-parse 'echo ~'
  _oil-should-parse 'echo \!'  # history?

  _oil-should-parse 'echo \%'  # job ID?  I feel like '%' is better
  _oil-should-parse 'echo \#'  # comment

  _oil-parse-error 'echo \.'
  _oil-parse-error 'echo \-'
  _oil-parse-error 'echo \/'

  _oil-parse-error 'echo \a'
  _oil-parse-error 'echo \Z'
  _oil-parse-error 'echo \0'
  _oil-parse-error 'echo \9'

  _should-parse 'echo \. \- \/ \a \Z \0 \9'
}

parse_dparen() {
  set +o errexit

  # Bash (( construct
  local bad

  bad='((1 > 0 && 43 > 42))'
  _should-parse "$bad"
  _oil-parse-error "$bad"

  bad='if ((1 > 0 && 43 > 42)); then echo yes; fi'
  _should-parse "$bad"
  _oil-parse-error "$bad"

  bad='for ((x = 1; x < 5; ++x)); do echo $x; done'
  _should-parse "$bad"
  _oil-parse-error "$bad"

  if is-oils-cpp; then
    echo 'Skipping parse_dparen cases'
    return
  fi
  _oil-should-parse 'if (1 > 0 and 43 > 42) { echo yes }'

  # Accepted workaround: add space
  _oil-should-parse 'if ( (1 > 0 and 43 > 42) ) { echo yes }'
}

oil_to_make_nicer() {
  set +o errexit

  # expects expression on right
  _oil-parse-error '='
  _oil-parse-error '_'

  # What about \u{123} parse errors
  # I get a warning now, but parse_backslash should give a syntax error
  # _oil-parse-error "x = c'\\uz'"

  # Dict pair split
  _oil-parse-error 'const d = { name:
42 }'

  #_oil-parse-error ' d = %{}'
}

parse_at() {
  set +o errexit

  _oil-parse-error 'echo @'
  _oil-parse-error 'echo @@'
  _oil-parse-error 'echo @{foo}'
  _oil-parse-error 'echo @/foo/'
  _oil-parse-error 'echo @"foo"'
}

invalid_parens() {
  set +o errexit

  if is-oils-cpp; then
    echo 'skipping invalid_parens on oils_cpp'
    return
  fi

  # compatible extension in both langauges
  local s='write -- $f(x)'
  _should-parse "$s"
  _oil-should-parse "$s"

  # requires parse_at
  local s='write -- @sorted(x)'
  _error-case "$s"  # this is a parse error, but BAD message!
  _oil-should-parse "$s"

  local s='
f() {
  write -- @sorted(x)
}
'
  _error-case "$s"
  _oil-should-parse "$s"

  # Analogous bad bug
  local s='
f() {
  write -- @sorted (( z ))
}
'
  _error-case "$s"
}

oil_nested_proc() {
  set +o errexit

  _oil-parse-error 'proc p { echo 1; proc f { echo f }; echo 2 }'
  _oil-parse-error 'proc p { echo 1; +weird() { echo f; }; echo 2 }'

  # ksh function
  _oil-parse-error 'proc p { echo 1; function f { echo f; }; echo 2 }'

  _oil-parse-error 'f() { echo 1; proc inner { echo inner; }; echo 2; }'

  if is-oils-cpp; then
    echo 'skipping oil_nested_proc'  # TODO: re-enable with pgen2
    return
  fi

  # shell nesting is still allowed
  _should-parse 'f() { echo 1; g() { echo g; }; echo 2; }'

  _oil-should-parse 'proc p() { shopt --unset errexit { false hi } }'
}

oil_var_decl() {
  set +o errexit

  _oil-parse-error '
  proc p(x) {
    echo hi
    var x = 2  # Cannot redeclare param
  }
  '

  _oil-parse-error '
  proc p {
    var x = 1
    echo hi
    var x = 2  # Cannot redeclare local
  }
  '

  _oil-parse-error '
  proc p {
    var x = 1
    echo hi
    const x = 2  # Cannot redeclare local
  }
  '

  _oil-parse-error '
  proc p(x, :out) {
    var out = 2   # Cannot redeclare out param
  }
  '

  _oil-parse-error '
  proc p {
    var out = 2   # Cannot redeclare out param
    cd /tmp { 
      var out = 3
    }
  }
  '

  # TODO: We COULD disallow this, but not sure it's necessary
  if false; then
    _oil-parse-error '
    proc p(x, :out) {
      var __out = 2   # Cannot redeclare out param
    }
    '
  fi

  if is-oils-cpp; then
    echo 'skipping oil_var_decl'  # TODO: re-enable with pgen2
    return
  fi

  _oil-should-parse '
  var x = 1
  proc p {
    echo hi
    var x = 2
  }

  proc p2 {
    var x = 3
  }
  '
}

oil_place_mutation() {
  set +o errexit

  _oil-parse-error '
  proc p(x) {
    var y = 1
    setvar L = "L"  # ERROR: not declared
  }
  '

  _oil-parse-error '
  proc p(x) {
    const c = 123
    setvar c = 42  # ERROR: cannot modify constant
  }
  '

  if is-oils-cpp; then
    echo 'skipping oil_place_mutation'  # TODO: re-enable with pgen2
    return
  fi

  _oil-should-parse '
  proc p(x) {
    setvar x = "X"  # is mutating params allowed?  I guess why not.
  }
  '
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

oil_case() {
  set +o errexit

  _oil-should-parse '
  case $foo {
    (*.py) echo "python" ;;
  }
  '

  _oil-should-parse '
  case "foo" {
    (*.py) echo "python" ;;
  }
  '

  # parse_bare_word
  _oil-parse-error '
  case foo {
    (*.py) echo "python" ;;
  }
  '

  # parse_sloppy_case

  _oil-parse-error '
  case $x {
    (*.py) echo "python" ;;
    *.sh) echo "shell" ;;
  }
  '

}

oil_for() {
  set +o errexit

  if is-oils-cpp; then
    echo 'skipping oil_for'
    return
  fi

  _oil-should-parse '
  for x in (obj) {
    echo $x
  }
  '

  _oil-parse-error '
  for x in (obj); do
    echo $x
  done
  '

  _oil-should-parse '
  for x, y in SPAM EGGS; do
    echo $x
  done
  '

  # Bad loop variable name
  _oil-parse-error '
  for x-y in SPAM EGGS; do
    echo $x
  done
  '

  # Too many indices
  _oil-parse-error '
  for x, y, z in SPAM EGGS; do
    echo $x
  done
  '

  _oil-parse-error '
  for w, x, y, z in SPAM EGGS; do
    echo $x
  done
  '

  # Old style
  _oil-should-parse '
  for x, y in SPAM EGGS
  do
    echo $x
  done
  '

  # for shell compatibility, allow this
  _oil-should-parse 'for const in (x) { echo $var }'
}

oil_for_parse_bare_word() {
  set +o errexit

  if is-oils-cpp; then
    echo 'skipping oil_for'
    return
  fi

  _oil-parse-error '
  for x in bare {
    echo $x
  }
  '

  _oil-should-parse '
  for x in a b {
    echo $x
  }
  '

  _oil-should-parse '
  for x in *.py {
    echo $x
  }
  '

  _oil-should-parse '
  for x in "quoted" {
    echo $x
  }
  '
}

oil_issue_1118() {
  set +o errexit

  if is-oils-cpp; then
    echo 'skipping oil_issue_1118'
    return
  fi

  # Originally pointed at 'for'
  _oil-parse-error '
  var snippets = [{status: 42}]
  for snippet in (snippets) {
    if (snippet["status"] === 0) {
      echo hi
    }

    # The $ causes a wierd error
    if ($snippet["status"] === 0) {
      echo hi
    }
  }
  '

  # Issue #1118
  # pointed at 'var' in count
  _oil-parse-error '
  var content = [ 1, 2, 4 ]
  var count = 0

  # The $ causes a weird error
  while (count < $len(content)) {
    setvar count += 1
  }
  '
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
# Note: PROMPT_COMAND and PS1 are hard to trigger in this framework

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

  oil-language  # oil_lang/
  append-builtin
  blocks
  parse_brace
  regex_literals
  proc_sig
  proc_arg_list
  oil_expr
  oil_expr_more
  oil_hay_assign
  oil_string_literals
  parse_backticks
  parse_dollar
  parse_backslash
  parse_dparen
  oil_to_make_nicer
  oil_nested_proc
  oil_var_decl
  oil_place_mutation
  oil_case
  oil_for
  oil_for_parse_bare_word
  oil_issue_1118

  shell_for
  parse_at
  invalid_parens
  nested_source_argvword
}

# Cases in their own file
cases-in-files() {
  # Don't fail
  set +o errexit

  for t in test/parse-errors/*.sh; do
    banner $t

    if is-oils-cpp; then
      case $t in
        */01-bad-func.sh)
          echo "Skipping file $t for oils_cpp"
          continue
          ;;
      esac
    fi


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
  ### Run with oils_cpp

  ninja _bin/cxx-asan/osh

  ASAN_OPTIONS='detect_leaks=0' SH=_bin/cxx-asan/osh all
}

release-oils-for-unix() {
  readonly OIL_VERSION=$(head -n 1 oil-version.txt)
  local dir="../benchmark-data/src/oils-for-unix-$OIL_VERSION"

  # Maybe rebuild it
  pushd $dir
  _build/oils.sh '' '' SKIP_REBUILD
  popd

  local out=_tmp/other/parse-errors-osh-cpp.txt
  SH=$dir/_bin/cxx-opt-sh/osh \
    run-other-suite-for-release parse-errors all $out
}

run-for-release() {
  ### Test with bin/osh and the ASAN binary.

  run-other-suite-for-release parse-errors all

  release-oils-for-unix
}

"$@"
