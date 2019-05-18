#!/bin/bash
#
# Figuring out if we can use pgen2 for Oil syntax.
#
# Usage:
#   ./oil-syntax.sh <function name>

# Things to parse:
# - Expressions
#   - same difficulties in shell arith parser: f(x,y), a[i+1], b ? a : b
#     - and our function calls will be more elaborate
#   - python features:
#     - list and dict comprehensions
#     - a not in b, a is not b
#     - a[1, 2] -- this is equivalent to tuple indexing?
#   - function literals, including the arg list syntax (which is complex)
#   - dict, set, tuple, list literals, which C parser doesn't have
#   - string and array literals, which need to invoke WordParser
#     - "${foo:-}" and [a b "$foo"]
#     - although disallow ${} and prefer $[] for expressions?
#   - including regex dialect?  (But that changes lexer modes)
# - Optional type declarations with MyPy-ish syntax
#
# Entry points:
# - var a = ...             # once you see var/const/set, switch
# - proc copy [src dest] {  # once you see proc, switch.  { switches back.
# - func f(name Str, age List<int>) List<int> {     # ditto, { switches back.
# - $stringfunc(x, y)       # once you see SmipleVarSub and look ahead to '('
#                           # then switch
# - @arrayfunc(x, y)        # hm this is harder?  Because oil-splice is
#                           # detected
#
# Exit Points:
# - a = [foo bar] but NOT a = List []   # array literals go back to word parser
# - a = '
#   a = $'   or %c''
#   a = '''  # multiline?               # string literals back to word parser
# - block {                             # goes back to CommandParser
#
# Extensions to pgen:
# - take tokens from a different lexer
# - callbacks to invoke the parser
#   - hm actually the "driver" can do this because it sees all the tokens?
#   - it's pushing rather than pulling.
#
# TODO: 
# - get rid of cruft and see what happens
# - write exhaustive test cases and get rid of arglist problem
#   - although you are going to change it to be honest
# - hook it up to Zephyr ASDL.  Create a convert= function.
#   - This is called on shift() and pop() in pgen2/parse.py.  You can look
#     at (typ, value) to figure out what to put in the LST.
#
# Construct an ambiguous grammar and see what happens?

set -o nounset
set -o pipefail
set -o errexit

banner() {
  echo
  echo "----- $@ -----"
  echo
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
    ../bin/opyc parse-with oil.grammar eval_input "$expr"
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
    ../bin/opyc parse-with oil.grammar arglist_input "$expr"
  done
}

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
    ../bin/opyc parse-with oil.grammar type_input "$expr"
  done
}


all() {
  banner 'exprs'
  parse-exprs

  banner 'arglists'
  parse-arglists

  banner 'types'
  parse-types
}

# Hm Python 3 has type syntax!  But we may not use it.
# And it has async/await.
# And walrus operator :=.
# @ matrix multiplication operator.

diff-grammars() {
  wc -l ~/src/languages/Python-*/Grammar/Grammar

  cdiff ~/src/languages/Python-{2.7.15,3.6.7}/Grammar/Grammar
}

"$@"
