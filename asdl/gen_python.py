#!/usr/bin/env python2
"""
gen_python.py: Generate Python code from an ASDL schema.
"""
from __future__ import print_function

from collections import defaultdict

from asdl import meta
from asdl import visitor
from core.util import log

_ = log  # shut up lint


class GenMyPyVisitor(visitor.AsdlVisitor):
  """Generate Python code with MyPy type annotations."""

  def __init__(self, f, type_lookup, abbrev_mod_entries=None, e_suffix=True):
    visitor.AsdlVisitor.__init__(self, f)
    self.type_lookup = type_lookup
    self.abbrev_mod_entries = abbrev_mod_entries or []
    self.e_suffix = e_suffix

    self._shared_type_tags = {}
    self._product_counter = 1000  # start it high

    self._products = []
    self._product_bases = defaultdict(list)

  def VisitSimpleSum(self, sum, name, depth):
    # First emit a type
    self.Emit('class %s_t(pybase.SimpleObj):' % name, depth)
    self.Emit('  pass', depth)
    self.Emit('', depth)

    # Now emit a namespace
    e_name = ('%s_e' % name) if self.e_suffix else name
    self.Emit('class %s(object):' % e_name, depth)
    for i, variant in enumerate(sum.types):
      attr = '  %s = %s_t(%d, %r)' % (
          variant.name, name, i + 1, variant.name)
      self.Emit(attr, depth)
    self.Emit('', depth)

  def _CodeSnippet(self, method_name, var_name, desc):
    none_guard = False
    if isinstance(desc, meta.BoolType):
      code_str = "PrettyLeaf('T' if %s else 'F', Color_OtherConst)" % var_name

    elif isinstance(desc, meta.IntType):
      code_str = 'PrettyLeaf(str(%s), Color_OtherConst)' % var_name

    elif isinstance(desc, meta.StrType):
      code_str = 'PrettyLeaf(%s, Color_StringConst)' % var_name

    elif isinstance(desc, meta.AnyType):
      # This is used for value.Obj().
      code_str = 'ExternalLeaf(%s)' % var_name

    # TODO: Is this unused?  Delete it?
    elif isinstance(desc, meta.UserType):  # e.g. Id
      # This assumes it's Id, which is a simple SumType.  TODO: Remove this.
      code_str = 'PrettyLeaf(%s.name, Color_UserType)' % var_name
      none_guard = True  # otherwise MyPy complains about foo.name

    elif isinstance(desc, meta.SumType):
      if desc.is_simple:
        code_str = 'PrettyLeaf(%s.name, Color_TypeName)' % var_name
        none_guard = True  # otherwise MyPy complains about foo.name
      else:
        code_str = '%s.%s()' % (var_name, method_name)
        none_guard = True

    elif isinstance(desc, meta.CompoundType):
      code_str = '%s.%s()' % (var_name, method_name)
      none_guard = True

    else:
      raise AssertionError(desc)

    return code_str, none_guard

  def _EmitCodeForField(self, method_name, field_name, desc, counter):
    """Given a field value and type descriptor, return a PrettyNode."""
    out_val_name = 'x%d' % counter

    if isinstance(desc, meta.ArrayType):
      iter_name = 'i%d' % counter

      self.Emit('  if self.%s:  # ArrayType' % field_name)
      self.Emit('    %s = PrettyArray()' % out_val_name)
      self.Emit('    for %s in self.%s:' % (iter_name, field_name))
      child_code_str, _ = self._CodeSnippet(method_name, iter_name, desc.desc)
      self.Emit('      %s.children.append(%s)' % (out_val_name, child_code_str))
      self.Emit('    L.append((%r, %s))' % (field_name, out_val_name))

    elif isinstance(desc, meta.MaybeType):
      self.Emit('  if self.%s is not None:  # MaybeType' % field_name)
      child_code_str, _ = self._CodeSnippet(method_name,
                                            'self.%s' % field_name, desc.desc)
      self.Emit('    %s = %s' % (out_val_name, child_code_str))
      self.Emit('    L.append((%r, %s))' % (field_name, out_val_name))

    else:
      var_name = 'self.%s' % field_name
      code_str, obj_none_guard = self._CodeSnippet(method_name, var_name, desc)

      depth = self.current_depth
      if obj_none_guard:  # to satisfy MyPy type system
        self.Emit('  assert self.%s is not None' % field_name)
      self.Emit('  %s = %s' % (out_val_name, code_str), depth)

      self.Emit('  L.append((%r, %s))' % (field_name, out_val_name), depth)

  def _GenClass(self, desc, attributes, class_name, base_classes, depth,
                tag_num):
    """Used for Constructor and Product."""
    pretty_cls_name = class_name.replace('__', '.')  # used below
    self.Emit('class %s(%s):' % (class_name, ', '.join(base_classes)))
    self.Emit('  tag = %d' % tag_num)

    # Add on attributes
    all_fields = desc.fields + attributes

    field_names = [f.name for f in all_fields]

    quoted_fields = repr(tuple(field_names))
    self.Emit('  __slots__ = %s' % quoted_fields)

    self.Emit('')

    #
    # __init__
    #

    args = ', '.join('%s=None' % f.name for f in all_fields)
    self.Emit('  def __init__(self, %s):' % args)

    arg_types = []
    for f in all_fields:
      field_desc = self.type_lookup.get(f.type)

      # op_id -> op_id_t, bool_expr -> bool_expr_t, etc.
      # NOTE: product type doesn't have _t suffix
      if isinstance(field_desc, meta.SumType):
        type_str = '%s_t' % f.type

      elif isinstance(field_desc, meta.StrType):
        type_str = 'str'

      elif isinstance(field_desc, meta.AnyType):
        type_str = 'Any'

      elif isinstance(field_desc, meta.UserType):
        type_str = field_desc.type_name

      else:
        type_str = f.type

      # We allow partially initializing, so both of these are Optional.
      # TODO: Change this?  I think it would make sense.  We can always use
      # locals to initialize.
      # NOTE: It's complicated in the List[] case, because we don't want a
      # mutable default arg?  That is a Python pitfall
      if f.seq:
        t = 'Optional[List[%s]]' % type_str
        arg_types.append(t)
      else:
        arg_types.append('Optional[%s]' % type_str)

    self.Emit('    # type: (%s) -> None' % ', '.join(arg_types), reflow=False)

    if not all_fields:
      self.Emit('    pass')  # for types like NoOp

    # TODO: Use the field_desc rather than the parse tree, for consistency.
    for f in all_fields:
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
      self.Emit('    self.%s = %s%s' % (f.name, f.name, default_str))

    self.Emit('')

    #
    # PrettyTree
    #

    self.Emit('  def PrettyTree(self):')
    self.Emit('    # type: () -> PrettyNode')
    self.Emit('    out_node = PrettyNode(%r)' % pretty_cls_name)
    self.Emit('    L = out_node.fields')
    self.Emit('')

    # Use the runtime type to be more like asdl/format.py
    desc = self.type_lookup[class_name]
    for i, (field_name, field_desc) in enumerate(desc.GetFields()):
      #log('%s :: %s', field_name, field_desc)
      self.Indent()
      self._EmitCodeForField('PrettyTree', field_name, field_desc, i)
      self.Dedent()
      self.Emit('')

    self.Emit('    return out_node')
    self.Emit('')

    #
    # AbbreviatedTree
    #

    self.Emit('  def _AbbreviatedTree(self):')
    self.Emit('    # type: () -> PrettyNode')
    self.Emit('    out_node = PrettyNode(%r)' % pretty_cls_name)
    self.Emit('    L = out_node.fields')
    for i, (field_name, field_desc) in enumerate(desc.GetFields()):
      if field_name == 'spids':
        continue  # don't emit in the abbreviated version

      self.Indent()
      self._EmitCodeForField('AbbreviatedTree', field_name, field_desc, i)
      self.Dedent()
      self.Emit('')
    self.Emit('    return out_node')

    self.Emit('')

    self.Emit('  def AbbreviatedTree(self):')
    self.Emit('    # type: () -> PrettyNode')
    abbrev_name = '_%s' % class_name
    if abbrev_name in self.abbrev_mod_entries:
      self.Emit('    p = %s(self)' % abbrev_name)
      # If the user function didn't return anything, fall back.
      self.Emit('    return p if p else self._AbbreviatedTree()')
    else:
      self.Emit('    return self._AbbreviatedTree()')
    self.Emit('')

  def VisitCompoundSum(self, sum, sum_name, depth):
    """
    Note that the following is_simple:

      cflow = Break | Continue

    But this is compound:

      cflow = Break | Continue | Return(int val)

    The generated code changes depending on which one it is.
    """
    # We emit THREE Python types for each meta.CompoundType:
    #
    # 1. enum for tag (cflow_e)
    # 2. base class for inheritance (cflow_t)
    # 3. namespace for classes (cflow)  -- TODO: Get rid of this one.
    #
    # Should code use cflow_e.tag or isinstance()?
    # isinstance() is better for MyPy I think.  But tag is better for C++.
    # int tag = static_cast<cflow>(node).tag;

    # enum for the tag
    self.Emit('class %s_e(object):' % sum_name, depth)
    for i, variant in enumerate(sum.types):
      if variant.shared_type:
        tag_num = self._shared_type_tags[variant.shared_type]
        # e.g. double_quoted may have base types expr_t, word_part_t
        base_class = sum_name + '_t'
        bases = self._product_bases[variant.shared_type]
        if base_class in bases:
          raise RuntimeError(
              "Two tags in sum %r refer to product type %r" %
              (sum_name, variant.shared_type))

        else:
          bases.append(base_class)
      else:
        tag_num = i + 1
      self.Emit('  %s = %d' % (variant.name, tag_num), depth)
    self.Emit('', depth)

    # the base class, e.g. 'oil_cmd'
    self.Emit('class %s_t(pybase.CompoundObj):' % sum_name, depth)
    self.Emit('  pass', depth)
    self.Emit('', depth)

    for i, variant in enumerate(sum.types):
      if variant.shared_type:
        # Do not generated a class.
        pass
      else:
        # Use fully-qualified name, so we can have osh_cmd.Simple and
        # oil_cmd.Simple.
        fq_name = '%s__%s' % (sum_name, variant.name)
        self._GenClass(variant, sum.attributes, fq_name, (sum_name + '_t',),
                       depth, i+1)

    # Emit a namespace
    self.Emit('class %s(object):' % sum_name, depth)
    # Put everything in a namespace of the base class, so we can instantiate
    # with oil_cmd.Simple()
    for i, variant in enumerate(sum.types):
      if variant.shared_type:
        # No class for this namespace
        pass
      else:
        # e.g. op_id.Plus = op_id__Plus.
        fq_name = '%s__%s' % (sum_name, variant.name)
        self.Emit('  %s = %s' % (variant.name, fq_name), depth)
    self.Emit('', depth)

  def VisitProduct(self, product, name, depth):
    self._shared_type_tags[name] = self._product_counter
    # Create a tuple of _GenClass args to create LAST.  They may inherit from
    # sum types that have yet to be defined.
    self._products.append(
        (product, product.attributes, name, depth, self._product_counter)
    )
    self._product_counter += 1

  def EmitFooter(self):
    # Now generate all the product types we deferred.
    for args in self._products:
      desc, attributes, name, depth, tag_num = args
      # Figure out base classes AFTERWARD.
      bases = self._product_bases[name]
      if not bases:
        bases = ('pybase.CompoundObj',)
      self._GenClass(desc, attributes, name, bases, depth, tag_num)
