"""
format_strings.py

Parse a printf format string so we can compile it to function calls.
"""
from __future__ import print_function

import re


def DecodeMyPyString(s):
    # type: (str) -> str
    """Workaround for MyPy's weird escaping.

    Used below and in cppgen_pass.py.
    """
    byte_string = bytes(s, 'utf-8')

    # In Python 3
    # >>> b'\\t'.decode('unicode_escape')
    # '\t'

    raw_string = byte_string.decode('unicode_escape')
    return raw_string


class LiteralPart:
  def __init__(self, s):
    self.s = s
    self.strlen = len(s)

  def __repr__(self):
    return '(Literal %r)' % (self.s)


class SubstPart:
  def __init__(self, char_code, arg_num):
    self.char_code = char_code
    self.arg_num = arg_num

  def __repr__(self):
    return '(Subst %s %d)' % (self.char_code, self.arg_num)


PAT = re.compile('([^%]*)(%.)?')

def Parse(fmt):

  arg_num = 0
  parts = []
  for m in PAT.finditer(fmt):
    lit = m.group(1)
    subst = m.group(2)

    if lit:
      parts.append(LiteralPart(lit))
    if subst:
      char_code = subst[1]
      if char_code == '%':
        part = LiteralPart('%')
      else:
        part = SubstPart(char_code, arg_num)
      parts.append(part)
      arg_num += 1

    #print('end =', m.end(0))

  return parts

# Note: This would be a lot easier in Oil!
# TODO: Should there be a char type?
"""
enum format_part {
  case Literal(s Str)
  case Subst(char_code Str, arg_num Int)
}

let PAT = ///
  < ~['%']* : lit >    # anything except %
  < '%' dot : subst >  # % and then any char
///

func Parse(fmt Str) {
  var arg_num = 0
  let parts = []

  for (m in find(fmt, PAT)) {
    if (m.lit) {
      do parts.append(format_part.Literal(m.lit))
    }
    if (m.subst) {
      if (char_code == '%') {
        part = format_part.Literal('%')
      } else {
        part = format_part.Subst(char_code, arg_num)
      }
      do parts.append(part)
      set arg_num += 1
    }
  }
  return parts
}
"""

