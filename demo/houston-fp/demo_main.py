#!/usr/bin/env python2
from __future__ import print_function
"""
houston-fp demo
"""

import sys

from demo_asdl import Token, expr_t, word_part_t, value, value_t

from typing import List, Optional, cast


def main(argv):
  # type: (List[str]) -> None

  # Better example:
  #
  # 1. Lexer() returning Token
  # 2. Mututally recursive parsers storing Token as first class variants:
  #    WordParser
  #    ArithParser
  #    BoolParser
  #    ExprParser
  #
  # 3. Evaluators using Token
  #
  # 4. Errors bubbled up to top-level, using Token
  #
  # ...
  #
  # TypeScript example: https://github.com/oilshell/yaks

  tok = Token(3, 4, 5, 'foo')
  print(tok)

  val = None  # type: Optional[value_t]
  ival = value.Int(42)

  val = ival

  my_word_part = None  # type: Optional[word_part_t]
  my_expr = None  # type: Optional[expr_t]

  my_word_part = tok
  my_expr = tok

  # Errors
  #my_word_part = val

  #val = tok


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
