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
# Extensions to pgen:
# - take tokens from a different lexer
# - callbacks to invoke the parser
#   - hm actually the "driver" can do this because it sees all the tokens?
#   - it's pushing rather than pulling.

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

parse-decls() {
  readonly -a decls=( 
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

  for expr in "${decls[@]}"; do
    ../bin/opyc parse-with oil.grammar arglist_input "$expr"
  done
}

all() {
  banner 'exprs'
  parse-exprs

  banner 'decls'
  parse-decls
}

"$@"
