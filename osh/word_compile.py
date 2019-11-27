#!/usr/bin/env python2
"""
word_compile.py

This is called the "compile" stage because it happens after parsing, but it
doesn't depend on any values at runtime.
"""

from typing import Any, Optional

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import class_literal_term, class_literal_term_t, token
from core import ui
from osh import string_ops


_ONE_CHAR = {
    '0': '\0',
    'a': '\a',
    'b': '\b',
    'e': '\x1b',
    'E': '\x1b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
    'v': '\v',
    '\\': '\\',
    "'": "'",  # for $'' only, not echo -e
    '"': '"',  # not sure why this is escaped within $''
}

def EvalCharLiteralForRegex(tok):
  # type: (token) -> class_literal_term_t
  """For regex char classes.

  Similar logic as below.
  """
  id_ = tok.id
  value = tok.val

  if id_ == Id.Char_OneChar:
    c = value[1]
    s = _ONE_CHAR[c]
    return class_literal_term.ByteSet(s, tok.span_id)

  elif id_ == Id.Char_Hex:
    s = value[2:]
    i = int(s, 16)
    return class_literal_term.ByteSet(chr(i), tok.span_id)

  elif id_ in (Id.Char_Unicode4, Id.Char_Unicode8):
    s = value[2:]
    i = int(s, 16)
    return class_literal_term.CodePoint(i, tok.span_id)

  else:
    raise AssertionError


# TODO: Strict mode syntax errors:
#
# \x is a syntax error -- needs two digits (It's like this in C)
# \0777 is a syntax error -- we shouldn't do modulus
# \d could be a syntax error -- it is better written as \\d

def EvalCStringToken(id_, value):
  # type: (Id_t, str) -> Optional[str]
  """
  This function is shared between echo -e and $''.

  $'' could use it at compile time, much like brace expansion in braces.py.
  """
  if id_ == Id.Char_Literals:
    return value

  elif id_ == Id.Char_BadBackslash:
    if 1:
      # TODO:
      # - make this an error in strict mode
      # - improve the error message.  We don't have a span_id!
      # Either \A or trailing \ (A is not a valid backslash escape)
      ui.Stderr('warning: Invalid backslash escape in C-style string')
    return value

  elif id_ == Id.Char_OneChar:
    c = value[1]
    return _ONE_CHAR[c]

  elif id_ == Id.Char_Stop:  # \c returns a special sentinel
    return None

  elif id_ in (Id.Char_Octal3, Id.Char_Octal4):
    if id_ == Id.Char_Octal3:  # $'\377'
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

  else:
    raise AssertionError
