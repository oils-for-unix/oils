"""
tdop_lexer.py
"""
from __future__ import print_function

import re
from typing import Iterator, Tuple, cast, TYPE_CHECKING

from asdl.tdop import Token

if TYPE_CHECKING:
  TupleStr4 = Tuple[str, str, str, str]
else:
  TupleStr4 = None  # Using runtime stub

#
# Using the pattern here: http://effbot.org/zone/xml-scanner.htm
#

# NOTE: () and [] need to be on their own so (-1+2) works
TOKEN_RE = re.compile(r"""
\s* (?: (\d+) | (\w+) | ( [\-\+\*/%!~<>=&^|?:,]+ ) | ([\(\)\[\]]) )
""", re.VERBOSE)

def Tokenize(s):
  # type: (str) -> Iterator[Token]
  for item in TOKEN_RE.findall(s):
    # The type checker can't know the true type of item!
    item = cast(TupleStr4, item)
    if item[0]:
      typ = 'number'
      val = item[0]
    elif item[1]:
      typ = 'name'
      val = item[1]
    elif item[2]:
      typ = item[2]
      val = item[2]
    elif item[3]:
      typ = item[3]
      val = item[3]
    yield Token(typ, val)
