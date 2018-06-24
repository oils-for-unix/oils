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

from core import util
log = util.log


class IdSpec(object):
  """Identifiers that form the "spine" of the shell program representation."""

  def __init__(self, id_enum, kind_enum,
               token_names, instance_lookup, kind_lookup, bool_ops):
    self.id_enum = id_enum
    self.kind_enum = kind_enum
    self.token_names = token_names  # integer -> string Id
    self.instance_lookup = instance_lookup
    self.kind_lookup = kind_lookup  # Id -> Kind

    self.kind_sizes = []  # stats

    self.lexer_pairs = {}  # Kind -> [(regex, Id), ...]
    self.bool_ops = bool_ops  # table of runtime values

    # Incremented on each method call
    self.token_index = 0
    self.kind_index = 0

  def LexerPairs(self, kind):
    return self.lexer_pairs[kind]

  def _AddId(self, token_name, kind=None):
    """
    Args:
      token_name: e.g. BoolBinary_Equal
      kind: override autoassignment.  For AddBoolBinaryForBuiltin
    """
    self.token_index += 1  # leave out 0 I guess?
    # The ONLY place that Id() is instantiated.
    id_val = self.id_enum(self.token_index)
    setattr(self.id_enum, token_name, id_val)

    t = self.token_index
    self.token_names[t] = token_name
    self.instance_lookup[t] = id_val
    if kind is None:
      kind = self.kind_index
    self.kind_lookup[t] = kind
    return id_val

  def _AddKind(self, kind_name):
    # TODO: Should be instantiated or folded into ASDL.
    setattr(self.kind_enum, kind_name, self.kind_index)
    #log('%s = %d', kind_name, self.kind_index)
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
      kind_name: string
      arg_type_pairs: dictionary of bool_arg_type_e -> []
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

  def AddBoolBinaryForBuiltin(self, token_name, kind, bool_arg_type_e):
    """For [ = ] [ == ] and [ != ].
    
    These operators are NOT added to the lexer.  The are "lexed" as StringWord.
    """
    token_name = 'BoolBinary_%s' % token_name
    id_val = self._AddId(token_name, kind=kind)
    self.AddBoolOp(id_val, bool_arg_type_e.Str)
    return id_val

  def AddBoolOp(self, id_, arg_type):
    self.bool_ops[id_] = arg_type


def AddKinds(spec):
  # TODO: Unknown_Tok is OK, but Undefined_Id is better
  spec.AddKind('Undefined', ['Tok'])  # for initial state
  spec.AddKind('Unknown',   ['Tok'])  # for when nothing matches
  spec.AddKind('Eol',       ['Tok'])  # no more tokens on line (\0)

  spec.AddKind('Eof', ['Real', 'RParen', 'Backtick'])

  spec.AddKind('Ignored', ['LineCont', 'Space', 'Comment'])

  # Id.WS_Space is for lex_mode_e.OUTER; Id.Ignored_Space is for
  # lex_mode_e.ARITH
  spec.AddKind('WS', ['Space'])

  spec.AddKind('Lit', [
      'Chars', 'VarLike', 'Other', 'EscapedChar',
      # Either brace expansion or keyword for { and }
      'LBrace', 'RBrace', 'Comma',
      'DRightBracket',     # the ]] that matches [[, NOT a keyword
      'Tilde',             # tilde expansion
      'Pound',             #  for comment or VAROP state
      'Slash', 'Percent',  #  / # % for patsub, NOT unary op
      'Digits',            # for lex_mode_e.ARITH
      'At',                # for ${a[@]}, in lex_mode_e.ARITH
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
      'AndGreat',   # bash &> stdout/stderr to file
      'AndDGreat',  # bash &>> stdout/stderr append to file
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
      'ExtGlob',       # )
  ])

  spec.AddKind('ExtGlob', ['At', 'Star', 'Plus', 'QMark', 'Bang'])

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


# Shared between [[ and test/[.
_UNARY_STR_CHARS = 'zn'  # -z -n
_UNARY_OTHER_CHARS = 'otvR'  # -o is overloaded 
_UNARY_PATH_CHARS = 'abcdefghLprsSuwxOGN'  # -a is overloaded

_BINARY_PATH = ['ef', 'nt', 'ot']
_BINARY_INT = ['eq', 'ne', 'gt', 'ge', 'lt', 'le']


def _Dash(strs):
  # Gives a pair of (token name, string to match)
  return [(s, '-' + s) for s in strs]


def AddBoolKinds(spec, Id, bool_arg_type_e):
  spec.AddBoolKind('BoolUnary', {
      bool_arg_type_e.Str: _Dash(list(_UNARY_STR_CHARS)),
      bool_arg_type_e.Other: _Dash(list(_UNARY_OTHER_CHARS)),
      bool_arg_type_e.Path: _Dash(list(_UNARY_PATH_CHARS)),
  })

  spec.AddBoolKind('BoolBinary', {
      bool_arg_type_e.Str: [
          ('GlobEqual', '='), ('GlobDEqual', '=='), ('GlobNEqual', '!='),
          ('EqualTilde', '=~'),
      ],
      bool_arg_type_e.Path: _Dash(_BINARY_PATH),
      bool_arg_type_e.Int: _Dash(_BINARY_INT),
  })

  # logical, arity, arg_type
  spec.AddBoolOp(Id.Op_DAmp, bool_arg_type_e.Undefined)
  spec.AddBoolOp(Id.Op_DPipe, bool_arg_type_e.Undefined)
  spec.AddBoolOp(Id.KW_Bang, bool_arg_type_e.Undefined)

  spec.AddBoolOp(Id.Redir_Less, bool_arg_type_e.Str)
  spec.AddBoolOp(Id.Redir_Great, bool_arg_type_e.Str)


def SetupTestBuiltin(Id, Kind, id_spec,
                     unary_lookup, binary_lookup, other_lookup,
                     bool_arg_type_e):
  """Setup tokens for test/[.

  Similar to _AddBoolKinds above.  Differences:
  - =~ doesn't exist
  - && -> -a, || -> -o
  - ( ) -> Op_LParen (they don't appear above)
  """ 
  for letter in _UNARY_STR_CHARS + _UNARY_OTHER_CHARS + _UNARY_PATH_CHARS:
    token_name = 'BoolUnary_%s' % letter
    unary_lookup['-' + letter] = getattr(Id, token_name)

  for s in _BINARY_PATH + _BINARY_INT:
    token_name = 'BoolBinary_%s' % s
    binary_lookup['-' + s] = getattr(Id, token_name)

  # Like the [[ definition above, but without globbing and without =~ .

  for token_name, token_str in [
      ('Equal', '='), ('DEqual', '=='), ('NEqual', '!=')]:
    id_val = id_spec.AddBoolBinaryForBuiltin(token_name, Kind.BoolBinary,
                                             bool_arg_type_e)

    binary_lookup[token_str] = id_val

  # Some of these names don't quite match, but it keeps the BoolParser simple.
  binary_lookup['<'] = Id.Redir_Less
  binary_lookup['>'] = Id.Redir_Great

  # NOTE: -a and -o overloaded as unary prefix operators BoolUnary_a and
  # BoolUnary_o.  The parser rather than the tokenizer handles this.
  other_lookup['!'] = Id.KW_Bang  # like [[ !
  other_lookup['('] = Id.Op_LParen
  other_lookup[')'] = Id.Op_RParen

  other_lookup[']'] = Id.Arith_RBracket  # For closing ]
