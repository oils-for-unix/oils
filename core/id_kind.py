#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
id_kind.py - Id and Kind definitions, used for Token, Word, Nodes, etc.
"""

import re
import sys

from core import util


_ID_TO_KIND = {}  # type: dict

def LookupKind(id_):
  return _ID_TO_KIND[id_]


_ID_NAMES = {}  # type: dict

def IdName(t):
  return _ID_NAMES[t]


class Id(object):
  """Universal Token, Word, and Node type.

  Used all over the place, but in particular the evaluator must consider all
  Ids.
  """
  pass


class Kind(object):
  """A coarser version of Id, used to make parsing decisions."""
  pass


class IdSpec(object):
  """Identifiers that form the "spine" of the shell program representation."""

  def __init__(self, token_names, kind_lookup, bool_ops):
    self.id_enum = Id
    self.kind_enum = Kind  # Should just be Kind
    self.token_names = token_names
    self.kind_lookup = kind_lookup

    self.kind_sizes = []  # stats

    self.lexer_pairs = {}  # Kind -> [(regex, Id), ...]
    self.bool_ops = bool_ops  # table of runtime values

    # Incremented on each method call
    self.token_index = 0
    self.kind_index = 0

  def LexerPairs(self, kind):
    return self.lexer_pairs[kind]

  def _AddId(self, token_name):
    self.token_index += 1  # leave out 0 I guess?
    setattr(self.id_enum, token_name, self.token_index)
    self.token_names[self.token_index] = token_name
    self.kind_lookup[self.token_index] = self.kind_index

  def _AddKind(self, kind_name):
    setattr(self.kind_enum, kind_name, self.kind_index)
    self.kind_index += 1

  def AddKind(self, kind_name, tokens):
    assert isinstance(tokens, list), tokens

    for name in tokens:
      token_name = '%s_%s' % (kind_name, name)
      self._AddId(token_name)

    # Must be after adding Id
    self._AddKind(kind_name)
    self.kind_sizes.append(len(tokens))  # debug info

  def AddKindPairs(self, kind_name, pairs):
    assert isinstance(pairs, list), pairs

    lexer_pairs = []
    for name, char_pat in pairs:
      token_name = '%s_%s' % (kind_name, name)
      self._AddId(token_name)
      # After _AddId
      lexer_pairs.append((False, char_pat, self.token_index))  # Constant

    self.lexer_pairs[self.kind_index] = lexer_pairs

    # Must be after adding Id
    self._AddKind(kind_name)
    self.kind_sizes.append(len(pairs))  # debug info

  def AddBoolKind(self, arity, arg_type_pairs):
    """
    Args:
    """
    if arity == 1:
      kind_name = 'BoolUnary'
    elif arity == 2:
      kind_name = 'BoolBinary'
    else:
      raise AssertionError(arity)

    lexer_pairs = []
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
        lexer_pairs.append((False, char_pat, self.token_index))  # constant

      num_tokens += len(pairs)

    self.lexer_pairs[self.kind_index] = lexer_pairs

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
      'DRightBracket',     # the ]] that matches [[, NOT a keyword
      'Tilde',             # tilde expansion
      'Pound',             #  for comment or VAROP state
      'Slash', 'Percent',  #  / # % for patsub, NOT unary op
      'Digits',            # for LexMode.ARITH
      'At',                # for ${a[@]}, in LexState.ARITH
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

      'LParen',  # For subshell.  Not Kind.Left because it's NOT a WordPart.
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

  spec.AddKindPairs('VTest', [
      ('ColonHyphen',   ':-'),
      ('Hyphen',        '-' ),
      ('ColonEquals',   ':='),
      ('Equals',        '=' ),
      ('ColonQMark',    ':?'),
      ('QMark',         '?' ),
      ('ColonPlus',     ':+'),
      ('Plus',          '+' ),
  ])

  # String removal ops
  spec.AddKindPairs('VOp1', [
      ('Percent',       '%' ),
      ('DPercent',      '%%'),
      ('Pound',         '#' ),
      ('DPound',        '##'),
      # Case ops, in bash.  At least parse them.  Execution might require
      # unicode stuff.
      ('Caret',         '^' ),
      ('DCaret',        '^^'),
      ('Comma',         ',' ),
      ('DComma',        ',,'),
  ])

  # Not in POSIX, but in Bash
  spec.AddKindPairs('VOp2', [
      ('Slash',         '/'),  #  / for replacement
      ('Colon',         ':'),  #  : for slicing
      ('LBracket',      '['),  #  [ for indexing
      ('RBracket',      ']'),  #  ] for indexing
  ])

  # Operators
  # NOTE: Could share Op_Pipe, Op_Amp, Op_DAmp, Op_Semi, Op_LParen, etc.
  # Actually All of Arith could be folded into Op, because we are using
  # WordParser._ReadArithWord vs. WordParser._ReadWord.
  spec.AddKindPairs('Arith', [
      ('Semi', ';'),   # ternary for loop only
      ('Comma', ','),  # function call and C comma operator
      ('Plus', '+'), ('Minus', '-'), ('Star', '*'), ('Slash', '/'),
      ('Percent', '%'),
      ('DPlus', '++'), ('DMinus', '--'), ('DStar', '**'),
      ('LParen', '('), ('RParen', ')'),  # grouping and function call extension
      ('LBracket', '['), ('RBracket', ']'),  # array and assoc array subscript
      ('RBrace', '}'),  # for end of var sub

      # Logical Ops
      ('QMark', '?'), ('Colon', ':'), # Ternary Op: a < b ? 0 : 1
      ('LessEqual', '<='), ('Less', '<'), ('GreatEqual', '>='), ('Great', '>'),
      ('DEqual', '=='), ('NEqual', '!='),
      ('DAmp', '&&'), ('DPipe', '||'), ('Bang', '!'),

      # Bitwise ops
      ('DGreat', '>>'), ('DLess', '<<'),
      ('Amp', '&'), ('Pipe', '|'), ('Caret', '^'), ('Tilde', '~'),

      # 11 mutating operators:  =  +=  -=  etc.
      ('Equal', '='),
      ('PlusEqual', '+='), ('MinusEqual', '-='), ('StarEqual', '*='),
      ('SlashEqual', '/='), ('PercentEqual', '%='),
      ('DGreatEqual', '>>='), ('DLessEqual', '<<='),
      ('AmpEqual', '&='), ('PipeEqual', '|='),
      ('CaretEqual', '^=')
  ])

  # This kind is for Node types that are NOT tokens.
  spec.AddKind('Node', [
     # Arithmetic nodes
     'PostDPlus', 'PostDMinus',  # Postfix inc/dec.
                                 # Prefix inc/dec use Arith_DPlus/Arith_DMinus.
     'UnaryPlus', 'UnaryMinus',  # +1 and -1, to distinguish from infix.
                                 # Actually we don't need this because we they
                                 # will be under Expr1/Plus vs Expr2/Plus.

     # Command nodes 
     'Command', 'Assign', 'AndOr', 'Block', 'Subshell', 'Fork',
     'FuncDef', 'ForEach', 'ForExpr', 'NoOp',

     # TODO: Unify ANode and BNode under these Unary, Binary, Ternary nodes.
     # They hold one, two, or three words.
     'Expr1', 'Expr2', 'Expr3',
     'ConstInt',  # for arithmetic.  There is no ConstBool.
                  # Could be Lit_Digits?  But oil will need
                  # ConstFloat/ConstNum.
  ])

  # A compound word, in arith context, boolean context, or command context.
  # A['foo'] A["foo"] A[$foo] A["$foo"] A[${foo}] A["${foo}"]
  spec.AddKind('Word', ['Compound'])

  # NOTE: Not doing AddKindPairs() here because oil will have a different set
  # of keywords.  It will probably have for/in/while/until/case/if/else/elif,
  # and then func/proc.
  spec.AddKind('KW', [
      'DLeftBracket', 'Bang', 
      'For', 'While', 'Until', 'Do', 'Done', 'In', 'Case',
      'Esac', 'If', 'Fi', 'Then', 'Else', 'Elif', 'Function',
  ])

  # Assignment builtins -- treated as statically parsed keywords.  They are
  # different from keywords because env bindings can appear before, e.g.
  # FOO=bar local v.
  spec.AddKind('Assign', ['Declare', 'Export', 'Local', 'Readonly'])


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
