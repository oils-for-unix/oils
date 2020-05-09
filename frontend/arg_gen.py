#!/usr/bin/env python2
"""
arg_gen.py
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import flag_type_e
from core.util import log
from frontend import arg_def
from mycpp.mylib import tagswitch

#from osh import builtin_assign
#from osh import builtin_bracket
#from osh import builtin_misc
#from osh import builtin_process
#from osh import builtin_printf
#from osh import builtin_pure


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  specs = arg_def.FLAG_SPEC

  if action == 'cpp':
    pass

  elif action == 'mypy':
    print("""
from frontend.args import _Attributes
from _devbuild.gen.runtime_asdl import (
   value_e, value__Bool, value__Int, value__Float, value__Str,
)
from typing import cast
""")
    for spec_name in sorted(specs):
      spec = specs[spec_name]

      log('%s', spec_name)
      #print(dir(spec))
      #print(spec.arity0)
      #print(spec.arity1)
      #print(spec.options)
      # Every flag has a default
      log('%s', spec.fields)

      print("""
class %s(object):
  def __init__(self, attrs):
    # type: (_Attributes) -> None
    flag = attrs.attrs
""" % spec_name)

      i = 0
      for field_name in sorted(spec.fields):
        typ = spec.fields[field_name]

        with tagswitch(typ) as case:
          if case(flag_type_e.Bool):
            subtype = 'Bool'
            subtype_field = 'b'  # e.g. Bool(bool b)
            mypy_type = 'bool'
            print('    self.%s = cast(value__Bool, flag[%r]).b  # type: bool' % (
              field_name, field_name))

          elif case(flag_type_e.Str):
            subtype = 'Str'
            subtype_field = 's'  # e.g. Bool(bool b)
            mypy_type = 'str'

            tmp = 'val%d' % i
            print('    %s = flag[%r]' % (tmp, field_name))
            print('    self.%s = None if %s.tag_() == value_e.Undef else cast(value__%s, %s).%s  # type: %s' % (
              field_name, tmp, subtype, tmp, subtype_field, mypy_type))
          else:
            raise AssertionError(typ)

        i += 1

      print()

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
