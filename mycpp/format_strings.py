"""
format_strings.py

Parse a printf format string so we can compile it to function calls.
"""
from __future__ import print_function

import re

from typing import List


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


class _Part:
    pass


class LiteralPart(_Part):

    def __init__(self, s: str):
        self.s = s
        self.strlen = len(s)

    def __repr__(self) -> str:
        return '(Literal %r)' % (self.s)


class SubstPart(_Part):

    def __init__(self, width: str, char_code: str, arg_num: int) -> None:
        self.width = width
        self.char_code = char_code
        self.arg_num = arg_num

    def __repr__(self) -> str:
        return '(Subst %r %s %d)' % (self.width, self.char_code, self.arg_num)


PAT = re.compile(
    '''
([^%]*)
(?:
  %([0-9]*)(.)   # optional number, and then character code
)?
''', re.VERBOSE)


def Parse(fmt: str) -> List[_Part]:

    arg_num = 0
    parts: List[_Part] = []
    for m in PAT.finditer(fmt):
        lit = m.group(1)
        width = m.group(2)
        char_code = m.group(3)

        if lit:
            parts.append(LiteralPart(lit))
        if char_code:
            if char_code == '%':
                part: _Part = LiteralPart('%')
            else:
                part = SubstPart(width, char_code, arg_num)
                arg_num += 1
            parts.append(part)

        #print('end =', m.end(0))

    return parts


# Note: This would be a lot easier in Oil!
# TODO: Should there be a char type?
"""
enum format_part {
  case Literal(s BigStr)
  case Subst(char_code BigStr, arg_num Int)
}

let PAT = ///
  < ~['%']* : lit >    # anything except %
  < '%' dot : subst >  # % and then any char
///

func Parse(fmt BigStr) {
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
