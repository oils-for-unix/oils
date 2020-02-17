#!/usr/bin/env python2
"""
option_gen.py
"""
from __future__ import print_function

import sys

from asdl import asdl_
from asdl.visitor import FormatLines
from frontend import builtin_def
from frontend import option_def

_OPT_ENUM = 'option'
_BUILTIN_ENUM = 'builtin'
_SIMPLE = [_OPT_ENUM, _BUILTIN_ENUM]


def _CreateSum(sum_name, variant_names):
  """ 
  Similar to frontend/id_kind_gen.py
  Usage of SYNTHETIC ASDL module:

  C++:

  using option_asdl::opt_num
  opt_num::nounset

  Python:
  from _devbuild.gen.option_asdl import opt_num
  opt_num.nounset
  """
  sum_ = asdl_.Sum([asdl_.Constructor(name) for name in variant_names])
  typ = asdl_.Type(sum_name, sum_)
  return typ


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  # TODO:
  # generate builtin::echo, etc.
  # 
  # And in Python do the same.

  option = _CreateSum(_OPT_ENUM, [opt.name for opt in option_def.All()])
  builtin = _CreateSum(_BUILTIN_ENUM, [b.enum_name for b in builtin_def.All()])
  # TODO: could shrink array later.
  # [opt.name for opt in option_def.All() if opt.implemented])

  schema_ast = asdl_.Module('option', [], [option, builtin])


  if action == 'cpp':
    from asdl import gen_cpp

    out_prefix = argv[2]

    with open(out_prefix + '.h', 'w') as f:
      f.write("""\
#ifndef OPTION_ASDL_H
#define OPTION_ASDL_H

namespace option_asdl {
""")

      # TODO: Could suppress option_str
      v = gen_cpp.ClassDefVisitor(f, {}, simple_int_sums=_SIMPLE)
      v.VisitModule(schema_ast)

      f.write("""
}  // namespace option_asdl

#endif  // OPTION_ASDL_H
""")

    with open(out_prefix + '.cc', 'w') as f:
      f.write("""\
#include <assert.h>
#include "option_asdl.h"

namespace option_asdl {

""")

      v = gen_cpp.MethodDefVisitor(f, {}, simple_int_sums=_SIMPLE)

      v.VisitModule(schema_ast)

      f.write('}  // namespace option_asdl\n')

  elif action == 'mypy':
    from asdl import gen_python

    f = sys.stdout

    f.write("""\
from asdl import pybase

""")
    # option_i type
    v = gen_python.GenMyPyVisitor(f, None, simple_int_sums=_SIMPLE)
    v.VisitModule(schema_ast)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
