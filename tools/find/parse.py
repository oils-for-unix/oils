#!/usr/bin/env python2
"""
parse.py
"""
from __future__ import print_function

import sys

#from core.util import log

# build/dev.sh minimal generates this
from _devbuild.gen.find_asdl import (
    expr, op_e
)
#from _devbuild.gen import find_nt  # non-terminals for the 'transformer'

from pgen2 import driver
from pgen2 import pgen
from pgen2 import parse
from pgen2 import token

from oil_lang.expr_parse import NoSingletonAction

from typing import TYPE_CHECKING, Dict, IO
if TYPE_CHECKING:
  from pgen2.parse import PNode


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


OPS = [
    '!',
    '(', ')',
    '-o', '-a',
    ',',
    ';', '+',

    '-true', '-false',

    '-name', '-iname', 
    '-lname', '-ilname', 
    '-regex', '-iregex', 
    '-path', '-ipath', 

    '-size', '-type', '-xtype', '-perm',

    '-group', '-user',
    '-gid', '-uid',
    '-nogroup', '-nouser',

    '-empty', '-executable', '-readable', '-writable',

    '-amin', '-anewer', '-atime',
    '-cmin', '-cnewer', '-ctime',
    '-mmin', '-newer', '-mtime',  # note -newer not -mnewer
    '-newerXY',

    '-delete',
    '-prune', '-quit',

    '-print', '-print0', '-printf', '-ls',
    '-fprint', '-fprint0', '-fprintf', '-fls',

    '-exec', '-execdir', '-ok', '-okdir',
]

OPMAP = {}
for i, op in enumerate(OPS):
  # Start at 100 so it doesn't overlap with Python tokens
  OPMAP[op] = i + 100


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
  """Prints a tree of PNode instances.

  Copied from oil_lang/expr_parse.py
  """

  def __init__(self, names):
    # type: (Dict[int, str]) -> None
    self.names = names

  def Print(self, pnode, f=sys.stdout, indent=0, i=0):
    # type: (PNode, IO[str], int, int) -> None

    ind = '  ' * indent
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
  start_symbol = 'start'
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

  #print(pnode)
  printer = ParseTreePrinter(names)
  printer.Print(pnode)

  # TODO: Translate pnode into a tree like this.
  left = expr.True_()
  right = expr.PathTest(False, '*.py')
  ast_node = expr.Binary(op_e.And, left, right)
  ast_node.PrettyPrint()
  print()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
