#!/usr/bin/env python2
"""
arg_gen.py
"""
from __future__ import print_function

import sys

from core.util import log
from frontend import arg_def
from frontend import args
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

  specs = arg_def.All()

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
      if isinstance(spec, args.FlagSpec):
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
""" % spec_name)

        i = 0
        for field_name in sorted(spec.fields):
          subtype = 'Bool'
          subtype_field = 'b'  # e.g. Bool(bool b)
          mypy_type = 'bool'
          tmp = 'val%d' % i
          print('    %s = attrs.attrs[%r]' % (tmp, field_name))
          print('    self.%s = None if %s.tag_() == value_e.Undef else cast(value__%s, %s).%s  # type: %s' % (
            field_name, tmp, subtype, tmp, subtype_field, mypy_type))
          i += 1
        print()

    #
    # I think you can write _Attributes -> arg_types.EXPORT
    # And then change setattr() to a dictionary.
    #
    # arg_types.py
    #
    # class EXPORT_t(object):
    #   pass
    
    # class EXPORT(object):
    #   def Parse(self, arg_r):
    #     # type: (args.Reader) -> EXPORT_t

    # Usage:
    #   arg = EXPORT_SPEC.Parse(arg_r)
    #     problem: can't translate arg_def.py because it has code at the top level?
    #     or maybe you can.
    #   Put it all in _Init like option_def and builtin_def.
    # But those are all serialized.
    # But you run that at every shell startup for now?  And then optimize it?

    # arg = arg_types.export(attrs)

    # Problem: _Action and value_t for default would have to be serializable?
    # This is a use case for 'oheap'.  It's compile-time computation.  I sort of
    # want that.
    # Except _Action an object with polymorphism now.  I think I should change it
    # to use a big switch statement.
    #
    # ASDL type:
    #
    # flag_arg_type = Bool | Int | Float | Str | Enum(string s)
    #
    # SetToArg(string name, flag_arg_type typ, bool quit_parsing)
    #   should this be
    #   Set{Int,Float,Str,Enum}ToArg
    # SetBoolToArg(string name)  # for --verbose=T, OilFlags syntax
    # SetShortOption(string name)
    # SetToTrue(string name)
    # SetOption(string name)
    # SetNamedOption(bool shopt)
    # SetAction(string name)
    # SetNamedAction()

  #def __init__(self):
  #  # type: () -> None
  #  self.arity0 = {}  # type: Dict[str, _Action]  # {'r': _Action} for read -r
  #  self.arity1 = {}  # type: Dict[str, _Action]  # {'t': _Action} for read -t 1.0
  #  self.options = {}  # type: Dict[str, _Action]  # e.g. for declare +r
  #  self.defaults = {}  # type: Dict[str, Any]

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
