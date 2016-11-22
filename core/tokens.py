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


# TODO: This should be CType() I think
CKind = util.Enum('CKind',
    'UNDEFINED COMMAND OPERATOR REDIR Eof'.split())


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
  Undefined = ('Tok',)  # for initial state
  Unknown   = ('Tok',)  # for when nothing matches

  Eof       = ('Real', 'RParen', 'Backtick')

  Ignored   = ('LineCont', 'Space', 'Comment')

  # Id.WS_Space is for LexMode.OUTER; Id.Ignored_Space is for LexMode.ARITH
  WS        = ('Space',)

  Lit       = ('Chars', 'VarLike', 'Other', 'EscapedChar',
               # Either brace expansion or keyword for { and }
               'LBrace', 'RBrace', 'Comma',
               # tilde expansion
               'Tilde',

               # [[ ]] = == -- so they appear together in one LiteralPart
               'DLeftBracket', 'DRightBracket',
               'Equal', 'DEqual',
               'NEqual', 'TEqual',

               'Pound',             #  for comment or VAROP state
               'Slash', 'Percent',  #  / # % for patsub, NOT unary op

               'Digits',            # for LexMode.ARITH
               )

  Op        = ('Newline', # mostly equivalent to SEMI
               'Amp',     # &
               'Pipe',    # |
               'PipeAmp', # |& -- bash extension for stderr
               'AndIf',   # &&
               'OrIf',    # ||
               'Semi',    # ;
               'DSemi',   # ;; for case

               # NOTE: This is for subshell only.  It's not under LEFT_ because
               # it's NOT a WordPart.
               'LParen',
               'RParen',  # Default, will be translated to Id.Right_*
               'DLeftParen',
               'DRightParen',
               )

  Redir     = ('Less',       # < stdin
               'Great',      # > stdout
               'DLess',      # << here doc redirect
               'TLess',      # <<< bash only here string
               'DGreat',     # >> append stdout
               'GreatAnd',   # >& descriptor redirect
               'LessAnd',    # <& descriptor redirect
               'DLessDash',  # <<- here doc redirect for tabs?
               'LessGreat',  # <>
               'Clobber',    # >|  POSIX?
               )

  # NOTE: This is for left/right WORDS only.  (( is not a word so it doesn't
  # get that.
  Left      = ('DoubleQuote',
               'SingleQuote',
               'Backtick',           # `
               'CommandSub',         # $(
               'VarSub',             # ${
               'ArithSub',           # $((
               'ArithSub2',          # $[ for bash (and zsh)
               'DollarDoubleQuote',  # $" for bash localized strings
               'DollarSingleQuote',  # $' for \n escapes
               'ProcSubIn',          # <( )
               'ProcSubOut',         # >( )
               )

  Right     = ('DoubleQuote',
               'SingleQuote',
               'Backtick',           # `
               'CommandSub',         # )
               'VarSub',             # }
               'ArithSub',           # ))
               # ArithSub2 is just Id.Arith_RBracket
               'DollarDoubleQuote',  # "
               'DollarSingleQuote',  # '

               # Disambiguated right parens
               'Subshell',      # )
               'FuncDef',       # )
               'CasePat',       # )
               'ArrayLiteral',  # )
               )

  # First position of var sub ${
  # Id.VOp_Pound -- however you can't tell the difference at first!  It could
  # be an op or a name.  So it makes sense to base i on the state.
  # Id.VOp_At
  # But then you have AS_STAR, or Id.Arith_Star maybe

  VSub      = ('Name',    # $foo or ${foo}
               'Number',  # $0 .. $9
               'Bang',    # $!
               'At',      # $@  or  [@] for array subscripting
               'Pound',   # $#  or  ${#var} for length
               'Dollar',  # $$
               'Amp',     # $&
               'Star',    # $*
               'Hyphen',  # $-
               'QMark',   # $?
               )

  # Test ops
  VTest     = ('ColonHyphen',  #  :-
               'Hyphen',       #   -
               'ColonEquals',  #  :=
               'Equals',       #   =
               'ColonQMark',   #  :?
               'QMark',        #   ?
               'ColonPlus',    #  :+
               'Plus',         #   +
               )

               # String removal ops
  VUnary    = ('Percent',       #  %
               'DPercent',      #  %%
               'Pound',         #  #
               'DPound',        #  ##

               # Case ops, in bash.  At least parse them.  Execution might
               # require unicode stuff.
               'Caret',         #  ^
               'DCaret',        #  ^^
               'Comma',         #  ,
               'DComma',        #  ,,
               )

               # not in POSIX, but in Bash
  VOp       = ('Slash',         #  / for replacement
               'Colon',         #  : for slicing
               'LBracket',      #  [ for indexing
               'RBracket',      #  ] for indexing
               )

  # Operators
  Arith     = ('Semi',   # ternary for loop only
               'Comma',  # function call and C comma operator
               'Plus', 'Minus', 'Star', 'Slash', 'Percent',
               'DPlus', 'DMinus', 'DStar',
               'LParen', 'RParen',  # grouping and function call extension
               'LBracket', 'RBracket',  # array and assoc array subscript
               'RBrace',  # for end of var sub
               # Only for ${a[@]} -- not valid in any other arith context
               'At',

               # Logical Ops
               'QMark',  'Colon',  # Ternary Op: a < b ? 0 : 1
               'LessEqual', 'Less', 'GreatEqual', 'Great', 'DEqual', 'NEqual',
               'DAmp', 'DPipe', 'Bang',  # && || !

               # Bitwise ops
               'DGreat', 'DLess',  # >> <<
               'Amp', 'Pipe', 'Caret', 'Tilde',  #  & | ^ ~ for bits

               # 11 mutating operators:  =  +=  -=  etc.
               'Equal',
               'PlusEqual', 'MinusEqual', 'StarEqual', 'SlashEqual',
               'PercentEqual',
               'DGreatEqual', 'DLessEqual', 'AmpEqual', 'PipeEqual',
               'CaretEqual')

  # This kind is for Node types that are NOT tokens.

  Node      = (
               # Postfix inc/dec.  Prefix inc/dec use Id.Arith_DPlus and
               # Id.Arith_DMinus.
               'PostDPlus', 'PostDMinus',
               # A complex word in the arith context.
               # A['foo'] A["foo"] A[$foo] A["$foo"] A[${foo}] A["${foo}"]
               'ArithWord',
               # +1 and -1, to distinguish from infix.
               'UnaryPlus', 'UnaryMinus',
               )
  # Others:
  # DB_LIT -- gets translated to BType()
  # KW_LIT -- keywords
  #
  # GOAL: no char literals or strcmp() anywhere in the source!


_TOKEN_TYPE_NAMES = {}  # type: dict

def TokenTypeToName(t):
  return _TOKEN_TYPE_NAMES[t]


class TokenKind(object):
  """Token kind is filled in dynamically."""
  pass


class Id(object):
  """
  Universal Token type and AST Node type.  Used by parsers and evaluators.
  """
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


def _GenCodeFromTokens(token_def, id_, tk, name_lookup, kind_lookup):
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
      token_index += 1

      token_name = '%s_%s' % (kind_name, t)
      setattr(id_, token_name, token_index)

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
  e.g. BType.ATOM_TOK, BType.LOGICAL_NOT, BType.BINARY_FILE_OT.
  """


class BKind(object):
  """
  Token kind for recursive descent dispatching: BKind.UNARY or BKind.BINARY.

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
    _TokenDef, Id, TokenKind, _TOKEN_TYPE_NAMES,
    _TOKEN_TYPE_TO_KIND)

# (kind, logical, arity, arg_type)
BOOLEAN_OP_TABLE = []  # type: list

_GenCodeFromBTokens(
    _BTokenDef, BKind, BType, _BTOKEN_TYPE_NAMES, BOOLEAN_OP_TABLE)
