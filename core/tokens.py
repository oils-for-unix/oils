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
    return '<%s %s>' % (IdName(self.type), EncodeTokenVal(self.val))

  def Val(self, pool):
    """Given a pool of lines, return the value of this token.

    NOTE: Not used right now because we haven't threaded 'pool' through
    everything.
    """
    line = pool.GetLine(self.pool_index)
    c = self.col
    return line[c : c+self.length]

  def Kind(self):
    return _ID_TO_KIND[self.type]


# This is word characters, - and _, as well as path name characters . and /.
_PLAIN_RE = re.compile(r'^[a-zA-Z0-9\-_./]+$')

def EncodeTokenVal(s):
  if '\n' in s:
    return json.dumps(s)  # account for the fact that $ matches the newline
  if _PLAIN_RE.match(s):
    return s
  else:
    return json.dumps(s)


_ID_TO_KIND = {}  # type: dict

def LookupKind(id_):
  return _ID_TO_KIND[id_]


_ID_NAMES = {}  # type: dict

def IdName(t):
  return _ID_NAMES[t]


class Kind(object):
  """Token kind is filled in dynamically."""
  pass


class Id(object):
  """
  Universal Token type and AST Node type.  Used by parsers and evaluators.
  """
  pass


# TODO: Fold in more constant tokens.
# ArithLexerPairs(), etc.

class IdSpec(object):
  """Identifiers that form the "spine" of the shell program representation."""

  def __init__(self, token_names, kind_lookup, bool_ops):
    self.id_enum = Id
    self.kind_enum = Kind  # Should just be Kind
    self.token_names = token_names
    self.kind_lookup = kind_lookup

    self.kind_sizes = []  # stats

    self.bool_lexer_pairs = []  # lexer values
    self.bool_ops = bool_ops  # table of runtime values

    # Incremented on each method call
    self.token_index = 0
    self.kind_index = 0

  def BoolLexerPairs(self):
    return self.bool_lexer_pairs

  def _AddId(self, token_name):
    self.token_index += 1  # leave out 0 I guess?
    setattr(self.id_enum, token_name, self.token_index)
    self.token_names[self.token_index] = token_name
    self.kind_lookup[self.token_index] = self.kind_index

  def _AddKind(self, kind_name):
    setattr(self.kind_enum, kind_name, self.kind_index)
    self.kind_index += 1

  def AddKind(self, kind_name, tokens):
    # TODO: Tokens can be pairs, and then we can register them as
    # spec.LexerPairs(Kind.BoolUnary) spec.LexerPairs(Kind.VTest)
    assert isinstance(tokens, list), tokens

    for t in tokens:
      token_name = '%s_%s' % (kind_name, t)
      self._AddId(token_name)

    # Must be after adding Id
    self._AddKind(kind_name)
    self.kind_sizes.append(len(tokens))  # debug info

  def AddBoolKind(self, arity, arg_type_pairs):
    """
    Args:
    """
    if arity == 1:
      kind_name = 'BoolUnary'
      #kind2 = 'UNARY'
    elif arity == 2:
      kind_name = 'BoolBinary'
      #kind2 = 'BINARY'
    else:
      raise AssertionError(arity)

    num_tokens = 0
    for arg_type, pairs in arg_type_pairs.items():
      #print(arg_type, pairs)

      for name, char_pat in pairs:
        # BoolUnary_f, BoolBinary_eq, BoolBinary_NEqual
        token_name = '%s_%s' % (kind_name, name)
        self._AddId(token_name)
        # not logical
        self.AddBoolOp(self.token_index, False, arity, arg_type)
        # After _AddId.
        self.bool_lexer_pairs.append((re.escape(char_pat), self.token_index))

      num_tokens += len(pairs)

    # Must do this after _AddId()
    self._AddKind(kind_name)
    self.kind_sizes.append(num_tokens)  # debug info

  def AddBoolOp(self, id_, logical, arity, arg_type):
    self.bool_ops[id_] = (logical, arity, arg_type)


def MakeTokens(spec):
  # TODO: Unknown_Tok is OK, but Undefined_Id is better

  spec.AddKind('Undefined', ['Tok'])  # for initial state
  spec.AddKind('Unknown',   ['Tok'])  # for when nothing matches

  spec.AddKind('Eof', ['Real', 'RParen', 'Backtick'])

  spec.AddKind('Ignored', ['LineCont', 'Space', 'Comment'])

  # Id.WS_Space is for LexMode.OUTER; Id.Ignored_Space is for LexMode.ARITH
  spec.AddKind('WS', ['Space'])

  spec.AddKind('Lit', [
      'Chars', 'VarLike', 'Other', 'EscapedChar',
      # Either brace expansion or keyword for { and }
      'LBrace', 'RBrace', 'Comma',
      'Tilde',             # tilde expansion
      'Pound',             #  for comment or VAROP state
      'Slash', 'Percent',  #  / # % for patsub, NOT unary op
      'Digits',            # for LexMode.ARITH
  ])

  spec.AddKind('Op', [
      'Newline', # mostly equivalent to SEMI
      'Amp',     # &
      'Pipe',    # |
      'PipeAmp', # |& -- bash extension for stderr
      'DAmp',   # &&
      'DPipe',    # ||
      'Semi',    # ;
      'DSemi',   # ;; for case

      # NOTE: This is for subshell only.  It's not under Kind.Left because it's
      # NOT a WordPart.
      'LParen',
      'RParen',  # Default, will be translated to Id.Right_*
      'DLeftParen',
      'DRightParen',
  ])

  spec.AddKind('Redir', [
      'Less',       # < stdin
      'Great',      # > stdout
      'DLess',      # << here doc redirect
      'TLess',      # <<< bash only here string
      'DGreat',     # >> append stdout
      'GreatAnd',   # >& descriptor redirect
      'LessAnd',    # <& descriptor redirect
      'DLessDash',  # <<- here doc redirect for tabs?
      'LessGreat',  # <>
      'Clobber',    # >|  POSIX?
  ])

  # NOTE: This is for left/right WORDS only.  (( is not a word so it doesn't
  # get that.
  spec.AddKind('Left', [
      'DoubleQuote',
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
  ])

  spec.AddKind('Right', [
      'DoubleQuote',
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
  ])

  # First position of var sub ${
  # Id.VOp2_Pound -- however you can't tell the difference at first!  It could
  # be an op or a name.  So it makes sense to base i on the state.
  # Id.VOp2_At
  # But then you have AS_STAR, or Id.Arith_Star maybe

  spec.AddKind('VSub', [
      'Name',    # $foo or ${foo}
      'Number',  # $0 .. $9
      'Bang',    # $!
      'At',      # $@  or  [@] for array subscripting
      'Pound',   # $#  or  ${#var} for length
      'Dollar',  # $$
      'Amp',     # $&
      'Star',    # $*
      'Hyphen',  # $-
      'QMark',   # $?
  ])

  spec.AddKind('VTest', [
      'ColonHyphen',  #  :-
      'Hyphen',       #   -
      'ColonEquals',  #  :=
      'Equals',       #   =
      'ColonQMark',   #  :?
      'QMark',        #   ?
      'ColonPlus',    #  :+
      'Plus',         #   +
  ])

  # String removal ops
  spec.AddKind('VOp1', [
      'Percent',       #  %
      'DPercent',      #  %%
      'Pound',         #  #
      'DPound',        #  ##

      # Case ops, in bash.  A         t least parse them.  Execution might
      # require unicode stuff         .
      'Caret',         #  ^           
      'DCaret',        #  ^^
      'Comma',         #  ,
      'DComma',        #  ,,
  ])

  # Not in POSIX, but in Bash
  spec.AddKind('VOp2', [
      'Slash',         #  / for replacement
      'Colon',         #  : for slicing
      'LBracket',      #  [ for indexing
      'RBracket',      #  ] for indexing
  ])

  # Operators
  spec.AddKind('Arith', [
      'Semi',   # ternary for loop only
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
      'CaretEqual'
  ])

  # This kind is for Node types that are NOT tokens.
  spec.AddKind('Node', [
     # Arithmetic nodes:
     'PostDPlus', 'PostDMinus',  # Postfix inc/dec.
                                 # Prefix inc/dec use Arith_DPlus/Arith_DMinus.
     'UnaryPlus', 'UnaryMinus',  # +1 and -1, to distinguish from infix.

     # Command nodes:
     'Command', 'Assign', 'AndOr', 'Block', 'Subshell', 'Fork',
     'FuncDef', 'ForEach', 'ForExpr', 'NoOp',
  ])

  # A compound word, in arith context, boolean context, or command
  # context.  Also used as a CommandKind.
  # A['foo'] A["foo"] A[$foo] A["$foo"] A[${foo}] A["${foo}"]
  spec.AddKind('Word', ['Compound'])

  spec.AddKind('KW', [
      'None', 
      'DRightBracket', 'DLeftBracket', 'Bang', 
      'For', 'While', 'Until', 'Do', 'Done', 'In', 'Case',
      'Esac', 'If', 'Fi', 'Then', 'Else', 'Elif', 'Function',
  ])

  # Assignment builtins -- treated as statically parsed keywords.  They are
  # different from keywords because env bindings can appear before, e.g.
  # FOO=bar local v.
  spec.AddKind('Assign', ['None', 'Declare', 'Export', 'Local', 'Readonly'])


# token_type -> (logical, arity, arg_type)
BOOL_OPS = {}  # type: dict

UNARY_FILE_CHARS = tuple('abcdefghLprsStuwxOGN')

BArgType = util.Enum('BArgType', 'NONE FILE INT STRING OTHER'.split())


def _Dash(strs):
  # Gives a pair of (token name, string to match)
  return [(s, '-' + s) for s in strs]


def MakeBool(spec):
  spec.AddBoolKind(1, {
      BArgType.STRING: _Dash(list('zn')),  # -z -n
      BArgType.OTHER: _Dash(list('ovR')),
      BArgType.FILE: _Dash(UNARY_FILE_CHARS),
  })

  spec.AddBoolKind(2, {
      BArgType.STRING: [
          ('Equal', '='), ('DEqual', '=='), ('NEqual', '!='),
          ('EqualTilde', '=~'),
      ],
      BArgType.FILE: _Dash(['ef', 'nt', 'ot']),
      BArgType.INT: _Dash(['eq', 'ne', 'gt', 'ge', 'lt', 'le']),
  })

  # logical, arity, arg_type
  spec.AddBoolOp(Id.Op_DAmp, True, 2, BArgType.NONE)
  spec.AddBoolOp(Id.Op_DPipe, True, 2, BArgType.NONE)
  spec.AddBoolOp(Id.KW_Bang, True, 1, BArgType.NONE)

  spec.AddBoolOp(Id.Redir_Less, False, 2, BArgType.STRING)
  spec.AddBoolOp(Id.Redir_Great, False, 2, BArgType.STRING)


ID_SPEC = IdSpec(_ID_NAMES, _ID_TO_KIND, BOOL_OPS)

MakeTokens(ID_SPEC)
MakeBool(ID_SPEC)  # must come second

# Debug
_kind_sizes = ID_SPEC.kind_sizes
