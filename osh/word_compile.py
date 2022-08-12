#!/usr/bin/env python2
"""
word_compile.py

This is called the "compile" stage because it happens after parsing, but it
doesn't depend on any values at runtime.
"""
from _devbuild.gen.id_kind_asdl import Id, Id_str
from _devbuild.gen.syntax_asdl import (
    Token, class_literal_term, class_literal_term_t, single_quoted,
    word_part_e, word_part_t,
)
from core.pyerror import log
from frontend import consts
from osh import string_ops
from qsn_ import qsn_native  # IsWhitespace

from typing import List, Optional, cast


def EvalCharLiteralForRegex(tok):
  # type: (Token) -> class_literal_term_t
  """For regex char classes.

  Similar logic as below.
  """
  id_ = tok.id
  value = tok.val

  if id_ == Id.Char_OneChar:
    c = value[1]
    s = consts.LookupCharC(c)
    return class_literal_term.ByteSet(s, tok.span_id)

  elif id_ == Id.Char_Hex:
    s = value[2:]
    i = int(s, 16)
    return class_literal_term.ByteSet(chr(i), tok.span_id)

  elif id_ == Id.Char_UBraced:
    s = value[3:-1]  # \u{123}
    i = int(s, 16)
    return class_literal_term.CodePoint(i, tok.span_id)

  elif id_ == Id.Expr_Name:
    # [b B] is the same as ['b' 'B']
    assert len(tok.val) == 1, tok
    return class_literal_term.ByteSet(tok.val[0], tok.span_id)

  else:
    raise AssertionError(Id_str(id_))


def EvalCStringToken(tok):
  # type: (Token) -> Optional[str]
  """
  This function is shared between echo -e and $''.

  $'' could use it at compile time, much like brace expansion in braces.py.
  """
  id_ = tok.id
  value = tok.val

  if 0:
    log('tok %s', tok)

  if id_ in (Id.Char_Literals, Id.Unknown_Backslash):
    # shopt -u parse_backslash detects Unknown_Backslash at PARSE time in Oil.
    return value

  # single quotes in the middle of a triple quoted string
  elif id_ == Id.Right_SingleQuote:
    return value

  elif id_ == Id.Char_OneChar:
    c = value[1]
    return consts.LookupCharC(c)

  elif id_ == Id.Char_Stop:  # \c returns a special sentinel
    return None

  elif id_ in (Id.Char_Octal3, Id.Char_Octal4):
    if id_ == Id.Char_Octal3:  # $'\377' (disallowed at parse time in Oil)
      s = value[1:]
    else:                      # echo -e '\0377'
      s = value[2:]

    i = int(s, 8)
    if i >= 256:
      i = i % 256
      # NOTE: This is for strict mode
      #raise AssertionError('Out of range')
    return chr(i)

  elif id_ == Id.Char_Hex:
    s = value[2:]
    i = int(s, 16)
    return chr(i)

  elif id_ in (Id.Char_Unicode4, Id.Char_Unicode8):
    s = value[2:]
    i = int(s, 16)
    #util.log('i = %d', i)
    return string_ops.Utf8Encode(i)

  elif id_ == Id.Char_UBraced:
    s = value[3:-1]  # \u{123}
    i = int(s, 16)
    return string_ops.Utf8Encode(i)

  else:
    raise AssertionError()


def EvalSingleQuoted(part):
  # type: (single_quoted) -> str
  if part.left.id in (Id.Left_SingleQuote, Id.Left_RSingleQuote,
      Id.Left_TSingleQuote, Id.Left_RTSingleQuote):

    # TODO: Strip leading whitespace for ''' and r'''
    if 0:
      for t in part.tokens:
        log('sq tok %s', t)

    tmp = [t.val for t in part.tokens]
    s = ''.join(tmp)

  elif part.left.id in (Id.Left_DollarSingleQuote, Id.Left_DollarTSingleQuote):
    # NOTE: This could be done at compile time

    # TODO: Strip leading whitespace for ''' and r'''

    tmp = [EvalCStringToken(t) for t in part.tokens]
    s = ''.join(tmp)

  else:
    raise AssertionError(part.left.id)
  return s


def IsLeadingSpace(s):
  # type: (str) -> bool
  """Determines if the token before ''' etc. can be stripped.
  
  Similar to qsn_native.IsWhitespace()
  """
  for ch in s:
    if ch not in ' \t':
      return False
  return True


# Whitespace stripping algorithm
#
# - First token should be WHITESPACE* NEWLINE.  Omit it
# - Last token should be WHITESPACE*
#   - Then go through all the other tokens that are AFTER token that ends with \n
#   - if tok.val[:n] is the same as the last token, then STRIP THAT PREFIX
# - Do you need to set a flag on the SingleQuoted part?
#
# TODO: do this all at compile time?

# These functions may mutate tok.val.  The LOSSLESS Syntax tree can be
# recovered with span_id.  (Is that the case with the new representation too?)

def RemoveLeadingSpaceDQ(parts):
  # type: (List[word_part_t]) -> None
  if len(parts) <= 1:  # We need at least 2 parts to strip anything
    return

  line_ended = False  # Think of it as a tiny state machine

  # The first token may have a newline
  UP_first = parts[0]
  if UP_first.tag_() == word_part_e.Literal:
    first = cast(Token, UP_first)
    #log('T %s', first_part)
    if qsn_native.IsWhitespace(first.val):
      # Remove the first part.  TODO: This could be expensive if there are many
      # lines.
      parts.pop(0)
    if first.val.endswith('\n'):
      line_ended = True

  UP_last = parts[-1]
  to_strip = None  # type: Optional[str]
  if UP_last.tag_() == word_part_e.Literal:
    last = cast(Token, UP_last)
    if IsLeadingSpace(last.val):
      to_strip = last.val
      parts.pop()  # Remove the last part

  if to_strip is not None:
    n = len(to_strip)
    for UP_p in parts:
      if UP_p.tag_() != word_part_e.Literal:
        line_ended = False
        continue

      p = cast(Token, UP_p)

      if line_ended:
        if p.val.startswith(to_strip):
          # MUTATING the part here
          p.val = p.val[n:]

      line_ended = False
      if p.val.endswith('\n'):
        line_ended = True
        #log('%s', p)


def RemoveLeadingSpaceSQ(tokens):
  # type: (List[Token]) -> None
  """
  In $''', we have Char_Literals \n
  In r''' and ''', we have Lit_Chars \n
  """
  if 0:  
    log('--')
    for tok in tokens:
      log('tok %s', tok)
    log('--')

  if len(tokens) <= 1:  # We need at least 2 parts to strip anything
    return

  line_ended = False

  first = tokens[0]
  if first.id in (Id.Lit_Chars, Id.Char_Literals):
    if qsn_native.IsWhitespace(first.val):
      tokens.pop(0)  # Remove the first part
    if first.val.endswith('\n'):
      line_ended = True

  last = tokens[-1]
  to_strip = None  # type: Optional[str]
  if last.id in (Id.Lit_Chars, Id.Char_Literals):
    if IsLeadingSpace(last.val):
      to_strip = last.val
      tokens.pop()  # Remove the last part

  if to_strip is not None:
    n = len(to_strip)
    for tok in tokens:
      if tok.id not in (Id.Lit_Chars, Id.Char_Literals):
        line_ended = False
        continue

      if line_ended:
        if tok.val.startswith(to_strip):
          # MUTATING the token here
          tok.val = tok.val[n:]

      line_ended = False
      if tok.val.endswith('\n'):
        line_ended = True
        #log('yes %r', tok.val)
