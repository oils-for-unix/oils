#!/usr/bin/env python
"""
gen_python.py

Generate Python code from and ASDL schema.

TODO:
- What about Id?  app_types?
"""
from __future__ import print_function

from asdl import visitor
from asdl import runtime
#from core.util import log


class GenClassesVisitor(visitor.AsdlVisitor):

  def VisitSimpleSum(self, sum, name, depth):
    self.Emit('class %s_e(runtime.SimpleObj):' % name, depth)
    self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % name, depth)
    self.Emit('', depth)

    # Just use #define, since enums aren't namespaced.
    for i, variant in enumerate(sum.types):
      attr = '%s_e.%s = %s_e(%d, %r)' % (
          name, variant.name, name, i + 1, variant.name)
      self.Emit(attr, depth)
    self.Emit('', depth)

  def _GenClass(self, desc, name, super_name, depth, tag_num=None):
    """Used for Constructor and Product."""
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

  def VisitConstructor(self, cons, sum_name, tag_num, depth):
    # Use fully-qualified name, so we can have osh_cmd.Simple and
    # oil_cmd.Simple.
    fq_name = '%s__%s' % (sum_name, cons.name)
    if cons.fields:
      self._GenClass(cons, fq_name, sum_name, depth, tag_num=tag_num)
    else:
      # No fields
      self.Emit('class %s(%s):' % (fq_name, sum_name), depth)
      self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % fq_name, depth)
      self.Emit('  tag = %d'  % tag_num, depth)
      self.Emit('', depth)

  def VisitCompoundSum(self, sum, sum_name, depth):
    # define command_e
    self.Emit('class %s_e(object):' % sum_name, depth)
    for i, variant in enumerate(sum.types):
      self.Emit('  %s = %d' % (variant.name, i + 1), depth)
    self.Emit('', depth)

    # the base class, e.g. 'oil_cmd'
    self.Emit('class %s(runtime.CompoundObj):' % sum_name, depth)
    self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % sum_name, depth)
    self.Emit('', depth)

    for i, t in enumerate(sum.types):
      tag_num = i + 1
      # e.g. 'oil_cmd' is the superclass
      self.VisitConstructor(t, sum_name, tag_num, depth)

    # Put everything in a namespace of the base class, so we can instantiate
    # with oil_cmd.Simple()
    for i, t in enumerate(sum.types):
      # e.g. op_id.Plus = op_id__Plus.
      fq_name = '%s__%s' % (sum_name, t.name)
      self.Emit('%s.%s = %s' % (sum_name, t.name, fq_name), depth)
    self.Emit('', depth)

  def VisitProduct(self, product, name, depth):
    self._GenClass(product, name, 'runtime.CompoundObj', depth)

  def EmitFooter(self):
    pass


class GenMyPyVisitor(visitor.AsdlVisitor):
  """Generate code with MyPy type annotations.

  TODO: Remove the code above.  This should substitute for it.
  """
  def __init__(self, f):
    visitor.AsdlVisitor.__init__(self, f)
    self.type_lookup = None

  def VisitSimpleSum(self, sum, name, depth):
    # First emit a type
    self.Emit('class %s_t(runtime.SimpleObj):' % name, depth)
    self.Emit('  pass', depth)
    self.Emit('', depth)

    # Now emit a namespace
    self.Emit('class %s_e(object):' % name, depth)
    for i, variant in enumerate(sum.types):
      attr = '  %s = %s_t(%d, %r)' % (
          variant.name, name, i + 1, variant.name)
      self.Emit(attr, depth)
    self.Emit('', depth)

  def _GenClass(self, desc, name, super_name, depth, tag_num=None):
    """Used for Constructor and Product."""
    self.Emit('class %s(%s):' % (name, super_name), depth)

    if tag_num is not None:
      self.Emit('  tag = %d' % tag_num, depth)

    field_names = [f.name for f in desc.fields]

    quoted_fields = repr(tuple(field_names))
    # NOTE: FIELDS is a duplicate of __slots__, used for pretty printing and
    # oheap serialization.  TODO: measure the effect of __slots__, and then get
    # rid of FIELDS?  Or you can just make it an alias.
    # FIELDS = self.__slots__.
    #self.Emit('  ASDL_TYPE = TYPE_LOOKUP[%r]' % name, depth)
    self.Emit('  __slots__ = %s' % quoted_fields, depth)

    self.Emit('', depth)

    # TODO: leave out spids?  Mark it as an attribute?
    args = ', '.join('%s=None' % f.name for f in desc.fields)
    self.Emit('  def __init__(self, %s):' % args, depth)

    # defaults:
    # int is 0 like C++?
    # str is ''?
    # There is no such thing as unset?
    # No I guess you can have nullptr for unset.  But not for ints.

    #for name, val in self.type_lookup.iteritems():
    #  log('%s %s', name, val)

    arg_types = []
    for f in desc.fields:
      # TODO: handle more types

      #log('field %s :: %s', f.name, f.type)

      # op_id -> op_id_t, bool_expr -> bool_expr_t, etc.
      field_desc = self.type_lookup.get(f.type)

      if f.type == 'string':
        type_str = 'str'

      # note: product type doesn't have _t suffix
      elif isinstance(field_desc, runtime.SumType):
        type_str = '%s_t' % f.type

      else:
        type_str = f.type

      if f.seq:
        # We set the default value to None because we don't want a mutable
        # default.  TODO: get rid of this?
        t = 'Optional[List[%s]]' % type_str
        arg_types.append(t)
      else:
        # We allow initializing, so we need None.
        # TODO: Change this?  I think it would make sense.  We can always use
        # locals to initialize.
        arg_types.append('Optional[%s]' % type_str)

    self.Emit('    # type: (%s) -> None' % ', '.join(arg_types),
              depth, reflow=False)

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

  def VisitConstructor(self, cons, sum_name, tag_num, depth):
    # Use fully-qualified name, so we can have osh_cmd.Simple and
    # oil_cmd.Simple.
    fq_name = '%s__%s' % (sum_name, cons.name)
    if cons.fields:
      self._GenClass(cons, fq_name, sum_name + '_t', depth, tag_num=tag_num)
    else:
      # No fields
      self.Emit('class %s(%s_t):' % (fq_name, sum_name), depth)
      self.Emit('  tag = %d'  % tag_num, depth)
      self.Emit('', depth)

  def VisitCompoundSum(self, sum, sum_name, depth):
    # Three types:
    #
    # 1. enum for tag (cflow_e)
    # 2. base class for inheritance (cflow_t)
    # 3. namespace for classes (cflow)
    #
    # Should code use cflow_e.tag or isinstance()?
    # isinstance() is better for MyPy I think.  But tag is better for C++.
    # int tag = static_cast<cflow>(node).tag;

    # enum for the tag
    self.Emit('class %s_e(object):' % sum_name, depth)
    for i, variant in enumerate(sum.types):
      self.Emit('  %s = %d' % (variant.name, i + 1), depth)
    self.Emit('', depth)

    # the base class, e.g. 'oil_cmd'
    self.Emit('class %s_t(runtime.CompoundObj):' % sum_name, depth)
    self.Emit('  pass', depth)
    self.Emit('', depth)

    for i, t in enumerate(sum.types):
      tag_num = i + 1
      # e.g. 'oil_cmd' is the superclass
      self.VisitConstructor(t, sum_name, tag_num, depth)

    # Emit a namespace
    self.Emit('class %s(object):' % sum_name, depth)
    # Put everything in a namespace of the base class, so we can instantiate
    # with oil_cmd.Simple()
    for i, t in enumerate(sum.types):
      # e.g. op_id.Plus = op_id__Plus.
      fq_name = '%s__%s' % (sum_name, t.name)
      self.Emit('  %s = %s' % (t.name, fq_name), depth)
    self.Emit('', depth)

  def VisitProduct(self, product, name, depth):
    self._GenClass(product, name, 'runtime.CompoundObj', depth)

  def EmitFooter(self):
    pass

  def VisitModule(self, mod, type_lookup):
    """Overrides method on base class."""
    self.type_lookup = type_lookup
    for dfn in mod.dfns:
      self.VisitType(dfn)
    self.EmitFooter()
