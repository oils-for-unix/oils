#!/usr/bin/python
"""
word_compile.py

This is called the "compile" stage because it happens after parsing, but it
doesn't depend on any values at runtime.
"""

from core.id_kind import Id

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

# TODO: Strict mode syntax errors:
#
# \x is a syntax error -- needs two digits (It's like this in C)
# \0777 is a syntax error -- we shouldn't do modulus
# \d could be a syntax error -- it is better written as \\d

def EvalCStringToken(id_, value):
  """
  This function is shared between echo -e and $''.

  $'' could use it at compile time, much like brace expansion in braces.py.
  """
  if id_ == Id.Char_Literals:
    return value

  elif id_ == Id.Char_BadBackslash:  # TODO: error in strict mode
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
    return unichr(i).encode('utf-8')  # Stay in the realm of bytes

  else:
    raise AssertionError

