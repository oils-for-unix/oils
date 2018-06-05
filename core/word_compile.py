#!/usr/bin/env python
"""
word_compile.py

This is called the "compile" stage because it happens after parsing, but it
doesn't depend on any values at runtime.
"""

from core import util

from osh.meta import Id
from osh.meta import runtime

var_flags_e = runtime.var_flags_e


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


def Utf8Encode(code):
  """
  Args:
    code: Unicode code point (integer)
  Returns:
    utf-8 encoded str
  """
  #print('Utf8Encode code %r' % code)
  if code <= 0x7F:
      bytes_ = [code & 0x7F]
      # chars[0] = code & 0x7F
      # count = 0
  elif code > 0x10FFFF:
      # unicode replacement character
      bytes_ = [0xEF, 0xBF, 0xBD]
      # chars[0] = 0xEF
      # chars[1] = 0xBF
      # chars[2] = 0xBD
      # chars[3] = 0
      # count = 2
  else:
      if code <= 0x7FF:
	  num_continuation_bytes = 1
      elif code <= 0xFFFF:
	  num_continuation_bytes = 2
      else:
	  num_continuation_bytes = 3
      
      bytes_ = []
      for i in xrange(num_continuation_bytes):
          bytes_.append(0x80 | (code & 0x3F))
	  #bytes_[count-i] = 0x80 | (code & 0x3F)
	  code >>= 6
      bytes_.append((0x1E << (6-num_continuation_bytes)) | (code & (0x3F >> num_continuation_bytes)))
      bytes_.reverse()
      #chars[1+count] = 0

  # print('chars %r' % chars)
  return "".join(chr(b % 256) for b in bytes_)
  # s = ''
  # for i in xrange(count+1):
  #   print('i = %d' % chars[i])
  #   s += chr(chars[i] % 256)
  # return s
#return unichr(c).encode('utf-8')


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

  elif id_ == Id.Char_BadBackslash:
    if 1:  # TODO: error in strict mode
      # Either \A or trailing \ (A is not a valid backslash escape)
      util.warn('Invalid backslash escape')
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
    return unichr(i).encode('utf-8')  # Stay in the realm of bytes

  else:
    raise AssertionError


#
# Assignment
#

def ParseAssignFlags(flag_args):
  """
  Args:
    flag_args looks like ['-r', '-x'] or ['-rx'], etc.

  Returns:
    A list of var_flags_e

  NOTE: Any errors should be caught at PARSE TIME, not compile time.
  """
  flags = []
  for arg in flag_args:
    assert arg[0] == '-', arg
    for char in arg[1:]:
      if char == 'x':
        flags.append(var_flags_e.Exported)
      elif char == 'r':
        flags.append(var_flags_e.ReadOnly)
      else:
        # -a is ignored right now?
        pass
  return flags

