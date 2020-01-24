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

  def __init__(self, f, type_lookup, abbrev_mod_entries=None, e_suffix=True,
               pretty_print_methods=True, optional_fields=True,
               simple_int_sums=None):

    visitor.AsdlVisitor.__init__(self, f)
    self.type_lookup = type_lookup
    self.abbrev_mod_entries = abbrev_mod_entries or []
    self.e_suffix = e_suffix
    self.pretty_print_methods = pretty_print_methods
    self.optional_fields = optional_fields
    # For Id to use different code gen.  It's used like an integer, not just
    # like an enum.
    self.simple_int_sums = simple_int_sums or []

    self._shared_type_tags = {}
    self._product_counter = 1000  # start it high

    self._products = []
    self._product_bases = defaultdict(list)

  def _EmitDict(self, name, d, depth):
    self.Emit('_%s_str = {' % name, depth)
    for k in sorted(d):
      self.Emit('%d: %r,' % (k, d[k]), depth + 1)
    self.Emit('}', depth)
    self.Emit('', depth)

  def VisitSimpleSum(self, sum, name, depth):
    int_to_str = {}
    variants = []
    for i, variant in enumerate(sum.types):
      tag_num = i + 1
      tag_str = '%s.%s' % (name, variant.name)
      int_to_str[tag_num] = tag_str
      variants.append((variant, tag_num))

    if name in self.simple_int_sums:
      self.Emit('Id_t = int  # type alias for integer')
      self.Emit('')

      self.Emit('class %s(object):' % name, depth)

      for variant, tag_num in variants:
        line = '  %s = %d' % (variant.name, tag_num)
        self.Emit(line, depth)

    else:
      # First emit a type
      self.Emit('class %s_t(pybase.SimpleObj):' % name, depth)
      self.Emit('  pass', depth)
      self.Emit('', depth)

      # Now emit a namespace
      e_name = ('%s_e' % name) if self.e_suffix else name
      self.Emit('class %s(object):' % e_name, depth)

      for variant, tag_num in variants:
        line = '  %s = %s_t(%d)' % (variant.name, name, tag_num)
        self.Emit(line, depth)

    self.Emit('', depth)

    self._EmitDict(name, int_to_str, depth)

    self.Emit('def %s_str(val):' % name, depth)
    self.Emit('  # type: (%s_t) -> str' % name, depth)
    self.Emit('  return _%s_str[val]' % name, depth)
    self.Emit('', depth)

  def _CodeSnippet(self, abbrev, field, desc, var_name):
    none_guard = False
    if isinstance(desc, meta.BoolType):
      code_str = "hnode.Leaf('T' if %s else 'F', color_e.OtherConst)" % var_name

    elif isinstance(desc, meta.IntType):
      code_str = 'hnode.Leaf(str(%s), color_e.OtherConst)' % var_name

    elif isinstance(desc, meta.StrType):
      code_str = 'NewLeaf(%s, color_e.StringConst)' % var_name

    elif isinstance(desc, meta.AnyType):
      # This is used for value.Obj().
      code_str = 'hnode.External(%s)' % var_name

    elif isinstance(desc, meta.AssocType):
      # Is this valid?
      code_str = 'hnode.External(%s)' % var_name

    elif isinstance(desc, meta.UserType):  # e.g. Id
      # This assumes it's Id, which is a simple SumType.  TODO: Remove this.
      code_str = 'hnode.Leaf(Id_str(%s), color_e.UserType)' % var_name
      none_guard = True  # otherwise MyPy complains about foo.name

    elif isinstance(desc, meta.SumType):
      if desc.is_simple:
        code_str = 'hnode.Leaf(%s_str(%s), color_e.TypeName)' % (
            field.type, var_name)

        none_guard = True  # otherwise MyPy complains about foo.name
      else:
        code_str = '%s.%s()' % (var_name, abbrev)
        none_guard = True

    elif isinstance(desc, meta.CompoundType):
      code_str = '%s.%s()' % (var_name, abbrev)
      none_guard = True

    else:
      raise AssertionError(desc)

    return code_str, none_guard

  def _EmitCodeForField(self, abbrev, field, counter):
    """Generate code that returns an hnode for a field."""
    out_val_name = 'x%d' % counter

    desc = self.type_lookup[field.type]

    if field.seq:
      iter_name = 'i%d' % counter

      self.Emit('  if self.%s:  # ArrayType' % field.name)
      self.Emit('    %s = hnode.Array([])' % out_val_name)
      self.Emit('    for %s in self.%s:' % (iter_name, field.name))
      child_code_str, _ = self._CodeSnippet(abbrev, field, desc, iter_name)
      self.Emit('      %s.children.append(%s)' % (out_val_name, child_code_str))
      self.Emit('    L.append(field(%r, %s))' % (field.name, out_val_name))

    elif field.opt:
      self.Emit('  if self.%s is not None:  # MaybeType' % field.name)
      child_code_str, _ = self._CodeSnippet(abbrev, field, desc,
                                            'self.%s' % field.name)
      self.Emit('    %s = %s' % (out_val_name, child_code_str))
      self.Emit('    L.append(field(%r, %s))' % (field.name, out_val_name))

    else:
      var_name = 'self.%s' % field.name
      code_str, obj_none_guard = self._CodeSnippet(abbrev, field, desc,
                                                   var_name)

      depth = self.current_depth
      if obj_none_guard:  # to satisfy MyPy type system
        self.Emit('  assert self.%s is not None' % field.name)
      self.Emit('  %s = %s' % (out_val_name, code_str), depth)

      self.Emit('  L.append(field(%r, %s))' % (field.name, out_val_name), depth)

  def _GenClass(self, desc, attributes, class_name, base_classes, depth,
                tag_num):
    """Used for Constructor and Product."""
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

    if self.optional_fields:
      args = ['%s=None' % f.name for f in all_fields]
    else:
      args = [f.name for f in all_fields]

    self.Emit('  def __init__(self, %s):' % ', '.join(args))

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

      elif isinstance(field_desc, meta.AssocType):
        type_str = 'Dict[str, str]'

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
        t = 'List[%s]' % type_str
      else:
        t = type_str

      if self.optional_fields:
        t = 'Optional[%s]' % t
      arg_types.append(t)

    self.Emit('    # type: (%s) -> None' % ', '.join(arg_types), reflow=False)

    if not all_fields:
      self.Emit('    pass')  # for types like NoOp

    # TODO: Use the field_desc rather than the parse tree, for consistency.
    for f in all_fields:
      # This logic is like _MakeFieldDescriptors
      default = None
      if f.opt:  # Maybe
        if f.type == 'int':
          default = 'runtime.NO_SPID'
        elif f.type == 'string':
          default = "''"
        else:
          default = 'None'

      elif f.seq:  # Array
        default = '[]'

      # PROBLEM: Optional ints can't be zero!
      # self.span_id = span_id or runtime.NO_SPID
      # I don't want to add if statements checking against None?
      # For now don't use optional ints.  We don't need it.

      default_str = (' or %s' % default) if default else ''
      self.Emit('    self.%s = %s%s' % (f.name, f.name, default_str))

    if not self.pretty_print_methods:
      self.Emit('')
      return

    pretty_cls_name = class_name.replace('__', '.')  # used below

    #
    # PrettyTree
    #

    self.Emit('  def PrettyTree(self):')
    self.Emit('    # type: () -> hnode_t')
    self.Emit('    out_node = NewRecord(%r)' % pretty_cls_name)
    self.Emit('    L = out_node.fields')
    self.Emit('')

    # Use the runtime type to be more like asdl/format.py
    for local_id, field in enumerate(all_fields):
      #log('%s :: %s', field_name, field_desc)
      self.Indent()
      self._EmitCodeForField('PrettyTree', field, local_id)
      self.Dedent()
      self.Emit('')
    self.Emit('    return out_node')
    self.Emit('')

    #
    # _AbbreviatedTree
    #

    self.Emit('  def _AbbreviatedTree(self):')
    self.Emit('    # type: () -> hnode_t')
    self.Emit('    out_node = NewRecord(%r)' % pretty_cls_name)
    self.Emit('    L = out_node.fields')

    # NO attributes in abbreviated version
    for local_id, field in enumerate(desc.fields):
      self.Indent()
      self._EmitCodeForField('AbbreviatedTree', field, local_id)
      self.Dedent()
      self.Emit('')
    self.Emit('    return out_node')
    self.Emit('')

    self.Emit('  def AbbreviatedTree(self):')
    self.Emit('    # type: () -> hnode_t')
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

    int_to_str = {}

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
      tag_str = '%s.%s' % (sum_name, variant.name)
      int_to_str[tag_num] = tag_str
    self.Emit('', depth)

    self._EmitDict(sum_name, int_to_str, depth)

    self.Emit('def %s_str(tag):' % sum_name, depth)
    self.Emit('  # type: (int) -> str', depth)
    self.Emit('  return _%s_str[tag]' % sum_name, depth)
    self.Emit('', depth)

    # the base class, e.g. 'oil_cmd'
    self.Emit('class %s_t(pybase.CompoundObj):' % sum_name, depth)
    self.Indent()
    depth = self.current_depth

    # To imitate C++ API
    self.Emit('def tag_(self):')
    self.Emit('  # type: () -> int')
    self.Emit('  return self.tag')

    # This is what we would do in C++, but we don't need it in Python because
    # every function is virtual.
    if 0:
    #if self.pretty_print_methods:
      for abbrev in 'PrettyTree', '_AbbreviatedTree', 'AbbreviatedTree':
        self.Emit('')
	self.Emit('def %s(self):' % abbrev, depth)
	self.Emit('  # type: () -> hnode_t', depth)
	self.Indent()
	depth = self.current_depth
	self.Emit('UP_self = self', depth)
	self.Emit('', depth)

	for variant in sum.types:
	  if variant.shared_type:
            subtype_name = variant.shared_type
	  else:
	    subtype_name = '%s__%s' % (sum_name, variant.name)

	  self.Emit('if self.tag_() == %s_e.%s:' % (sum_name, variant.name),
		    depth)
	  self.Emit('  self = cast(%s, UP_self)' % subtype_name, depth)
	  self.Emit('  return self.%s()' % abbrev, depth)

	self.Emit('raise AssertionError', depth)

	self.Dedent()
	depth = self.current_depth
    else:
      # Otherwise it's empty
      self.Emit('pass', depth)

    self.Dedent()
    depth = self.current_depth
    self.Emit('')

    for i, variant in enumerate(sum.types):
      if variant.shared_type:
        # Don't generate a class.
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
