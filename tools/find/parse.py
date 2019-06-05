#!/usr/bin/python
"""
parse.py
"""
from __future__ import print_function

import sys

from core.util import log

from pgen2 import driver
from pgen2 import pgen
from pgen2 import parse
from pgen2 import token

from oil_lang.expr_parse import NoSingletonAction


def Tokens(strs):
  start = end = (1, 0)  # dummy location data
  line_text = ''
  for s in strs:
    #log('tok = %r', s)
    if s in OPMAP:
      typ = token.OP
    else:
      typ = token.STRING
    yield (typ, s, start, end, line_text)
  yield (token.ENDMARKER, '', start, end, line_text)


# NOTE: should be disjoint from Python's
OPMAP = {
    '!': 101,
    '(': 102,
    ')': 103,
    '-o': 104,
    '-a': 105,
    ',': 106,
    ';': 107,
    '+': 108,

    '-true': 190,
    '-false': 191,

    '-name': 200,
    '-type': 201,
    '-print': 202,
    '-print0': 203,
    '-printf': 204,
    '-exec': 205,
}


class TokenDef(object):
  def GetTerminalNum(self, label):
    """ e.g. NAME -> 1 """
    itoken = getattr(token, label, None)
    assert isinstance(itoken, int), label
    assert itoken in token.tok_name, label
    return itoken

  def GetOpNum(self, value):
    """ e.g '(' -> LPAR """
    return OPMAP[value]


class ParseTreePrinter(object):
  """Prints a tree of PNode instances."""
  def __init__(self, names):
    # type: (Dict[int, str]) -> None
    self.names = names

  def Print(self, pnode, f=sys.stdout, indent=0, i=0):
    # type: (PNode, IO[str], int, int) -> None

    ind = '  ' * indent
    # NOTE:
    # - value is filled in for TOKENS, but it's always None for PRODUCTIONS.
    # - context is (prefix, (lineno, column)), where lineno is 1-based, and
    #   'prefix' is a string of whitespace.
    #   e.g. for 'f(1, 3)', the "3" token has a prefix of ' '.
    if isinstance(pnode.tok, tuple):
      v = pnode.tok[0]
    else:
      v = '-'
    f.write('%s%d %s %s\n' % (ind, i, self.names[pnode.typ], v))
    if pnode.children:  # could be None
      for i, child in enumerate(pnode.children):
        self.Print(child, indent=indent+1, i=i)


def main(argv):
  grammar_path = 'tools/find/find.pgen2'
  tok_def = TokenDef()
  with open(grammar_path) as f:
    gr = pgen.MakeGrammar(f, tok_def=tok_def)

  p = parse.Parser(gr, convert=NoSingletonAction)
  tokens = Tokens(argv[1:])

  #print(list(tokens))
  start_symbol = 'eval_input'
  #start_symbol = 'factor_input'
  pnode = driver.PushTokens(p, tokens, gr, start_symbol, opmap=OPMAP)

  names = {}
  for k, v in gr.number2symbol.items():
    # eval_input == 256.  Remove?
    assert k >= 256, (k, v)
    assert k not in names, k
    names[k] = v
  # TODO: These overlap
  for k, v in token.tok_name.items():
    if k != token.NT_OFFSET:
      assert k not in names, k
      names[k] = v
  for name, num in OPMAP.items():
    assert num not in names, num
    names[num] = name

  print(pnode)
  printer = ParseTreePrinter(names)
  printer.Print(pnode)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
