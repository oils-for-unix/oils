#!/usr/bin/env python2
"""
arith_parse_gen.py
"""
from __future__ import print_function

import collections
import sys

from osh import arith_parse
from core.util import log


def main(argv):
  spec = arith_parse.Spec()

  print("""\
#include "osh_arith_parse.h"

using syntax_asdl::arith_expr_t;
using syntax_asdl::word_t;
using tdop::TdopParser;
""")

  to_declare = collections.defaultdict(set)

  for row in spec.nud_lookup.itervalues():
    mod_name, func_name = row.ModuleAndFuncName()
    to_declare[mod_name].add(('N', func_name))

  log('')
  log('')

  # TODO: namespace are arith_parse or tdop
  for row in spec.led_lookup.itervalues():
    mod_name, func_name = row.ModuleAndFuncName()
    to_declare[mod_name].add(('L', func_name))

  # main program has no headers, so here are prototypes
  for mod_name in to_declare:
    print('namespace %s { ' % mod_name)
    for typ, func in sorted(to_declare[mod_name]):
      if typ == 'N':
        # tdop::NullFunc
        fmt = 'arith_expr_t* %s(TdopParser*, word_t*, int);'
      else:
        # tdop::LeftFunc
        fmt = 'arith_expr_t* %s(TdopParser*, word_t*, arith_expr_t*, int);' 
      print(fmt % func)

    print('}')
    print('')

  print("""\
namespace arith_parse {

tdop::LeftInfo kLeftLookup[] = {
  { nullptr, 0, 0 },  // empty
""", end='')

  n = max(spec.led_lookup)
  m = max(spec.nud_lookup)
  assert n == m
  log('arith_parse_gen.py: precedence table has %d entries', n)

  for i in xrange(1, n):
    row = spec.led_lookup.get(i)
    if row is None:
      assert False, 'No empty rows anymore'
      print('  { nullptr, 0, 0 },  // empty')
    else:
      print('  %s' % row)

  print("""\
};

tdop::NullInfo kNullLookup[] = {
  { nullptr, 0 },  // empty
""", end='')

  for i in xrange(1, n):
    row = spec.nud_lookup.get(i)
    if row is None:
      assert False, 'No empty rows anymore'
      print('  { nullptr, 0 },  // empty')
    else:
      print('  %s' % row)

  print("""\
};

};
""")


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
