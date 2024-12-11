#!/usr/bin/env python2
"""gen_python.py: Generate Python code from an ASDL schema."""
from __future__ import print_function

from collections import defaultdict

from asdl import ast
from asdl import visitor
from asdl.util import log

_ = log  # shut up lint

_PRIMITIVES = {
    'string': 'str',
    'int': 'int',
    'uint16': 'int',
    'BigInt': 'mops.BigInt',
    'float': 'float',
    'bool': 'bool',
    'any': 'Any',
    # TODO: frontend/syntax.asdl should properly import id enum instead of
    # hard-coding it here.
    'id': 'Id_t',
}


def _MyPyType(typ):
    """ASDL type to MyPy Type."""
    if isinstance(typ, ast.ParameterizedType):

        if typ.type_name == 'Dict':
            k_type = _MyPyType(typ.children[0])
            v_type = _MyPyType(typ.children[1])
            return 'Dict[%s, %s]' % (k_type, v_type)

        if typ.type_name == 'List':
            return 'List[%s]' % _MyPyType(typ.children[0])

        if typ.type_name == 'Optional':
            return 'Optional[%s]' % _MyPyType(typ.children[0])

    elif isinstance(typ, ast.NamedType):
        if typ.resolved:
            if isinstance(typ.resolved, ast.Sum):  # includes SimpleSum
                return '%s_t' % typ.name
            if isinstance(typ.resolved, ast.Product):
                return typ.name
            if isinstance(typ.resolved, ast.Use):
                return ast.TypeNameHeuristic(typ.name)
            if isinstance(typ.resolved, ast.Extern):
                r = typ.resolved
                type_name = r.names[-1]
                py_module = r.names[-2]
                return '%s.%s' % (py_module, type_name)

        # 'id' falls through here
        return _PRIMITIVES[typ.name]

    else:
        raise AssertionError()


def _CastedNull(mypy_type):
    # type: (str) -> None
    return "cast('%s', None)" % mypy_type


def _DefaultValue(typ, mypy_type):
    """Values that the static CreateNull() constructor passes.

    mypy_type is used to cast None, to maintain mypy --strict for ASDL.

    We circumvent the type system on CreateNull().  Then the user is
    responsible for filling in all the fields.  If they do so, we can
    rely on it when reading fields at runtime.
    """
    if isinstance(typ, ast.ParameterizedType):
        type_name = typ.type_name

        if type_name == 'Optional':
            return _CastedNull(mypy_type)

        if type_name == 'List':
            return "[] if alloc_lists else cast('%s', None)" % mypy_type

        if type_name == 'Dict':  # TODO: can respect alloc_dicts=True
            return _CastedNull(mypy_type)

        raise AssertionError(type_name)

    if isinstance(typ, ast.NamedType):
        type_name = typ.name

        if type_name == 'id':  # hard-coded HACK
            return '-1'

        if type_name == 'int':
            return '-1'

        if type_name == 'BigInt':
            return 'mops.BigInt(-1)'

        if type_name == 'bool':
            return 'False'

        if type_name == 'float':
            return '0.0'  # or should it be NaN?

        if type_name == 'string':
            return "''"

        if isinstance(typ.resolved, ast.SimpleSum):
            sum_type = typ.resolved
            # Just make it the first variant.  We could define "Undef" for
            # each enum, but it doesn't seem worth it.
            return '%s_e.%s' % (type_name, sum_type.types[0].name)

        # CompoundSum or Product type
        return _CastedNull(mypy_type)

    else:
        raise AssertionError()


def _HNodeExpr(typ, var_name):
    # type: (str, ast.TypeExpr, str) -> str
    none_guard = False

    if typ.IsOptional():
        typ = typ.children[0]  # descend one level

    if isinstance(typ, ast.ParameterizedType):
        code_str = '%s.PrettyTree()' % var_name
        none_guard = True

    elif isinstance(typ, ast.NamedType):
        type_name = typ.name

        if type_name == 'bool':
            code_str = "hnode.Leaf('T' if %s else 'F', color_e.OtherConst)" % var_name

        elif type_name in ('int', 'uint16'):
            code_str = 'hnode.Leaf(str(%s), color_e.OtherConst)' % var_name

        elif type_name == 'BigInt':
            code_str = 'hnode.Leaf(mops.ToStr(%s), color_e.OtherConst)' % var_name

        elif type_name == 'float':
            code_str = 'hnode.Leaf(str(%s), color_e.OtherConst)' % var_name

        elif type_name == 'string':
            code_str = 'NewLeaf(%s, color_e.StringConst)' % var_name

        elif type_name == 'any':
            code_str = 'NewLeaf(str(%s), color_e.External)' % var_name

        elif type_name == 'id':  # was meta.UserType
            # This assumes it's Id, which is a simple SumType.  TODO: Remove this.
            code_str = 'hnode.Leaf(Id_str(%s, dot=False), color_e.UserType)' % var_name

        elif typ.resolved and isinstance(typ.resolved, ast.SimpleSum):
            code_str = 'hnode.Leaf(%s_str(%s), color_e.TypeName)' % (type_name,
                                                                     var_name)

        else:
            code_str = '%s.PrettyTree(do_abbrev, trav=trav)' % var_name
            none_guard = True

    else:
        raise AssertionError()

    return code_str, none_guard


class GenMyPyVisitor(visitor.AsdlVisitor):
    """Generate Python code with MyPy type annotations."""

    def __init__(self,
                 f,
                 abbrev_mod_entries=None,
                 pretty_print_methods=True,
                 py_init_n=False,
                 simple_int_sums=None):

        visitor.AsdlVisitor.__init__(self, f)
        self.abbrev_mod_entries = abbrev_mod_entries or []
        self.pretty_print_methods = pretty_print_methods
        self.py_init_n = py_init_n

        # For Id to use different code gen.  It's used like an integer, not just
        # like an enum.
        self.simple_int_sums = simple_int_sums or []

        self._shared_type_tags = {}
        self._product_counter = 64  # matches asdl/gen_cpp.py

        self._products = []
        self._base_classes = defaultdict(list)

        self._subtypes = []

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
            int_to_str[tag_num] = variant.name
            variants.append((variant, tag_num))

        add_suffix = not ('no_namespace_suffix' in sum.generate)
        gen_integers = 'integers' in sum.generate or 'uint16' in sum.generate

        if gen_integers:
            self.Emit('%s_t = int  # type alias for integer' % sum_name)
            self.Emit('')

            i_name = ('%s_i' % sum_name) if add_suffix else sum_name

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
            e_name = ('%s_e' % sum_name) if add_suffix else sum_name
            self.Emit('class %s(object):' % e_name, depth)

            for variant, tag_num in variants:
                line = '  %s = %s_t(%d)' % (variant.name, sum_name, tag_num)
                self.Emit(line, depth)

        self.Emit('', depth)

        self._EmitDict(sum_name, int_to_str, depth)

        self.Emit('def %s_str(val, dot=True):' % sum_name, depth)
        self.Emit('  # type: (%s_t, bool) -> str' % sum_name, depth)
        self.Emit('  v = _%s_str[val]' % sum_name, depth)
        self.Emit('  if dot:', depth)
        self.Emit('    return "%s.%%s" %% v' % sum_name, depth)
        self.Emit('  else:', depth)
        self.Emit('    return v', depth)
        self.Emit('', depth)

    def _EmitCodeForField(self, field, counter):
        """Generate code that returns an hnode for a field."""
        out_val_name = 'x%d' % counter

        if field.typ.IsList():
            iter_name = 'i%d' % counter

            typ = field.typ
            if typ.type_name == 'Optional':  # descend one level
                typ = typ.children[0]
            item_type = typ.children[0]

            self.Emit('  if self.%s is not None:  # List' % field.name)
            self.Emit('    %s = hnode.Array([])' % out_val_name)
            self.Emit('    for %s in self.%s:' % (iter_name, field.name))
            child_code_str, none_guard = _HNodeExpr(item_type, iter_name)

            if none_guard:  # e.g. for List[Optional[value_t]]
                # TODO: could consolidate with asdl/runtime.py NewLeaf(), which
                # also uses _ to mean None/nullptr
                self.Emit(
                    '      h = (hnode.Leaf("_", color_e.OtherConst) if %s is None else %s)'
                    % (iter_name, child_code_str))
                self.Emit('      %s.children.append(h)' % out_val_name)
            else:
                self.Emit('      %s.children.append(%s)' %
                          (out_val_name, child_code_str))

            self.Emit('    L.append(Field(%r, %s))' %
                      (field.name, out_val_name))

        elif field.typ.IsDict():
            k = 'k%d' % counter
            v = 'v%d' % counter

            typ = field.typ
            if typ.type_name == 'Optional':  # descend one level
                typ = typ.children[0]

            k_typ = typ.children[0]
            v_typ = typ.children[1]

            k_code_str, _ = _HNodeExpr(k_typ, k)
            v_code_str, _ = _HNodeExpr(v_typ, v)

            unnamed = 'unnamed%d' % counter
            self.Emit('  if self.%s is not None:  # Dict' % field.name)
            self.Emit('    %s = []  # type: List[hnode_t]' % unnamed)
            self.Emit('    %s = hnode.Record("", "{", "}", [], %s)' %
                      (out_val_name, unnamed))
            self.Emit('    for %s, %s in self.%s.iteritems():' %
                      (k, v, field.name))
            self.Emit('      %s.append(%s)' % (unnamed, k_code_str))
            self.Emit('      %s.append(%s)' % (unnamed, v_code_str))
            self.Emit('    L.append(Field(%r, %s))' %
                      (field.name, out_val_name))

        elif field.typ.IsOptional():
            typ = field.typ.children[0]

            self.Emit('  if self.%s is not None:  # Optional' % field.name)
            child_code_str, _ = _HNodeExpr(typ, 'self.%s' % field.name)
            self.Emit('    %s = %s' % (out_val_name, child_code_str))
            self.Emit('    L.append(Field(%r, %s))' %
                      (field.name, out_val_name))

        else:
            var_name = 'self.%s' % field.name
            code_str, obj_none_guard = _HNodeExpr(field.typ, var_name)
            depth = self.current_depth
            if obj_none_guard:  # to satisfy MyPy type system
                self.Emit('  assert self.%s is not None' % field.name)
            self.Emit('  %s = %s' % (out_val_name, code_str), depth)

            self.Emit('  L.append(Field(%r, %s))' % (field.name, out_val_name),
                      depth)

    def _GenClassBegin(self, class_name, base_classes, tag_num):
        self.Emit('class %s(%s):' % (class_name, ', '.join(base_classes)))
        self.Emit('  _type_tag = %d' % tag_num)

    def _GenListSubclass(self, class_name, base_classes, tag_num, class_ns=''):
        self._GenClassBegin(class_name, base_classes, tag_num)

        # TODO: Do something nicer
        base_class_str = [b for b in base_classes if b.startswith('List[')][0]

        # Needed for c = CompoundWord() to work
        # TODO: make it
        # c = CompoundWord.New()
        if 0:
            self.Emit('  def __init__(self, other=None):')
            self.Emit('    # type: (Optional[%s]) -> None' % base_class_str,
                      reflow=False)
            self.Emit('    if other is not None:')
            self.Emit('        self.extend(other)')
            self.Emit('')

        # Use our own constructor
        self.Emit('  @staticmethod')
        self.Emit('  def New():')
        self.Emit('    # type: () -> %s' % class_name)
        self.Emit('    return %s()' % class_name)
        self.Emit('')

        self.Emit('  @staticmethod')
        self.Emit('  def Take(plain_list):')
        self.Emit('    # type: (%s) -> %s' % (base_class_str, class_name))
        self.Emit('    result = %s(plain_list)' % class_name)
        self.Emit('    del plain_list[:]')
        self.Emit('    return result')
        self.Emit('')

        if self.pretty_print_methods:
            self._EmitPrettyPrintMethodsForList(class_name)

    def _GenClass(self,
                  fields,
                  class_name,
                  base_classes,
                  tag_num,
                  class_ns=''):
        """Generate a typed Python class.

        Used for both Sum variants ("constructors") and Product types.

        Args:
          class_ns: for variants like value.Str
        """
        self._GenClassBegin(class_name, base_classes, tag_num)

        field_names = [f.name for f in fields]

        quoted_fields = repr(tuple(field_names))
        self.Emit('  __slots__ = %s' % quoted_fields)
        self.Emit('')

        #
        # __init__
        #

        args = [f.name for f in fields]
        arg_types = []
        default_vals = []
        for f in fields:
            mypy_type = _MyPyType(f.typ)
            arg_types.append(mypy_type)

            d_str = _DefaultValue(f.typ, mypy_type)
            default_vals.append(d_str)

        self.Emit('  def __init__(self, %s):' % ', '.join(args))
        self.Emit('    # type: (%s) -> None' % ', '.join(arg_types),
                  reflow=False)

        if not fields:
            self.Emit('    pass')  # for types like NoOp

        for f in fields:
            # don't wrap the type comment
            self.Emit('    self.%s = %s' % (f.name, f.name), reflow=False)

        self.Emit('')

        # CreateNull() - another way of initializing
        if len(fields) and not self.py_init_n:
            self.Emit('  @staticmethod')
            self.Emit('  def CreateNull(alloc_lists=False):')
            self.Emit('    # type: () -> %s%s' % (class_ns, class_name))
            self.Emit('    return %s%s(%s)' %
                      (class_ns, class_name, ', '.join(default_vals)),
                      reflow=False)
            self.Emit('')

        # PrettyTree()
        if self.pretty_print_methods:
            self._EmitPrettyPrintMethods(class_name, class_ns, fields)

    def _EmitPrettyBegin(self):
        self.Emit('  def PrettyTree(self, do_abbrev, trav=None):')
        self.Emit('    # type: (bool, Optional[TraversalState]) -> hnode_t')
        self.Emit('    trav = trav or TraversalState()')
        self.Emit('    heap_id = id(self)')
        self.Emit('    if heap_id in trav.seen:')
        # cut off recursion
        self.Emit('      return hnode.AlreadySeen(heap_id)')
        self.Emit('    trav.seen[heap_id] = True')

    def _EmitPrettyPrintMethodsForList(self, class_name):
        self._EmitPrettyBegin()
        self.Emit('    h = runtime.NewRecord(%r)' % class_name)
        self.Emit(
            '    h.unnamed_fields = [c.PrettyTree(do_abbrev) for c in self]')
        self.Emit('    return h')
        self.Emit('')

    def _EmitPrettyPrintMethods(self, class_name, class_ns, fields):
        if len(fields) == 0:
            # value__Stdin -> value.Stdin (defined at top level)
            pretty_cls_name = class_name.replace('__', '.')
        else:
            # value.Str (defined inside the 'class value') namespace
            pretty_cls_name = '%s%s' % (class_ns, class_name)

        # def PrettyTree(...):

        self._EmitPrettyBegin()
        self.Emit('')

        if class_ns:
            # e.g. _command__Simple
            assert class_ns.endswith('.')
            abbrev_name = '_%s__%s' % (class_ns[:-1], class_name)
        else:
            # e.g. _Token
            abbrev_name = '_%s' % class_name

        if abbrev_name in self.abbrev_mod_entries:
            self.Emit('    if do_abbrev:')
            self.Emit('      p = %s(self)' % abbrev_name)
            self.Emit('      if p:')
            self.Emit('        return p')
            self.Emit('')

        self.Emit('    out_node = NewRecord(%r)' % pretty_cls_name)
        self.Emit('    L = out_node.fields')
        self.Emit('')

        # Use the runtime type to be more like asdl/format.py
        for local_id, field in enumerate(fields):
            #log('%s :: %s', field_name, field_desc)
            self.Indent()
            self._EmitCodeForField(field, local_id)
            self.Dedent()
            self.Emit('')
        self.Emit('    return out_node')
        self.Emit('')

    def VisitCompoundSum(self, sum, sum_name, depth):
        """Note that the following is_simple:

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
                # e.g. DoubleQuoted may have base types expr_t, word_part_t
                base_class = sum_name + '_t'
                bases = self._base_classes[variant.shared_type]
                if base_class in bases:
                    raise RuntimeError(
                        "Two tags in sum %r refer to product type %r" %
                        (sum_name, variant.shared_type))

                else:
                    bases.append(base_class)
            else:
                tag_num = i + 1
            self.Emit('  %s = %d' % (variant.name, tag_num), depth)
            int_to_str[tag_num] = variant.name
        self.Emit('', depth)

        self._EmitDict(sum_name, int_to_str, depth)

        self.Emit('def %s_str(tag, dot=True):' % sum_name, depth)
        self.Emit('  # type: (int, bool) -> str', depth)
        self.Emit('  v = _%s_str[tag]' % sum_name, depth)
        self.Emit('  if dot:', depth)
        self.Emit('    return "%s.%%s" %% v' % sum_name, depth)
        self.Emit('  else:', depth)
        self.Emit('    return v', depth)
        self.Emit('', depth)

        # the base class, e.g. 'oil_cmd'
        self.Emit('class %s_t(pybase.CompoundObj):' % sum_name, depth)
        self.Indent()
        depth = self.current_depth

        # To imitate C++ API
        self.Emit('def tag(self):')
        self.Emit('  # type: () -> int')
        self.Emit('  return self._type_tag')

        self.Dedent()
        depth = self.current_depth

        self.Emit('')

        # Declare any zero argument singleton classes outside of the main
        # "namespace" class.
        for i, variant in enumerate(sum.types):
            if variant.shared_type:
                continue  # Don't generate a class for shared types.
            if len(variant.fields) == 0:
                # We must use the old-style naming here, ie. command__NoOp, in order
                # to support zero field variants as constants.
                class_name = '%s__%s' % (sum_name, variant.name)
                self._GenClass(variant.fields, class_name, (sum_name + '_t', ),
                               i + 1)

        # Class that's just a NAMESPACE, e.g. for value.Str
        self.Emit('class %s(object):' % sum_name, depth)

        self.Indent()

        for i, variant in enumerate(sum.types):
            if variant.shared_type:
                continue

            if len(variant.fields) == 0:
                self.Emit('%s = %s__%s()' %
                          (variant.name, sum_name, variant.name))
                self.Emit('')
            else:
                # Use fully-qualified name, so we can have osh_cmd.Simple and
                # oil_cmd.Simple.
                fq_name = variant.name
                self._GenClass(variant.fields,
                               fq_name, (sum_name + '_t', ),
                               i + 1,
                               class_ns=sum_name + '.')
        self.Emit('  pass', depth)  # in case every variant is first class

        self.Dedent()
        self.Emit('')

    def VisitSubType(self, subtype):
        self._shared_type_tags[subtype.name] = self._product_counter

        # Also create these last. They may inherit from sum types that have yet
        # to be defined.
        self._subtypes.append((subtype, self._product_counter))
        self._product_counter += 1

    def VisitProduct(self, product, name, depth):
        self._shared_type_tags[name] = self._product_counter
        # Create a tuple of _GenClass args to create LAST.  They may inherit from
        # sum types that have yet to be defined.
        self._products.append((product, name, depth, self._product_counter))
        self._product_counter += 1

    def EmitFooter(self):
        # Now generate all the product types we deferred.
        for args in self._products:
            ast_node, name, depth, tag_num = args
            # Figure out base classes AFTERWARD.
            bases = self._base_classes[name]
            if not bases:
                bases = ['pybase.CompoundObj']
            self._GenClass(ast_node.fields, name, bases, tag_num)

        for args in self._subtypes:
            subtype, tag_num = args
            # Figure out base classes AFTERWARD.
            bases = self._base_classes[subtype.name]
            if not bases:
                bases = ['pybase.CompoundObj']

            bases.append(_MyPyType(subtype.base_class))

            if subtype.base_class.IsList():
                self._GenListSubclass(subtype.name, bases, tag_num)
            else:
                self._GenClass([], subtype.name, bases, tag_num)
