"""
gen_cpp.py - Generate C++ classes from an ASDL schema.

TODO:

- Integrate some of the lessons here:  
  - https://github.com/oilshell/blog-code/tree/master/asdl
  - And maybe mycpp/target_lang.cc

- pretty printing methods
  - so asdl/format.py get translated?

- ASDL optional args to C++ default arguments?
- what about spids?  optional?
  - TODO: test this out in target_lang.cc

- NoOp needs to be instantiated without args?
- dict becomes Dict[str, str] ?
- how to handle UserType(id) ?

- How do optional ASDL values like int? work?  Use C++ default values?
  - This means that all the optionals have to be on the end.  That seems OK.
  - I guess that's how Python does it.
"""
from __future__ import print_function

import sys

from asdl import meta
from asdl import visitor


# Used by core/asdl_gen.py to generate _devbuild/gen/osh-types.h, with
# lex_mode__*
class CEnumVisitor(visitor.AsdlVisitor):

  def VisitSimpleSum(self, sum, name, depth):
    # Just use #define, since enums aren't namespaced.
    for i, variant in enumerate(sum.types):
      self.Emit('#define %s__%s %d' % (name, variant.name, i + 1), depth)
    self.Emit("", depth)


_BUILTINS = {
    'string': 'Str*',  # declared in mylib.h
    'int': 'int',
    'bool': 'bool',
    'any': 'void*',
    # TODO: frontend/syntax.asdl should properly import id enum instead of
    # hard-coding it here.
    'id': 'Id_t',
}


class ForwardDeclareVisitor(visitor.AsdlVisitor):
  """Print forward declarations.

  ASDL allows forward references of types, but C++ doesn't.
  """
  def VisitCompoundSum(self, sum, name, depth):
    self.Emit("class %(name)s_t;" % locals(), depth)

  def VisitProduct(self, product, name, depth):
    self.Emit("class %(name)s;" % locals(), depth)

  def EmitFooter(self):
    self.Emit("", 0)  # blank line


class ClassDefVisitor(visitor.AsdlVisitor):
  """Generate C++ classes and type-safe enums."""

  def __init__(self, f, type_lookup, e_suffix=True, pretty_print_methods=True):
    visitor.AsdlVisitor.__init__(self, f)
    self.type_lookup = type_lookup
    self.e_suffix = e_suffix
    self.pretty_print_methods = pretty_print_methods

  def _GetInnerCppType(self, field):
    type_name = field.type

    cpp_type = _BUILTINS.get(type_name)
    if cpp_type is not None:
      return cpp_type

    typ = self.type_lookup[type_name]
    if isinstance(typ, meta.SumType):
      if typ.is_simple:
        # Use the enum instead of the class.
        return "%s_e" % type_name
      else:
        # Everything is a pointer for now.  No references.
        return "%s_t*" % type_name

    return '%s*' % type_name

  def _GetCppType(self, field):
    """Return a string for the C++ name of the type."""

    # TODO: The once instance of 'dict' needs an overhaul!
    # Right now it's untyped in ASDL.
    # I guess is should be Dict[str, str] for the associative array contents?
    c_type = self._GetInnerCppType(field)
    if field.seq:
      return 'List<%s>*' % c_type
    else:
      return c_type

  def _EmitEnum(self, sum, sum_name, depth):
    enum = []
    int_to_str = {}
    for i in xrange(len(sum.types)):
      variant = sum.types[i]
      tag_num = i + 1
      enum.append("%s = %d" % (variant.name, tag_num))  # zero is reserved
      int_to_str[tag_num] = variant.name

    enum_name = '%s_e' % sum_name if self.e_suffix else sum_name
    self.Emit('enum class %s {' % enum_name, depth)
    self.Emit(', '.join(enum), depth + 1)
    self.Emit('};', depth)
    self.Emit('', depth)

    self.Emit('const char* %s_str(%s tag) {' % (sum_name, enum_name), depth)
    self.Emit('  switch (tag) {', depth)
    for variant in sum.types:
      self.Emit('case %s::%s:' % (enum_name, variant.name), depth + 1)
      self.Emit('  return "%s.%s";' % (sum_name, variant.name), depth + 1)
    self.Emit('  }', depth)
    self.Emit('}', depth)
    self.Emit('', depth)

  def VisitSimpleSum(self, sum, name, depth):
    self._EmitEnum(sum, name, depth)
    # type alias to match Python code
    enum_name = '%s_e' % name if self.e_suffix else name
    self.Emit('typedef %s %s_t;' % (enum_name, name), depth)

  def VisitCompoundSum(self, sum, sum_name, depth):
    # This is a sign that Python needs string interpolation!!!
    def Emit(s, depth=depth):
      self.Emit(s % sys._getframe(1).f_locals, depth)

    self._EmitEnum(sum, sum_name, depth)

    # TODO: DISALLOW_COPY_AND_ASSIGN on this class and others?

    # This is the base class.
    Emit("class %(sum_name)s_t {")
    Emit(" public:")
    Emit("  %s_t(%s_e tag) : tag(tag) {" % (sum_name, sum_name))
    Emit("  }")
    Emit("  %s_e tag;" % sum_name)
    # TODO: This should be a free function.
    if self.pretty_print_methods:
      self.Emit("  hnode_t* AbbreviatedTree() {")
      self.Emit("    return new hnode__External(nullptr);")
      self.Emit("  }")

    Emit("};")
    Emit("")

    for variant in sum.types:
      if variant.shared_type:
        # Do not generated a class.
        pass
      else:
        super_name = '%s_t' % sum_name
        if variant.fields:
          tag = '%s_e::%s' % (sum_name, variant.name)
          class_name = '%s__%s' % (sum_name, variant.name)
          self._GenClass(variant, sum.attributes, class_name, super_name, depth,
                         tag=tag)

  def _GenClass(self, desc, attributes, class_name, super_name, depth,
                tag=None):
    """For Product and Constructor."""
    if super_name:
      self.Emit("class %s : public %s {" % (class_name, super_name), depth)
    else:
      self.Emit("class %s {" % class_name, depth)
    self.Emit(" public:", depth)

    params = []
    inits = []

    if tag:
      inits.append('%s(%s)' % (super_name, tag))
    for f in desc.fields:
      params.append('%s %s' % (self._GetCppType(f), f.name))
      inits.append('%s(%s)' % (f.name, f.name))

    # Constructor
    self.Emit("  %s(%s) : %s {" %
        (class_name, ', '.join(params), ', '.join(inits)), depth)
    self.Emit("  }")

    all_fields = desc.fields + attributes
    for f in all_fields:
      self.Emit("  %s %s;" % (self._GetCppType(f), f.name))
    self.Emit("};", depth)
    self.Emit("", depth)

  def VisitProduct(self, product, name, depth):
    self._GenClass(product, product.attributes, name, None, depth)
