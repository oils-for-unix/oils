#!/bin/bash
#
# Proof of concept for pgen2 and Oil syntax.
#
# Usage:
#   ./pgen2-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

banner() {
  echo
  echo "----- $@ -----"
  echo
}

grammar-gen() {
  PYTHONPATH=. oil_lang/grammar_gen.py "$@"
}

# Build the grammar and parse code.  Outside of the Oil binary.
parse() {
  grammar-gen parse "$@"
}

parse-exprs() {
  readonly -a exprs=(
    '1+2'
    '1 + 2 * 3'
    'x | ~y'
    '1 << x'
    'a not in b'
    'a is not b'
    '[x for x in a]'
    '[1, 2]'
    '{myset, a}'
    '{mydict: a, key: b}'
    '{x: dictcomp for x in b}'
    'a[1,2]'
    'a[i:i+1]'
  )
  for expr in "${exprs[@]}"; do
    parse pgen2/oil.grammar eval_input "$expr"

    # TODO: switch to Oil
    #parse $OIL_GRAMMAR test_input "$expr"
  done
}

parse-arglists() {
  readonly -a arglists=( 
    'a'
    'a,b'
    'a,b=1'
    # Hm this parses, although isn't not valid
    'a=1,b'
    'a, *b, **kwargs'

    # Hm how is this valid?

    # Comment:
    # "The reason that keywords are test nodes instead of NAME is that using
    # NAME results in an ambiguity. ast.c makes sure it's a NAME."
    #
    # Hm is the parsing model powerful enough?   
    # TODO: change it to NAME and figure out what happens.
    #
    # Python 3.6's grammar has more comments!

    # "test '=' test" is really "keyword '=' test", but we have no such token.
    # These need to be in a single rule to avoid grammar that is ambiguous
    # to our LL(1) parser. Even though 'test' includes '*expr' in star_expr,
    # we explicitly match '*' here, too, to give it proper precedence.
    # Illegal combinations and orderings are blocked in ast.c:
    # multiple (test comp_for) arguments are blocked; keyword unpackings
    # that precede iterable unpackings are blocked; etc.

    'a+1'
  )

  for expr in "${arglists[@]}"; do
    parse pgen2/oil.grammar arglist_input "$expr"
  done
}

# NOTE: Unused small demo.
parse-types() {
  readonly -a types=(
    'int'
    'str'
    'List<str>'
    'Tuple<str, int, int>'
    'Dict<str, int>'
    # aha!  Tokenizer issue
    #'Dict<str, Tuple<int, int>>'

    # Must be like this!  That's funny.  Oil will have lexer modes to solve
    # this problem!
    'Dict<str, Tuple<int, int> >'
  )
  for expr in "${types[@]}"; do
    parse pgen2/oil.grammar type_input "$expr"
  done
}

readonly OIL_GRAMMAR='oil_lang/grammar.pgen2'

calc-test() {
  local -a exprs=(
    'a + 2'
    '1 + 2*3/4'  # operator precedence and left assoc

    # Tuple
    'x+1, y+1'
    #'(x+1, y+1)'  # TODO: atom

    # Associative
    '-1+2+3'
    '4*5*6'
    'i % n'
    'i % n / 2'

    # Uses string tokens
    #'"abc" + "def"'

    '2 ^ 3 ^ 4'  # right assoc
    'f(1)'
    'f(1, 2, 3)'

    'f(a[i], 2, 3)'
    'f(a[i, j], 2, 3)'

    'f(x)^3'
    'f(x)[i]^3'

    #'x < 3 and y <= 4'

    # bad token
    #'a * 3&4'
  )

  for e in "${exprs[@]}"; do
    echo "$e"
    parse $OIL_GRAMMAR eval_input "$e"
  done
}

oil-productions() {
  parse $OIL_GRAMMAR oil_var 'a = 1;'
  parse $OIL_GRAMMAR oil_var 'a Int = 2;'

  # Invalid because += now allowed
  #parse $OIL_GRAMMAR oil_var 'a += 1;'

  parse $OIL_GRAMMAR oil_setvar 'x = 3;'
  parse $OIL_GRAMMAR oil_setvar 'x += 4;'

  # Invalid because type expression isn't allowed (it could conflict)
  #parse $OIL_GRAMMAR oil_setvar 'x Int += 4;'
}

mode-test() {
  # Test all the mode transitions
  local -a exprs=(
    # Expr -> Array
    # TODO: how is OilOuter different than Array
    '@[]'
    'x + @[a b] + y'

    # Expr -> Command
    # Hm empty could be illegal?
    '$[]'
    'x + $[hi there] + y'

    # Expr -> Expr
    '$(x)'
    # NOTE: operator precedence is respected here!
    'x + $(f(y) - 3) * 4'
    # Expr -> Expr even though we saw )
    #'$(f(x, y) + (1 * 3))'

    # Expr -> OilVS
    #'${}'  # syntax error
    '${x}'
    # This will work when we add | to grammar
    #'x + ${p|html} + y'

    # Expr -> Regex
    #'$/ /'
    'x + $/ mypat / + y'  # syntactically valid, semantically invalid

    # Expr -> OilDQ
    '"hello \$"'
    'x + "hello \$" + y'
    # TODO: Also do every other kind of string:
    # r'raw'   r"raw $sub"   '''   """   r'''   r"""

    # Regex -> CharClass
    #'$/ any* "." [a-z A-Z _] [a-z A-Z _ 0-9]+ /'
    '$/ "." [a-z A-Z _] [a-z A-Z _ 0-9] /'
    '$/ a [b] c /'

    # Array -> CharClass  
    '@[one two *.[c h] *.[NOT c h] ]'

    # Expr -> Array -> CharClass  
    'left + @[one two *.[c h] ] + right'
    # Array brace sub.  Not PARSED yet, but no lexer mode change AFAICT
    #'@[ -{one,two}- *.[c h] ]'

    ## OilDQ -> Expr
    '"var expr $(2 + 3)"'

    ## OilDQ -> Command
    '"command $[echo hi]"'

    # OilDQ -> OilVS -- % is not an operator
    #'"quoted ${x %02d}"'
    '"quoted ${x}"'

  #)
  #local -a exprs=(

  )

  for e in "${exprs[@]}"; do
    echo "$e"
    parse $OIL_GRAMMAR eval_input "$e"
  done

  # Command stuff.  TODO: we don't have a parser for this!
  # Maybe add 'echo' do everything?
  exprs+=(
    #'x = $[echo one; echo *.[c h] ]'

    # Command -> Expr (PROBLEM: requires lookahead to =)
    'x = a + b'
    'var x = a + b'
    'setvar x = a + b'

    # Command -> Expr
    'echo $(a + b)'
    'echo ${x|html}'

    # Command -> Expr
    'echo $stringfunc(x, y)'
    'echo @arrayfunc(x, y)'

    # The signature must be parsed expression mode if it have
    # defaults.
    'func foo(x Int, y Int = 42 + 1) Int {
       echo $x $y
     }
    '
    # I guess [] is parsed in expression mode too.  It's a very simple grammar.
    # It only accepts strings.  Maybe there is a special "BLOCK" var you can
    # evaluate.
    'proc copy [src dest="default $value"] {
       echo $src $dest
     }
    '

    'if (x > 1) { echo hi }'

    'while (x > 0) {
       set x -= 1
     }
    '
    'for (x in y) {  # "var" is implied; error if x is already defined?
       echo $y
     }
    '
    'for (i = 0; i < 10; ++i) {
       echo $i
     }
    '
    'switch (i+1) {
     case 1:
       echo "one"
     case 2:
       echo "two"
     }
    '
    'match (x) {
     1 { echo "one" }
     2 { echo "two" }
     }
    '

    # Command -> OilVS -- % is not an operator
    'echo ${x %02d}'

    # Command -> CharClass is DISALLOWED.  Must go through array?
    # @() could be synonym for array expression.
    # Although if you could come up with a custom syntax error for this: it
    # might be OK.
    # a[x] = 1
    #'echo *.[c h]'
    #
    # I think you could restrict the first words
  )

  # I don't think these are essential.
  local -a deferred=(
    # Expr -> Command (PROBLEM: mode is grammatical; needs state machine)
    'x = func(x, y={}) {
      echo hi
    }
    '

    # Expr -> Command (PROBLEM: ditto)
    # This one is even harder, because technically the expression on the left
    # could have {}?  Or we can ban that in patterns?
    'x = match(x) {
      1 { echo one }
      2 { echo two }
    }
    '

    # stays in Expr for comparison
    'x = match(x) {
      1 => "one"
      2 => "two"
    }
    '
  )
}

enum-test() {
  readonly -a enums=(
    # second alternative
    'for 3 a'
    'for 3 { a, b }'
    'for 3 a { a, b }'
    #'for'
    #'a'
  )
  for expr in "${enums[@]}"; do
    parse pgen2/enum.grammar eval_input "$expr"
  done
}

all() {
  banner 'exprs'
  parse-exprs

  #banner 'arglists'
  #parse-arglists

  banner 'calc'
  calc-test

  banner 'mode-test'
  mode-test

  banner 'oil-productions'
  oil-productions

  # enum-test doesn't work?
}

# Hm Python 3 has type syntax!  But we may not use it.
# And it has async/await.
# And walrus operator :=.
# @ matrix multiplication operator.

diff-grammars() {
  wc -l ~/src/languages/Python-*/Grammar/Grammar

  cdiff ~/src/languages/Python-{2.7.15,3.7.3}/Grammar/Grammar
}

stdlib-test() {
  pgen2 stdlib-test
}

"$@"
