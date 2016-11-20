#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
"""
tokens.py - Token, Word, and AST Node ID definitions.
"""

import json
import re
import sys

from core import util


_TOKEN_TYPE_TO_KIND = {}  # type: dict


class Token(object):
  def __init__(self, type, val):
    self.type = type
    self.val = val

    # In C++, instead of val, it will be this triple.  Change it to Val()
    # perhaps.
    # Initialize them to invalid values
    self.pool_index = -1
    self.col = -1  # zero-indexed
    self.length = -1

    # Size
    # 1 byte type (maybe, because I'm not sure if we'll have oil tokens in the
    #              same space, because they will appear in nodes)
    # 2 byte col: 64K columns
    # 1 byte length: max 256 char var name, 256 char here doc line?  hm.
    #   Well you could use the lexer to relax this
    # 4 byte pool index (4 B)
    # Or maybe 16 bytes is OK

  def __eq__(self, other):  # for unit tests
    return self.type == other.type and self.val == other.val

  def __repr__(self):
    return '<%s %s>' % (TokenTypeToName(self.type), EncodeTokenVal(self.val))

  def Val(self, pool):
    """Given a pool of lines, return the value of this token.

    NOTE: Not used right now because we haven't threaded 'pool' through
    everything.
    """
    line = pool.GetLine(self.pool_index)
    c = self.col
    return line[c : c+self.length]

  def Kind(self):
    return _TOKEN_TYPE_TO_KIND[self.type]


# Token types and kinds.  We could generated Python code from shell/tokens.txt,
# but that's probably overkill for this demo.


# This is Kind -> list of tokens
# Then the lexer is State -> list of (regex, token)
#
# TokenDef helps us generate enums and token name stuff.  The other one will
# help us generate text.
# But do I want a description here?
# These names will also be used in the text format?  

class _TokenDef(object):
  UNDEFINED = ('TOK',)  # for initial state
  UNKNOWN   = ('TOK',)  # for when nothing matches

  Eof       = ('REAL', 'RPAREN', 'BACKTICK')

  IGNORED   = ('LINE_CONT', 'SPACE', 'COMMENT')

  # WS_SPACE is for LexMode.OUTER; IGNORED_SPACE is for LexMode.ARITH
  WS        = ('SPACE',)# 'NEWLINE')

  LIT       = ('CHARS', 'VAR_LIKE', 'OTHER', 'ESCAPED_CHAR',
               # Either brace expansion or keyword for { and }
               'LBRACE', 'RBRACE', 'COMMA',
               # tilde expansion
               'TILDE',

               # [[ ]] = == -- so they appear together in one LiteralPart
               'LEFT_DBRACKET', 'RIGHT_DBRACKET',
               'EQUAL', 'DEQUAL',
               'NEQUAL', 'TEQUAL',

               'POUND',  # for comment or VAROP state
               'SLASH', 'PERCENT',  # / # % for patsub, NOT unary op

               'DIGITS',  # for LexMode.ARITH
               )

  OP        = ('NEWLINE', # mostly equivalent to SEMI
               'AMP',     # &
               'PIPE',    # |
               'PIPEAMP', # |& -- bash extension for stderr
               'AND_IF',  # &&
               'OR_IF',   # || 
               'SEMI',    # ;
               'DSEMI',   # ;; for case

               # NOTE: This is for subshell only.  It shouldn't be under LEFT_
               # because it's NOT a WordPart.  ReadCommandWord shouldn't
               # process it.
               'LPAREN',
               'RPAREN',  # DEFAULT, WILL BE TRANSLATED to RIGHT_*
               'LEFT_DPAREN',
               'RIGHT_DPAREN',
               )

  REDIR     = ('LESS',       # < stdin
               'GREAT',      # > stdout
               'DLESS',      # << here doc redirect
               'TLESS',      # <<< bash only here string
               'DGREAT',     # >> append stdout
               'GREATAND',   # >& descriptor redirect
               'LESSAND',    # <& descriptor redirect
               'DLESSDASH',  # <<- here doc redirect for tabs?
               'LESSGREAT',  # <>
               'CLOBBER',    # >|  POSIX?

               # TODO: Add bash-specific operators
               )

  # NOTE: This is for left/right WORDS only.  (( is not a word so it doesn't
  # get that.
  LEFT      = ('D_QUOTE',
               'S_QUOTE',
               'BACKTICK',     # `
               'COMMAND_SUB',  # $(
               'VAR_SUB',      # ${
               'ARITH_SUB',    # $((
               'ARITH_SUB2',   # $[ for bash (and zsh)
               'DD_QUOTE',     # $" for bash localized strings
               'DS_QUOTE',     # $' for \n escapes
               'PROC_SUB_IN',  # <( )
               'PROC_SUB_OUT', # >( )
               )

  RIGHT     = ('D_QUOTE',
               'S_QUOTE',
               'BACKTICK',     # `
               'COMMAND_SUB',  # )
               'VAR_SUB',      # }
               'ARITH_SUB',    # ))
               # ARITH_SUB2 is just AS_OP_RBRACKET
               'DD_QUOTE',     # "
               'DS_QUOTE',     # '

               # Disambiguated right parens
               'SUBSHELL',  # )
               'FUNC_DEF',  # )
               'CASE_PAT',  # )
               'ARRAY_LITERAL',  # )
               )

  # First position of var sub ${
  # VS_OP_POUND -- however you can't tell the difference at first!  It could
  # be an op or a name.  So it makes sense to base i on the state.  
  # VS_OP_AT
  # But then you have AS_STAR, or AS_OP_STAR maybe

  VS        = ('NAME',  # Dummy for VS_NAME in C++, which is a different kind?
               'NUMBER',  # $0 .. $9
               'BANG',    # $!
               'AT',      # $@  or  [@] for array subscripting
               'POUND',   # $#  or  ${#var} for length
               'DOLLAR',  # $$
               'AMP',     # $&
               'STAR',    # $*
               'HYPHEN',  # $-
               'QMARK',   # $?
               )
  
  # Test ops
  VS_TEST   = ('COLON_HYPHEN',  #  :-
               'HYPHEN',        #   -
               'COLON_EQUALS',  #  :=
               'EQUALS',        #   =
               'COLON_QMARK',   #  :?
               'QMARK',         #   ?
               'COLON_PLUS',    #  :+
               'PLUS',          #   +
               )

               # String removal ops
  VS_UNARY  = ('PERCENT',       #  %
               'DPERCENT',      #  %%
               'POUND',         #  # 
               'DPOUND',        #  ##

               # Case ops, in bash.  At least parse them.  Execution might
               # require unicode stuff.
               'CARET',         #  ^
               'DCARET',        #  ^^
               'COMMA',         #  ,
               'DCOMMA',        #  ,,
               )

               # not in POSIX, but in Bash
  VS_OP     = ('SLASH',         #  / for replacement
               'COLON',         #  : for slicing
               'LBRACKET',      #  [ for indexing
               'RBRACKET',      #  ] for indexing
              )

  # Operators
  AS_OP     = ('SEMI',  # ternary for loop only
               'COMMA',  # function call and C comma operator
               'PLUS', 'MINUS', 'STAR', 'SLASH', 'PERCENT',
               'DPLUS', 'DMINUS', 'DSTAR',
               'LPAREN', 'RPAREN',  # grouping and function call extension
               'LBRACKET', 'RBRACKET',  # array and assoc array subscript
               'RBRACE',  # for end of var sub
               # Only for ${a[@]} -- not valid in any other arith context
               'AT',

               # Logical ops
               'QMARK',  'COLON',  # ternary op: a < b ? 0 : 1
               'LE', 'LESS', 'GE', 'GREAT', 'DEQUAL', 'NEQUAL',
               'DAMP', 'DPIPE', 'BANG',  # && || !

               # Bitwise ops
               'DGREAT', 'DLESS',  # >> <<
               'AMP', 'PIPE', 'CARET', 'TILDE', # & | ^ ~ for bits

  # 11 mutating operators:  =  +=  -=  etc.
              'EQUAL',
              'PLUS_EQUAL', 'MINUS_EQUAL', 'STAR_EQUAL', 'SLASH_EQUAL',
              'PERCENT_EQUAL',
              'DGREAT_EQUAL', 'DLESS_EQUAL', 'AMP_EQUAL', 'PIPE_EQUAL',
              'CARET_EQUAL')

  # This kind is for Node types that are NOT tokens.

  NODE      = (
               # Postfix inc/dec.  Prefix inc/dec use AS_OP_DPLUS and
               # AS_OP_DMINUS.
               'POST_DPLUS', 'POST_DMINUS',
               # A complex word in the arith context.
               # A['foo'] A["foo"] A[$foo] A["$foo"] A[${foo}] A["${foo}"]
               'ARITH_WORD',
               # +1 and -1, to distinguish from infix.
               'UNARY_PLUS', 'UNARY_MINUS',
               )

  # Others:
  # DB_LIT -- gets translated to BType()  
  # KW_LIT -- keywords
  #
  # GOAL: no char literals or strcmp() anywhere in the source!


_TOKEN_TYPE_NAMES = {}  # type: dict

def TokenTypeToName(t):
  return _TOKEN_TYPE_NAMES[t]


class TN(object):
  """Token type or node type."""
  pass


class TokenKind(object):
  """Token kind is filled in dynamically."""
  pass


# This is word characters, - and _, as well as path name characters . and /.
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def EncodeTokenVal(s):
  if '\n' in s:
    return json.dumps(s)  # account for the fact that $ matches the newline
  if _PLAIN_RE.match(s):
    return s
  else:
    return json.dumps(s)


def _GenCodeFromTokens(token_def, module, tk, name_lookup, kind_lookup):
  kind_index = 0
  token_index = 0
  kind_sizes = []
  # NOTE: dir returns names in alphabetical order, which is fine
  for kind_name in dir(token_def):
    tokens = getattr(token_def, kind_name)
    if not isinstance(tokens, tuple):
      continue
    kind_sizes.append(len(tokens))

    setattr(tk, kind_name, kind_index)

    for t in tokens:
      token_name = '%s_%s' % (kind_name, t)
      #print(token_name)
      token_index += 1

      #print('Setting %s' % token_name)
      setattr(module, token_name, token_index)
      name_lookup[token_index] = token_name
      kind_lookup[token_index] = kind_index

    kind_index += 1

  return kind_sizes

#
# Bool
#

_BTOKEN_TYPE_NAMES = {}  # type: dict

def BTokenTypeToName(t):
  return _BTOKEN_TYPE_NAMES[t]


class BType(object):
  """
  Token type for execution, determined at parse time.
  Filled in by metaprogramming.
  e.g. BTokenType.ATOM, BTokenType.LOGICAL_NOT, BTokenType.BINARY_FILE_OT.
  """


class BKind(object):
  """
  Token kind for recursive descent dispatching: BTokenKind.UNARY or
  BTokenType.BINARY.

  Filled in by metaprogramming.
  """


UNARY_FILE_CHARS = tuple('abcdefghLprsStuwxOGN')


class _BTokenDef(object):
  """Tokens in [[ are WORDS.

  BNode types, separated into BKind.

  NOTE: THere is a difference between ops and tokens:
  = and == are the same op
  [[ foo ]] is an implicit -n op
  """
  ATOM = ('TOK',)
  NEWLINE = ('TOK',)

  # BinaryWordBNode
  BINARY = {
      'STRING': ('EQUAL', 'NOT_EQUAL', 'TILDE_EQUAL', 'LESS', 'GREAT'),
      'FILE': ('EF', 'NT', 'OT'),
      'INT': ('EQ', 'NE', 'GT', 'GE', 'LT', 'LE'),
      }

  Eof = ('TOK',)

  # For parsing, this must be a different BKind that BINARY or UNARY.
  LOGICAL = {
      'BINARY': ('AND', 'OR'),
      'UNARY': ('NOT',),
      }

  PAREN = ('LEFT', 'RIGHT')

  # UnaryWordBNode
  UNARY = {
      'STRING': ('z', 'n'),  # -z -n
      'OTHER': ('o', 'v', 'R'),
      'FILE': UNARY_FILE_CHARS,
      }

  UNDEFINED = ('TOK',)


BArgType = util.Enum('BArgType', 'NONE FILE INT STRING OTHER'.split())


def _GenCodeFromBTokens(token_def, bkind_enum, btype_enum, name_lookup,
    op_table):
  """
  Hierarchy: kind, kind2, type
  """
  kind_index = 0
  token_index = 0
  # NOTE: dir returns names in alphabetical order, whichi s fine
  for kind_name in dir(token_def):
    tokens = getattr(token_def, kind_name)

    if isinstance(tokens, tuple):

      for j, t in enumerate(tokens):
        token_name = '%s_%s' % (kind_name, t)

        setattr(btype_enum, token_name, token_index)
        name_lookup[token_index] = token_name

        op_table.append((kind_index, False, -1, BArgType.NONE))

        token_index += 1

    elif isinstance(tokens, dict):  # UNARY, BINARY, LOGICAL
      for j, kind2 in enumerate(sorted(tokens)):
        names = tokens[kind2]

        for k, t in enumerate(names):
          token_name = '%s_%s_%s' % (kind_name, kind2, t)

          setattr(btype_enum, token_name, token_index)
          name_lookup[token_index] = token_name

          # Figure out the table entry
          logical = (kind_name == 'LOGICAL')
          if logical:
            if kind2 == 'UNARY':
              arity = 1
            elif kind2 == 'BINARY':
              arity = 2
            else:
              raise AssertionError(kind2)

            arg_type = BArgType.NONE  # not used

          else:
            if kind_name == 'UNARY':
              arity = 1
            elif kind_name == 'BINARY':
              arity = 2
            else:
              arity = -1
            if kind2 == 'FILE':
              arg_type = BArgType.FILE
            elif kind2 == 'INT':
              arg_type = BArgType.INT
            elif kind2 == 'STRING':
              arg_type = BArgType.STRING
            elif kind2 == 'OTHER':
              arg_type = BArgType.OTHER
            else:
              raise AssertionError(kind2)

          op_table.append((kind_index, logical, arity, arg_type))

          token_index += 1
    else:
      continue

    setattr(bkind_enum, kind_name, kind_index)
    kind_index += 1


_kind_sizes = _GenCodeFromTokens(
    _TokenDef, sys.modules[__name__], TokenKind, _TOKEN_TYPE_NAMES,
    _TOKEN_TYPE_TO_KIND)

# (kind, logical, arity, arg_type)
BOOLEAN_OP_TABLE = []  # type: list

_GenCodeFromBTokens(
    _BTokenDef, BKind, BType, _BTOKEN_TYPE_NAMES, BOOLEAN_OP_TABLE)
