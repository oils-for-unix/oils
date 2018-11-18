#!/usr/bin/env python
"""
gen_python.py

Generate Python code from and ASDL schema.

TODO:
- What about Id?  app_types?
"""
from __future__ import print_function

from asdl import visitor


class GenClassesVisitor(visitor.AsdlVisitor):

  def VisitSimpleSum(self, sum, name, depth):
    self.Emit('class %s_e(py_meta.SimpleObj):' % name, depth)
    self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % name, depth)
    self.Emit('', depth)

    # Just use #define, since enums aren't namespaced.
    for i, variant in enumerate(sum.types):
      attr = '%s_e.%s = %s_e(%d, %r)' % (
          name, variant.name, name, i + 1, variant.name)
      self.Emit(attr, depth)
    self.Emit('', depth)

  def _GenClass(self, desc, name, super_name, depth, tag_num=None):
    self.Emit('class %s(%s):' % (name, super_name), depth)

    if tag_num is not None:
      self.Emit('  tag = %d' % tag_num, depth)

    field_names = [f.name for f in desc.fields]

    quoted_fields = repr(tuple(field_names))
    # NOTE: FIELDS is a duplicate of __slots__, used for pretty printing and
    # oheap serialization.  TODO: measure the effect of __slots__, and then get
    # rid of FIELDS?  Or you can just make it an alias.
    # FIELDS = self.__slots__.
    self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % name, depth)
    self.Emit('  __slots__ = %s' % quoted_fields, depth)

    self.Emit('', depth)

    # TODO: leave out spids?  Mark it as an attribute?
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

      # PROBLEM: Optional ints can't be zero!
      # self.span_id = span_id or const.NO_INTEGER
      # I don't want to add if statements checking against None?
      # For now don't use optional ints.  We don't need it.

      default_str = (' or %s' % default) if default else ''
      self.Emit('    self.%s = %s%s' % (f.name, f.name, default_str), depth)

    self.Emit('', depth)

  def VisitConstructor(self, cons, super_name, tag_num, depth):
    if cons.fields:
      self._GenClass(cons, cons.name, super_name, depth, tag_num=tag_num)
    else:
      self.Emit("class %s(%s):" % (cons.name, super_name), depth)
      self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % cons.name, depth)
      self.Emit('  tag = %d'  % tag_num, depth)
      self.Emit('', depth)

  def VisitCompoundSum(self, sum, name, depth):
    # define command_e
    self.Emit('class %s_e(object):' % name, depth)
    for i, variant in enumerate(sum.types):
      self.Emit('  %s = %d' % (variant.name, i + 1), depth)
    self.Emit('', depth)

    # the base class, e.g. 'oil_cmd'
    self.Emit('class %s(py_meta.CompoundObj):' % name, depth)
    self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % name, depth)
    self.Emit('', depth)

    for i, t in enumerate(sum.types):
      tag_num = i + 1
      # name of sum e.g. 'oil_cmd' is the superclass
      self.VisitConstructor(t, name, tag_num, depth)

    # Put everything in a namespace of the base class, so we can instantiate
    # with oil_cmd.Simple()
    for i, t in enumerate(sum.types):
      self.Emit('%s.%s = %s' % (name, t.name, t.name), depth)
    self.Emit('', depth)

  def VisitProduct(self, product, name, depth):
    self._GenClass(product, name, 'py_meta.CompoundObj', depth)

  def EmitFooter(self):
    pass
