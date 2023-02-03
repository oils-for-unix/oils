#!/usr/bin/env python2
"""
gen_python.py: Generate Python code from an ASDL schema.
"""
from __future__ import print_function

from collections import defaultdict

from asdl import ast
from asdl import visitor
from core.pyerror import log

_ = log  # shut up lint


_PRIMITIVES = {
    'string': 'str',
    'int': 'int',
    'float': 'float',
    'bool': 'bool',
    'any': 'Any',
    # TODO: frontend/syntax.asdl should properly import id enum instead of
    # hard-coding it here.
    'id': 'Id_t',
}


def _MyPyType(typ):
  type_name = typ.name

  if type_name == 'map':
    k_type = _MyPyType(typ.children[0])
    v_type = _MyPyType(typ.children[1])
    return 'Dict[%s, %s]' % (k_type, v_type)

  if type_name == 'array':
    return 'List[%s]' % _MyPyType(typ.children[0])

  if type_name == 'maybe':
    # TODO: maybe[int] and maybe[simple_sum] are invalid
    return 'Optional[%s]' % _MyPyType(typ.children[0])

  if typ.resolved:
    if isinstance(typ.resolved, ast.Sum):  # includes SimpleSum
      return '%s_t' % typ.name
    if isinstance(typ.resolved, ast.Product):
      return typ.name
    if isinstance(typ.resolved, ast.Use):
      return ast.TypeNameHeuristic(type_name)

  # 'id' falls through here
  return _PRIMITIVES[type_name]


def _DefaultValue(typ):
  """
  Given an ASDL type, return the default value in Python.

  TODO: Reconcile this with C++.  Many of the commented out values below BREAK
  UNIT AND SPEC TESTS.  The interpreter should be written so that isn't the
  case.
  """
  type_name = typ.name

  default = None

  if type_name == 'map':
    # need this cast for MyPy
    default = "cast('%s', OrderedDict())" % _MyPyType(typ)

  elif type_name == 'array':
    default = '[]'

  elif type_name == 'maybe':
    child_typ = typ.children[0]
    if child_typ.name == 'string':
      default = "''"
    else:
      default = 'None'

  elif type_name == 'int':
    #default = '-1'
    pass

  elif type_name == 'id':  # hard-coded HACK
    #default = '-1'
    pass

  elif type_name == 'bool':
    #default = 'False'
    pass
  elif type_name == 'float':
    #default = '0.0'  # or should it be NaN?
    pass

  elif type_name == 'string':
    #default = "''"
    pass

  elif typ.resolved and isinstance(typ.resolved, ast.SimpleSum):
    sum_type = typ.resolved
    # Just make it the first variant.  We could define "Undef" for
    # each enum, but it doesn't seem worth it.
    default = '%s_e.%s' % (type_name, sum_type.types[0].name)

  return default


def _HNodeExpr(abbrev, typ, var_name):
  # type: (str, ast.TypeExpr, str) -> str
  none_guard = False
  type_name = typ.name

  if type_name == 'bool':
    code_str = "hnode.Leaf('T' if %s else 'F', color_e.OtherConst)" % var_name

  elif type_name == 'int':
    code_str = 'hnode.Leaf(str(%s), color_e.OtherConst)' % var_name

  elif type_name == 'float':
    code_str = 'hnode.Leaf(str(%s), color_e.OtherConst)' % var_name

  elif type_name == 'string':
    code_str = 'NewLeaf(%s, color_e.StringConst)' % var_name

  elif type_name == 'any':  # TODO: Remove this.  Used for value.Obj().
    code_str = 'hnode.External(%s)' % var_name

  elif type_name == 'id':  # was meta.UserType
    # This assumes it's Id, which is a simple SumType.  TODO: Remove this.
    code_str = 'hnode.Leaf(Id_str(%s), color_e.UserType)' % var_name

  elif typ.resolved and isinstance(typ.resolved, ast.SimpleSum):
    code_str = 'hnode.Leaf(%s_str(%s), color_e.TypeName)' % (
        typ.name, var_name)

  else:
    code_str = '%s.%s()' % (var_name, abbrev)
    none_guard = True

  return code_str, none_guard



class GenMyPyVisitor(visitor.AsdlVisitor):
  """Generate Python code with MyPy type annotations."""

  def __init__(self, f, abbrev_mod_entries=None, e_suffix=True,
               pretty_print_methods=True, py_init_required=False,
               simple_int_sums=None):

    visitor.AsdlVisitor.__init__(self, f)
    self.abbrev_mod_entries = abbrev_mod_entries or []
    self.e_suffix = e_suffix
    self.pretty_print_methods = pretty_print_methods
    self.py_init_required = py_init_required
    # For Id to use different code gen.  It's used like an integer, not just
    # like an enum.
    self.simple_int_sums = simple_int_sums or []

    self._shared_type_tags = {}
    self._product_counter = 64  # matches asdl/gen_cpp.py

    self._products = []
    self._product_bases = defaultdict(list)

  def _EmitDict(self, name, d, depth):
    self.Emit('_%s_str = {' % name, depth)
    for k in sorted(d):
      self.Emit('%d: %r,' % (k, d[k]), depth + 1)
    self.Emit('}', depth)
    self.Emit('', depth)

  def VisitSimpleSum(self, sum, sum_name, depth):
    int_to_str = {}
    variants = []
    for i, variant in enumerate(sum.types):
      tag_num = i + 1
      tag_str = '%s.%s' % (sum_name, variant.name)
      int_to_str[tag_num] = tag_str
      variants.append((variant, tag_num))

    if sum_name in self.simple_int_sums:
      self.Emit('%s_t = int  # type alias for integer' % sum_name)
      self.Emit('')

      i_name = ('%s_i' % sum_name) if self.e_suffix else sum_name

      self.Emit('class %s(object):' % i_name, depth)

      for variant, tag_num in variants:
        line = '  %s = %d' % (variant.name, tag_num)
        self.Emit(line, depth)

      # Help in sizing array.  Note that we're 1-based.
      line = '  %s = %d' % ('ARRAY_SIZE', len(variants) + 1)
      self.Emit(line, depth)
     
    else:
      # First emit a type
      self.Emit('class %s_t(pybase.SimpleObj):' % sum_name, depth)
      self.Emit('  pass', depth)
      self.Emit('', depth)

      # Now emit a namespace
      e_name = ('%s_e' % sum_name) if self.e_suffix else sum_name
      self.Emit('class %s(object):' % e_name, depth)

      for variant, tag_num in variants:
        line = '  %s = %s_t(%d)' % (variant.name, sum_name, tag_num)
        self.Emit(line, depth)

    self.Emit('', depth)

    self._EmitDict(sum_name, int_to_str, depth)

    self.Emit('def %s_str(val):' % sum_name, depth)
    self.Emit('  # type: (%s_t) -> str' % sum_name, depth)
    self.Emit('  return _%s_str[val]' % sum_name, depth)
    self.Emit('', depth)

  def _EmitCodeForField(self, abbrev, field, counter):
    """Generate code that returns an hnode for a field."""
    out_val_name = 'x%d' % counter

    if field.IsArray():
      iter_name = 'i%d' % counter
      typ = field.typ.children[0]

      self.Emit('  if self.%s:  # ArrayType' % field.name)
      self.Emit('    %s = hnode.Array([])' % out_val_name)
      self.Emit('    for %s in self.%s:' % (iter_name, field.name))
      child_code_str, _ = _HNodeExpr(abbrev, typ, iter_name)
      self.Emit('      %s.children.append(%s)' % (out_val_name, child_code_str))
      self.Emit('    L.append(field(%r, %s))' % (field.name, out_val_name))

    elif field.IsMaybe():
      typ = field.typ.children[0]

      self.Emit('  if self.%s is not None:  # MaybeType' % field.name)
      child_code_str, _ = _HNodeExpr(abbrev, typ, 'self.%s' % field.name)
      self.Emit('    %s = %s' % (out_val_name, child_code_str))
      self.Emit('    L.append(field(%r, %s))' % (field.name, out_val_name))

    elif field.IsMap():
      k = 'k%d' % counter
      v = 'v%d' % counter

      k_typ = field.typ.children[0]
      v_typ = field.typ.children[1]

      k_code_str, _ = _HNodeExpr(abbrev, k_typ, k)
      v_code_str, _ = _HNodeExpr(abbrev, v_typ, v)

      self.Emit('  if self.%s:  # ArrayType' % field.name)
      self.Emit('    m = hnode.Leaf("map", color_e.OtherConst)')
      self.Emit('    %s = hnode.Array([m])' % out_val_name)
      self.Emit('    for %s, %s in self.%s.iteritems():' % (k, v, field.name))
      self.Emit('      %s.children.append(%s)' % (out_val_name, k_code_str))
      self.Emit('      %s.children.append(%s)' % (out_val_name, v_code_str))
      self.Emit('    L.append(field(%r, %s))' % (field.name, out_val_name))

    else:
      var_name = 'self.%s' % field.name
      code_str, obj_none_guard = _HNodeExpr(abbrev, field.typ, var_name)
      depth = self.current_depth
      if obj_none_guard:  # to satisfy MyPy type system
        self.Emit('  assert self.%s is not None' % field.name)
      self.Emit('  %s = %s' % (out_val_name, code_str), depth)

      self.Emit('  L.append(field(%r, %s))' % (field.name, out_val_name), depth)

  def _GenClass(self, ast_node, attributes, class_name, base_classes, depth,
                tag_num):
    """Used for Constructor and Product."""
    self.Emit('class %s(%s):' % (class_name, ', '.join(base_classes)))
    self.Emit('  _type_tag = %d' % tag_num)

    # Add on attributes
    all_fields = ast_node.fields + attributes

    field_names = [f.name for f in all_fields]

    quoted_fields = repr(tuple(field_names))
    self.Emit('  __slots__ = %s' % quoted_fields)

    self.Emit('')

    #
    # __init__
    #

    if self.py_init_required:
      args = [f.name for f in all_fields]
    else:
      args = ['%s=None' % f.name for f in all_fields]

    self.Emit('  def __init__(self, %s):' % ', '.join(args))

    arg_types = []
    for f in all_fields:
      t = _MyPyType(f.typ)

      if not self.py_init_required and f.typ.name != 'maybe':  # already Optional
        t = 'Optional[%s]' % t
      arg_types.append(t)

    self.Emit('    # type: (%s) -> None' % ', '.join(arg_types), reflow=False)

    if not all_fields:
      self.Emit('    pass')  # for types like NoOp

    # TODO: Use the field_desc rather than the parse tree, for consistency.
    for f in all_fields:
      d_str = _DefaultValue(f.typ)

      # PROBLEM: Optional ints are not supported.  I don't want to add if
      # statements checking against None.  And 0 and -1 are valid values.

      if d_str:
        expr_str = ' if %s is not None else %s' % (f.name, d_str)
        if 'OrderedDict' in d_str:
          # OrderedDict() is not typed
          expr_str += '  # type: ignore'
      else:
        expr_str = ''

      # don't wrap the type comment
      self.Emit('    self.%s = %s%s' % (f.name, f.name, expr_str), reflow=False)

    self.Emit('')
    if not self.pretty_print_methods:
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
    for local_id, field in enumerate(ast_node.fields):
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
    #log('%d variants in %s', len(sum.types), sum_name)

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
    self.Emit('  return self._type_tag')

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
      ast_node, attributes, name, depth, tag_num = args
      # Figure out base classes AFTERWARD.
      bases = self._product_bases[name]
      if not bases:
        bases = ('pybase.CompoundObj',)
      self._GenClass(ast_node, attributes, name, bases, depth, tag_num)
