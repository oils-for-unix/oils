#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
id_kind.py - Id and Kind definitions, used for Token, Word, Nodes, etc.
"""

from core import util


_ID_TO_KIND = {}  # type: dict

def LookupKind(id_):
  return _ID_TO_KIND[id_]


_ID_NAMES = {}  # type: dict

def IdName(id_):
  return _ID_NAMES[id_]


class Id(object):
  """Token and op type.

  The evaluator must consider all Ids.
  """
  def __init__(self, enum_value):
    self.enum_value = enum_value

  def __eq__(self, other):
    # NOTE: We need to compare to ints too because of the ID hash tables.  They
    # are keyed by index, and then an equality test happens.
    if isinstance(other, int):
      return self.enum_value == other

    return self.enum_value == other.enum_value

  def __hash__(self):
    return hash(self.enum_value)

  def __repr__(self):
    return IdName(self.enum_value)


class Kind(object):
  """A coarser version of Id, used to make parsing decisions."""
  pass


class IdSpec(object):
  """Identifiers that form the "spine" of the shell program representation."""

  def __init__(self, token_names, kind_lookup, bool_ops):
    self.id_enum = Id
    self.kind_enum = Kind
    self.token_names = token_names  # integer -> string Id
    self.kind_lookup = kind_lookup  # Id -> Kind

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
    id_val = Id(self.token_index)
    setattr(self.id_enum, token_name, id_val)
    self.token_names[self.token_index] = token_name
    self.kind_lookup[self.token_index] = self.kind_index
    return id_val

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
      id_val = self._AddId(token_name)
      # After _AddId
      lexer_pairs.append((False, char_pat, id_val))  # Constant

    self.lexer_pairs[self.kind_index] = lexer_pairs

    # Must be after adding Id
    self._AddKind(kind_name)
    self.kind_sizes.append(len(pairs))  # debug info

  def AddBoolKind(self, kind_name, arg_type_pairs):
    """
    Args:
    """
    lexer_pairs = []
    num_tokens = 0
    for arg_type, pairs in arg_type_pairs.items():
      #print(arg_type, pairs)

      for name, char_pat in pairs:
        # BoolUnary_f, BoolBinary_eq, BoolBinary_NEqual
        token_name = '%s_%s' % (kind_name, name)
        id_val = self._AddId(token_name)
        # not logical
        self.AddBoolOp(id_val, arg_type)
        # After _AddId.
        lexer_pairs.append((False, char_pat, id_val))  # constant

      num_tokens += len(pairs)

    self.lexer_pairs[self.kind_index] = lexer_pairs

    # Must do this after _AddId()
    self._AddKind(kind_name)
    self.kind_sizes.append(num_tokens)  # debug info

  def AddBoolOp(self, id_, arg_type):
    self.bool_ops[id_] = arg_type


def _AddKinds(spec):
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
      'At',                # for ${a[@]}, in LexMode.ARITH
      'ArithVarLike',      # for $((var+1)).  Distinct from Lit_VarLike 'var='
  ])

  spec.AddKind('Op', [
      'Newline',  # mostly equivalent to SEMI
      'Amp',      # &
      'Pipe',     # |
      'PipeAmp',  # |& -- bash extension for stderr
      'DAmp',     # &&
      'DPipe',    # ||
      'Semi',     # ;
      'DSemi',    # ;; for case

      'LParen',   # For subshell.  Not Kind.Left because it's NOT a WordPart.
      'RParen',   # Default, will be translated to Id.Right_*
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
      ('QMark', '?'), ('Colon', ':'),  # Ternary Op: a < b ? 0 : 1
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
     'ArithVar',                 # a bare variable like (( foo = bar ))

     # Command nodes
     'Command', 'Assign', 'AndOr', 'Block', 'Subshell', 'Fork',
     'FuncDef', 'ForEach', 'ForExpr', 'NoOp',

     # TODO: Unify ExprNode and BNode under these Unary, Binary, Ternary nodes.
     # They hold one, two, or three words.
     'UnaryExpr', 'BinaryExpr', 'TernaryExpr', 'FuncCall',
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
      'Time',
  ])

  # Assignment builtins -- treated as statically parsed keywords.  They are
  # different from keywords because env bindings can appear before, e.g.
  # FOO=bar local v.
  # "None" could either be a global variable or assignment to a local.
  # NOTE: We're not parsing export here.  Although it sets a global variable,
  # and has the same syntax, too many scripts use it in a dynamic fashion.
  spec.AddKind('Assign', ['Declare', 'Local', 'Readonly', 'None'])

  # Unlike bash, we parse control flow statically.  They're not
  # dynamically-resolved builtins.
  spec.AddKind('ControlFlow', ['Break', 'Continue', 'Return'])


# Id -> OperandType
BOOL_OPS = {}  # type: dict

UNARY_FILE_CHARS = tuple('abcdefghLprsStuwxOGN')

OperandType = util.Enum('OperandType', 'Undefined Path Int Str Other'.split())


def _Dash(strs):
  # Gives a pair of (token name, string to match)
  return [(s, '-' + s) for s in strs]


def _AddBoolKinds(spec):
  spec.AddBoolKind('BoolUnary', {
      OperandType.Str: _Dash(list('zn')),  # -z -n
      OperandType.Other: _Dash(list('ovR')),
      OperandType.Path: _Dash(UNARY_FILE_CHARS),
  })

  spec.AddBoolKind('BoolBinary', {
      OperandType.Str: [
          ('Equal', '='), ('DEqual', '=='), ('NEqual', '!='),
          ('EqualTilde', '=~'),
      ],
      OperandType.Path: _Dash(['ef', 'nt', 'ot']),
      OperandType.Int: _Dash(['eq', 'ne', 'gt', 'ge', 'lt', 'le']),
  })

  # logical, arity, arg_type
  spec.AddBoolOp(Id.Op_DAmp, OperandType.Undefined)
  spec.AddBoolOp(Id.Op_DPipe, OperandType.Undefined)
  spec.AddBoolOp(Id.KW_Bang, OperandType.Undefined)

  spec.AddBoolOp(Id.Redir_Less, OperandType.Str)
  spec.AddBoolOp(Id.Redir_Great, OperandType.Str)


#
# Instantiate the spec
#


ID_SPEC = IdSpec(_ID_NAMES, _ID_TO_KIND, BOOL_OPS)

_AddKinds(ID_SPEC)
_AddBoolKinds(ID_SPEC)  # must come second

# Debug
_kind_sizes = ID_SPEC.kind_sizes


#
# Redirect Tables associated with IDs
#
# These might be osh specific.
#

REDIR_DEFAULT_FD = {
    # filename
    Id.Redir_Less: 0,  # cat <input.txt means cat 0<input.txt
    Id.Redir_Great: 1,
    Id.Redir_DGreat: 1,
    Id.Redir_Clobber: 1,
    Id.Redir_LessGreat: 1,  # TODO: What does echo <>foo do?

    # descriptor
    Id.Redir_GreatAnd: 1,  # echo >&2  means echo 1>&2
    Id.Redir_LessAnd: 0,   # echo <&3 means echo 0<&3, I think

    Id.Redir_TLess: 0,  # here word

    # here docs included
    Id.Redir_DLess: 0,
    Id.Redir_DLessDash: 0,
}

RedirType = util.Enum('RedirType', 'Path Desc Here'.split())

REDIR_TYPE = {
    # filename
    Id.Redir_Less: RedirType.Path,
    Id.Redir_Great: RedirType.Path,
    Id.Redir_DGreat: RedirType.Path,
    Id.Redir_Clobber: RedirType.Path,
    Id.Redir_LessGreat: RedirType.Path,  # TODO: What does echo <>foo do?

    # descriptor
    Id.Redir_GreatAnd: RedirType.Desc,
    Id.Redir_LessAnd: RedirType.Desc,

    Id.Redir_TLess: RedirType.Here,  # here word
    # note: here docs aren't included
}
