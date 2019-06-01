#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
id_kind.py - Id and Kind definitions, used for Token, Word, Nodes, etc.

NOTE: If this changes, the lexer may need to be recompiled with
build/codegen.sh lexer.
"""
from __future__ import print_function

from _devbuild.gen.types_asdl import (bool_arg_type_e, bool_arg_type_t)
#from core.util import log

from typing import List, Tuple, Dict, Optional, TYPE_CHECKING
if TYPE_CHECKING:  # avoid circular build deps
  from _devbuild.gen.id_kind_asdl import Id_t, Kind_t


class IdSpec(object):
  """Identifiers that form the "spine" of the shell program representation."""

  def __init__(self, kind_lookup, bool_ops):
    # type: (Dict[int, int], Dict[int, bool_arg_type_t]) -> None
    self.id_str2int = {}  # type: Dict[str, int]
    self.kind_str2int = {}  # type: Dict[str, int]

    self.kind_lookup = kind_lookup  # Id int -> Kind int
    self.kind_name_list = []  # type: List[str]
    self.kind_sizes = []  # type: List[int]  # optional stats

    self.lexer_pairs = {}  # type: Dict[int, List[Tuple[bool, str, int]]]
    self.bool_ops = bool_ops  # type: Dict[int, bool_arg_type_t]

    # Incremented on each method call
    # IMPORTANT: 1-based indices match what asdl/gen_python.py does!!!
    self.id_index = 1
    self.kind_index = 1

  def LexerPairs(self, kind):
    # type: (Kind_t) -> List[Tuple[bool, str, Id_t]]
    from core import meta  # break circular dep
    result = []
    for is_regex, pat, id_int in self.lexer_pairs[kind.enum_id]:
      result.append((is_regex, pat, meta.IdInstance(id_int)))
    return result

  def _AddId(self, id_name, kind=None):
    # type: (str, Optional[int]) -> int
    """
    Args:
      id_name: e.g. BoolBinary_Equal
      kind: override autoassignment.  For AddBoolBinaryForBuiltin
    """
    t = self.id_index

    self.id_str2int[id_name] = t

    if kind is None:
      kind = self.kind_index
    self.kind_lookup[t] = kind

    self.id_index += 1  # mutate last
    return t  # the index we used

  def _AddKind(self, kind_name):
    # type: (str) -> None
    self.kind_str2int[kind_name] = self.kind_index
    #log('%s = %d', kind_name, self.kind_index)
    self.kind_index += 1
    self.kind_name_list.append(kind_name)

  def AddKind(self, kind_name, tokens):
    # type: (str, List[str]) -> None
    assert isinstance(tokens, list), tokens

    for name in tokens:
      id_name = '%s_%s' % (kind_name, name)
      self._AddId(id_name)

    # Must be after adding Id
    self._AddKind(kind_name)
    self.kind_sizes.append(len(tokens))  # debug info

  def AddKindPairs(self, kind_name, pairs):
    # type: (str, List[Tuple[str, str]]) -> None
    assert isinstance(pairs, list), pairs

    lexer_pairs = []
    for name, char_pat in pairs:
      id_name = '%s_%s' % (kind_name, name)
      id_int = self._AddId(id_name)
      # After _AddId
      lexer_pairs.append((False, char_pat, id_int))  # Constant

    self.lexer_pairs[self.kind_index] = lexer_pairs

    # Must be after adding Id
    self._AddKind(kind_name)
    self.kind_sizes.append(len(pairs))  # debug info

  def AddBoolKind(self,
                  kind_name,  # type: str
                  arg_type_pairs,  # type: List[Tuple[bool_arg_type_t, List[Tuple[str, str]]]]
                  ):
    # type: (...) -> None
    """
    Args:
      kind_name: string
      arg_type_pairs: dictionary of bool_arg_type_e -> []
    """
    lexer_pairs = []
    num_tokens = 0
    for arg_type, pairs in arg_type_pairs:
      #print(arg_type, pairs)

      for name, char_pat in pairs:
        # BoolUnary_f, BoolBinary_eq, BoolBinary_NEqual
        id_name = '%s_%s' % (kind_name, name)
        id_int = self._AddId(id_name)
        self.AddBoolOp(id_int, arg_type)  # register type
        lexer_pairs.append((False, char_pat, id_int))  # constant

      num_tokens += len(pairs)

    self.lexer_pairs[self.kind_index] = lexer_pairs

    # Must do this after _AddId()
    self._AddKind(kind_name)
    self.kind_sizes.append(num_tokens)  # debug info

  def AddBoolBinaryForBuiltin(self, id_name, kind):
    # type: (str, int) -> int
    """For [ = ] [ == ] and [ != ].

    These operators are NOT added to the lexer.  The are "lexed" as StringWord.
    """
    id_name = 'BoolBinary_%s' % id_name
    id_int = self._AddId(id_name, kind=kind)
    self.AddBoolOp(id_int, bool_arg_type_e.Str)
    return id_int

  def AddBoolOp(self, id_int, arg_type):
    # type: (int, bool_arg_type_t) -> None
    """Associate an ID integer with an bool_arg_type_e."""
    self.bool_ops[id_int] = arg_type


def AddKinds(spec):
  # type: (IdSpec) -> None
  # TODO: Unknown_Tok is OK, but Undefined_Id is better
  spec.AddKind('Undefined', ['Tok'])  # for initial state
  spec.AddKind('Unknown',   ['Tok'])  # for when nothing matches
  spec.AddKind('Eol',       ['Tok'])  # no more tokens on line (\0)

  spec.AddKind('Eof', ['Real', 'RParen', 'Backtick'])

  spec.AddKind('Ignored', ['LineCont', 'Space', 'Comment'])

  # Id.WS_Space is for lex_mode_e.ShCommand; Id.Ignored_Space is for
  # lex_mode_e.Arith
  spec.AddKind('WS', ['Space'])

  spec.AddKind('Lit', [
      'Chars', 'VarLike', 'ArrayLhsOpen', 'ArrayLhsClose',
      'Other', 'EscapedChar', 'RegexMeta',
      # Either brace expansion or keyword for { and }
      'LBrace', 'RBrace', 'Comma',
      'DRightBracket',     # the ]] that matches [[, NOT a keyword
      'TildeLike',         # tilde expansion
      'Pound',             #  for comment or VAROP state
      'Slash', 'Percent',  #  / # % for patsub, NOT unary op
      'Digits',            # for lex_mode_e.Arith
      'At',                # for ${a[@]}, in lex_mode_e.Arith
      'ArithVarLike',      # for $((var+1)).  Distinct from Lit_VarLike 'var='
      'CompDummy',        # A fake Lit_* token to get partial words during
                           # completion
  ])

  # For recognizing \` and \" and \\ within backticks.  There's an extra layer
  # of backslash quoting.
  spec.AddKind('Backtick', ['Right', 'Quoted', 'Other'])

  spec.AddKind('History', ['Op', 'Num', 'Search', 'Other'])

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

      # Oil [] {}
      'LBracket',
      'RBracket',
      'LBrace',
      'RBrace',
      'Bang',  # In Oil, this is an operator, not a keyword.  if !ls.
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
      'AndGreat',   # bash &> stdout/stderr to file
      'AndDGreat',  # bash &>> stdout/stderr append to file

      'GreatPlus',  # >+ is append in Oil
      'DGreatPlus', # >>+ is append to string in Oil
  ])

  # For Oil
  spec.AddKind('Fd', ['Number', 'Name'])

  # NOTE: This is for left/right WORDS only.  (( is not a word so it doesn't
  # get that.
  spec.AddKind('Left', [
      'DoubleQuote',
      'SingleQuote',
      'Backtick',           # `
      'DollarParen',        # $(
      'DollarBrace',        # ${
      'DollarDParen',       # $((
      'DollarBracket',      # $[ - synonym for $(( in bash and zsh
      'DollarDoubleQuote',  # $" for bash localized strings
      'DollarSingleQuote',  # $' for \n escapes
      'ProcSubIn',          # <( )
      'ProcSubOut',         # >( )

      'DollarSlash',        # $/ for Oil regex
      'AtBracket',          # @[ for Oil arrays
  ])

  spec.AddKind('Right', [
      'DoubleQuote',
      'SingleQuote',
      'Backtick',           # `
      'DollarBrace',        # }
      'DollarDParen',       # )) -- really the second one is a PushHint()
      # ArithSub2 is just Id.Arith_RBracket
      'DollarDoubleQuote',  # "
      'DollarSingleQuote',  # '

      # Disambiguated right parens
      'Subshell',      # )
      'FuncDef',       # )
      'CasePat',       # )
      'ArrayLiteral',  # )
      'ExtGlob',       # )
  ])

  spec.AddKind('ExtGlob', ['At', 'Star', 'Plus', 'QMark', 'Bang'])

  # First position of var sub ${
  # Id.VOp2_Pound -- however you can't tell the difference at first!  It could
  # be an op or a name.  So it makes sense to base i on the state.
  # Id.VOp2_At
  # But then you have AS_STAR, or Id.Arith_Star maybe

  spec.AddKind('VSub', [
      'DollarName',  # $foo
      'Name',        # 'foo' in ${foo}
      'Number',      # $0 .. $9
      'Bang',        # $!
      'At',          # $@  or  [@] for array subscripting
      'Pound',       # $#  or  ${#var} for length
      'Dollar',      # $$
      'Star',        # $*
      'Hyphen',      # $-
      'QMark',       # $?
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

  # Statically parse @P, so @x etc. is an error.
  spec.AddKindPairs('VOp0', [
      ('Q', '@Q'),  # ${x@Q} for quoting
      ('E', '@E'),
      ('P', '@P'),  # ${PS1@P} for prompt eval
      ('A', '@A'),
      ('a', '@a'),
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
  # Actually all of Arith could be folded into Op, because we are using
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
      # note: these 3 are not in Oil's Expr.  (Could be used in find dialect.)
      ('DAmp', '&&'), ('DPipe', '||'), ('Bang', '!'),

      # Bitwise ops
      ('DGreat', '>>'), ('DLess', '<<'),
      # Oil: ^ is exponent
      ('Amp', '&'), ('Pipe', '|'), ('Caret', '^'), ('Tilde', '~'),

      # 11 mutating operators:  =  +=  -=  etc.
      ('Equal', '='),
      ('PlusEqual', '+='), ('MinusEqual', '-='), ('StarEqual', '*='),
      ('SlashEqual', '/='), ('PercentEqual', '%='),
      ('DGreatEqual', '>>='), ('DLessEqual', '<<='),
      ('AmpEqual', '&='), ('PipeEqual', '|='),
      ('CaretEqual', '^=')
  ])

  # Oil expressions use Kind.Arith (above) and Kind.Expr (below)
  spec.AddKind('Expr', [
    'Name', 'Digits',
    'Dot', 'DColon', 'RArrow', 'RDArrow',
    'At', 'DoubleAt',  # splice operators

    'NotTilde',  # !~

    # Keywords are resolved after lexing, but otherwise behave like tokens.
    # NOTE: These are not used because pgen2 automatically creates a
    # gr.keywords dict in the grammar.
    #'Div', 'Xor', 
    #'And', 'Or', 'Not', 
    #'For',
    #'Is', 'In', 'If', 'Else',
    #'Match', 'Func',
  ])

  # This kind is for Node types that are NOT tokens.
  spec.AddKind('Node', [
     # Arithmetic nodes
     'PostDPlus', 'PostDMinus',  # Postfix inc/dec.
                                 # Prefix inc/dec use Arith_DPlus/Arith_DMinus.
     'UnaryPlus', 'UnaryMinus',  # +1 and -1, to distinguish from infix.
                                 # Actually we don't need this because we they
                                 # will be under Expr1/Plus vs Expr2/Plus.

     # Oil Command nodes?  Not used yet.
     #'Command', 'Assign', 'AndOr', 'Block', 'Subshell', 'Fork',
     #'FuncDef', 'ForEach', 'ForExpr', 'NoOp',

     #'UnaryExpr', 'BinaryExpr', 'TernaryExpr', 'FuncCall',
     #'ConstInt',  # for arithmetic.  There is no ConstBool.
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

      # Oil keywords.
      'Const', 'Set', 'SetGlobal', 'Var',  # assignment
      'SetVar',  # for OSH compatibility
      'Fork', 'Shell',  # blocks
      'Proc', 'Func',
      'Match', 'With',  # matching
      # not sure: yield

      # mycpp
      'Switch', 
      # mod (class) and 'init' (constructor) and maybe 'call'
      # record
      # enum
      # try except (no finally?)
      # use (instead of import)

      # dialects: wok rule, etc.
  ])

  # Assignment builtins -- treated as statically parsed keywords.  They are
  # different from keywords because env bindings can appear before, e.g.
  # FOO=bar local v.
  # "None" could either be a global variable or assignment to a local.
  # NOTE: We're not parsing export here.  Although it sets a global variable,
  # and has the same syntax, too many scripts use it in a dynamic fashion.
  spec.AddKind('Assign', ['Declare', 'Typeset', 'Local', 'Readonly', 'None'])

  # Unlike bash, we parse control flow statically.  They're not
  # dynamically-resolved builtins.
  spec.AddKind('ControlFlow', ['Break', 'Continue', 'Return', 'Exit'])

  # For C-escaped strings.
  spec.AddKind('Char', [
      'OneChar', 'Stop', 'Hex',
      # Two variants of Octal: \377, and \0377.
      'Octal3', 'Octal4',
      'Unicode4', 'Unicode8', 'Literals',
      'BadBackslash',  # \D or trailing \
  ])

  # For parsing globs and converting them to regexes.
  spec.AddKind('Glob', [
      'LBracket', 'RBracket',
      'Star', 'QMark', 'Bang', 'Caret',
      'EscapedChar', 'BadBackslash',
      'CleanLiterals', 'OtherLiteral',
      'Eof',
  ])

  # For C-escaped strings.
  spec.AddKind('Format', [
      'EscapedPercent',
      'Percent',  # starts another lexer mode
      'Flag', 'Num', 'Dot', 'Type',
  ])

  # For parsing prompt strings like PS1.
  spec.AddKind('PS', [
      'Subst', 'Octal3', 'LBrace', 'RBrace', 'Literals', 'BadBackslash',
  ])

  spec.AddKind('Range', ['Int', 'Char', 'Dots', 'Other', 'Eof'])


# Shared between [[ and test/[.
_UNARY_STR_CHARS = 'zn'  # -z -n
_UNARY_OTHER_CHARS = 'otvR'  # -o is overloaded
_UNARY_PATH_CHARS = 'abcdefghLprsSuwxOGN'  # -a is overloaded

_BINARY_PATH = ['ef', 'nt', 'ot']
_BINARY_INT = ['eq', 'ne', 'gt', 'ge', 'lt', 'le']


def _Dash(strs):
  # type: (List[str]) -> List[Tuple[str, str]]
  # Gives a pair of (token name, string to match)
  return [(s, '-' + s) for s in strs]


def AddBoolKinds(spec):
  # type: (IdSpec) -> None
  spec.AddBoolKind('BoolUnary', [
      (bool_arg_type_e.Str, _Dash(list(_UNARY_STR_CHARS))),
      (bool_arg_type_e.Other, _Dash(list(_UNARY_OTHER_CHARS))),
      (bool_arg_type_e.Path, _Dash(list(_UNARY_PATH_CHARS))),
  ])

  spec.AddBoolKind('BoolBinary', [
      (bool_arg_type_e.Str, [
          ('GlobEqual', '='), ('GlobDEqual', '=='), ('GlobNEqual', '!='),
          ('EqualTilde', '=~'),
      ]),
      (bool_arg_type_e.Path, _Dash(_BINARY_PATH)),
      (bool_arg_type_e.Int, _Dash(_BINARY_INT)),
  ])

  Id = spec.id_str2int
  # logical, arity, arg_type
  spec.AddBoolOp(Id['Op_DAmp'], bool_arg_type_e.Undefined)
  spec.AddBoolOp(Id['Op_DPipe'], bool_arg_type_e.Undefined)
  spec.AddBoolOp(Id['KW_Bang'], bool_arg_type_e.Undefined)

  spec.AddBoolOp(Id['Redir_Less'], bool_arg_type_e.Str)
  spec.AddBoolOp(Id['Redir_Great'], bool_arg_type_e.Str)


def SetupTestBuiltin(id_spec,  # type: IdSpec
                     unary_lookup,  # type: Dict[str, int]
                     binary_lookup,  # type: Dict[str, int]
                     other_lookup,  # type: Dict[str, int]
                     ):
  # type: (...) -> None
  """Setup tokens for test/[.

  Similar to _AddBoolKinds above.  Differences:
  - =~ doesn't exist
  - && -> -a, || -> -o
  - ( ) -> Op_LParen (they don't appear above)
  """
  Id = id_spec.id_str2int
  Kind = id_spec.kind_str2int

  for letter in _UNARY_STR_CHARS + _UNARY_OTHER_CHARS + _UNARY_PATH_CHARS:
    id_name = 'BoolUnary_%s' % letter
    unary_lookup['-' + letter] = Id[id_name]

  for s in _BINARY_PATH + _BINARY_INT:
    id_name = 'BoolBinary_%s' % s
    binary_lookup['-' + s] = Id[id_name]

  # Like the [[ definition above, but without globbing and without =~ .

  for id_name, token_str in [
      ('Equal', '='), ('DEqual', '=='), ('NEqual', '!=')]:
    id_int = id_spec.AddBoolBinaryForBuiltin(id_name, Kind['BoolBinary'])

    binary_lookup[token_str] = id_int

  # Some of these names don't quite match, but it keeps the BoolParser simple.
  binary_lookup['<'] = Id['Redir_Less']
  binary_lookup['>'] = Id['Redir_Great']

  # NOTE: -a and -o overloaded as unary prefix operators BoolUnary_a and
  # BoolUnary_o.  The parser rather than the tokenizer handles this.
  other_lookup['!'] = Id['KW_Bang']  # like [[ !
  other_lookup['('] = Id['Op_LParen']
  other_lookup[')'] = Id['Op_RParen']

  other_lookup[']'] = Id['Arith_RBracket']  # For closing ]
