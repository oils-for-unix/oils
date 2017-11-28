#!/usr/bin/python
"""
gen_python.py
"""

import sys

from asdl import gen_cpp
from asdl import asdl_ as asdl


class GenClassesVisitor(gen_cpp.AsdlVisitor):
  # TODO:
  # - __eq__ isn't the same
  # - DESCRIPTOR  and FIELDS are dummies right now.
  # - I think FIELDS is used for encoding.
  #
  # - Debug mode:
  #   - _CheckType(value, desc) on initialization and __setattr__.
  #   - check unassigned.  Why is it done with unit tests with CheckUnassigned,
  #     but also in _Init?

  def VisitSimpleSum(self, sum, name, depth):
    self.Emit('class %s_e(asdl_base.SimpleObj):' % name, depth)
    self.Emit('  pass', depth)
    self.Emit('', depth)

    # Just use #define, since enums aren't namespaced.
    for i, variant in enumerate(sum.types):
      attr = '%s_e.%s = %s_e(%d, %r)' % (
          name, variant.name, name, i + 1, variant.name)
      self.Emit(attr, depth)
    self.Emit('', depth)

  def _GenClass(self, desc, name, super_name, depth, tag_num=None,
                add_spids=True):
    self.Emit('class %s(%s):' % (name, super_name), depth)

    if tag_num is not None:
      self.Emit('  tag = %d' % tag_num, depth)

    field_names = [f.name for f in desc.fields]
    if add_spids:
      field_names.append('spids')

    quoted_fields = repr(tuple(field_names))
    # NOTE: FIELDS is a duplicate of __slots__, used for pretty printing and
    # oheap serialization.  TODO: measure the effect of __slots__, and then get
    # rid of FIELDS?  Or you can just make it an alias.
    # FIELDS = self.__slots__.
    self.Emit('  FIELDS = %s' % quoted_fields, depth)

    self.Emit('  __slots__ = %s' % quoted_fields, depth)

    # TODO: 
    # py_meta.MakeTypes and py_meta._MakeFieldDescriptors fill
    # DESCRIPTOR_LOOKUP, which is used for pretty printing.
    lookup = {}
    self.Emit('  DESCRIPTOR_LOOKUP = %r' % lookup, depth)
    self.Emit('', depth)

    args = ', '.join('%s=None' % f.name for f in desc.fields)
    self.Emit('  def __init__(self, %s):' % args, depth)

    for f in desc.fields:
      # This logic is like _MakeFieldDescriptors
      default = None
      if f.opt:  # Maybe
        if f.type == 'int':
          default = 'const.NO_INTEGER'
        elif f.type == 'string':
          default = "''"
        else:
          default = 'None'

      elif f.seq:  # Array
        default = '[]'

      default_str = (' or %s' % default) if default else ''
      self.Emit('    self.%s = %s%s' % (f.name, f.name, default_str), depth)

    # Like add_spids in _MakeFieldDescriptors.  TODO: This should be optional
    # for token and span!  Also for runtime.asdl.  We need to make it optional.
    if add_spids:
      self.Emit('    self.spids = []', depth)

    self.Emit('', depth)

    self.Emit('  def CheckUnassigned(self):', depth)
    self.Emit('    pass', depth)
    self.Emit('', depth)

  def VisitConstructor(self, cons, def_name, tag_num, depth):
    if cons.fields:
      self._GenClass(cons, cons.name, def_name, depth, tag_num=tag_num)
    else:
      self.Emit("class %s(%s):" % (cons.name, def_name), depth)
      self.Emit('  tag = %d'  % tag_num, depth)
      self.Emit('', depth)

  def VisitCompoundSum(self, sum, name, depth):
    # define command_e
    self.Emit('class %s_e(object):' % name, depth)
    for i, variant in enumerate(sum.types):
      self.Emit('  %s = %d' % (variant.name, i + 1), depth)
    self.Emit('', depth)

    self.Emit('class %s(asdl_base.CompoundObj):' % name, depth)
    self.Emit('  pass', depth)
    self.Emit('', depth)

    # define command_t, and then make subclasses
    super_name = '%s' % name
    for i, t in enumerate(sum.types):
      tag_num = i + 1
      self.VisitConstructor(t, super_name, tag_num, depth)

  def VisitProduct(self, product, name, depth):
    self._GenClass(product, name, 'asdl_base.CompoundObj', depth)

  def EmitFooter(self):
    pass


def main(argv):

  schema_path = argv[1]
  with open(schema_path) as input_f:
    module = asdl.parse(input_f)

  f = sys.stdout

  f.write("""\
from asdl import const  # For const.NO_INTEGER
from asdl import asdl_base
""")

  v = GenClassesVisitor(f)
  v.VisitModule(module)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
