#!/usr/bin/env python2
"""
asdl_cpp.py

Turn an ASDL schema into C++ code that reads the OHeap V1 format.

TODO:
- Optional fields
  - in osh, it's only used in two places:
  - arith_expr? for slice length
  - word? for var replace
  - So you're already using pointers, can encode the NULL pointer.

- Change everything to use references instead of pointers?  Non-nullable.
- Unify ClassDefVisitor and MethodBodyVisitor.
  - Whether you need a separate method body should be a flag.
  - offset calculations are duplicated
- generate a C++ pretty-printer

Technically we don't even need alignment?  I guess the reason is to increase
address space.  If 1, then we have 16MiB of code.  If 4, then we have 64 MiB.

Everything is decoded on the fly, or is a char*, which I don't think has to be
aligned (because the natural alignment woudl be 1 byte anyway.)
"""
from __future__ import print_function

import sys

from asdl import asdl_ as asdl
from asdl import front_end
from asdl import meta
from asdl import runtime
from asdl import visitor
from misc.old import encode

class ChainOfVisitors:
  def __init__(self, *visitors):
    self.visitors = visitors

  def VisitModule(self, module):
    for v in self.visitors:
      v.VisitModule(module)


_BUILTINS = {
    'string': 'char*',  # A read-only string is a char*
    'int': 'int',
    'bool': 'bool',
    'id': 'Id',  # Application specific hack for now
}

class ForwardDeclareVisitor(visitor.AsdlVisitor):
  """Print forward declarations.

  ASDL allows forward references of types, but C++ doesn't.
  """
  def VisitCompoundSum(self, sum, name, depth):
    self.Emit("class %(name)s_t;" % locals(), depth)

  def VisitProduct(self, product, name, depth):
    self.Emit("class %(name)s_t;" % locals(), depth)

  def EmitFooter(self):
    self.Emit("", 0)  # blank line


class ClassDefVisitor(visitor.AsdlVisitor):
  """Generate C++ classes and type-safe enums."""

  def __init__(self, f, enc_params, type_lookup, enum_types=None):
    visitor.AsdlVisitor.__init__(self, f)
    self.ref_width = enc_params.ref_width
    self.type_lookup = type_lookup
    self.enum_types = enum_types or {}
    self.pointer_type = enc_params.pointer_type
    self.footer = []  # lines

  def _GetCppType(self, field):
    """Return a string for the C++ name of the type."""
    type_name = field.type

    cpp_type = _BUILTINS.get(type_name)
    if cpp_type is not None:
      return cpp_type

    typ = self.type_lookup[type_name]
    if isinstance(typ, asdl.Sum) and asdl.is_simple(typ):
      # Use the enum instead of the class.
      return "%s_e" % type_name

    # - Pointer for optional type.
    # - ints and strings should generally not be optional?  We don't have them
    # in osh yet, so leave it out for now.
    if field.opt:
      return "%s_t*" % type_name

    return "%s_t&" % type_name

  def EmitFooter(self):
    for line in self.footer:
      self.f.write(line)

  def _EmitEnum(self, sum, name, depth):
    enum = []
    for i in xrange(len(sum.types)):
      type = sum.types[i]
      enum.append("%s = %d" % (type.name, i + 1))  # zero is reserved

    self.Emit("enum class %s_e : uint8_t {" % name, depth)
    self.Emit(", ".join(enum), depth + 1)
    self.Emit("};", depth)
    self.Emit("", depth)

  def VisitSimpleSum(self, sum, name, depth):
    self._EmitEnum(sum, name, depth)

  def VisitCompoundSum(self, sum, name, depth):
    # This is a sign that Python needs string interpolation!!!
    def Emit(s, depth=depth):
      self.Emit(s % sys._getframe(1).f_locals, depth)

    self._EmitEnum(sum, name, depth)

    Emit("class %(name)s_t : public Obj {")
    Emit(" public:")
    # All sum types have a tag
    Emit("%(name)s_e tag() const {", depth + 1)
    Emit("return static_cast<%(name)s_e>(bytes_[0]);", depth + 2)
    Emit("}", depth + 1)
    Emit("};")
    Emit("")

    # TODO: This should be replaced with a call to the generic
    # self.VisitChildren()
    super_name = "%s_t" % name
    for t in sum.types:
      self.VisitConstructor(t, super_name, depth)

    # rudimentary attribute handling
    for field in sum.attributes:
      type_name = str(field.type)
      assert type_name in runtime.BUILTIN_TYPES, type_name
      Emit("%s %s;" % (type_name, field.name), depth + 1)

  def VisitConstructor(self, cons, def_name, depth):
    #print(dir(cons))
    if cons.fields:
      self.Emit("class %s : public %s {" % (cons.name, def_name), depth)
      self.Emit(" public:", depth)
      offset = 1  #  for the ID
      for f in cons.fields:
        self.VisitField(f, cons.name, offset, depth + 1)
        offset += self.ref_width
      self.Emit("};", depth)
      self.Emit("", depth)

  def VisitProduct(self, product, name, depth):
    self.Emit("class %(name)s_t : public Obj {" % locals(), depth)
    self.Emit(" public:", depth)
    offset = 0
    for f in product.fields:
      type_name = '%s_t' % name
      self.VisitField(f, type_name, offset, depth + 1)
      offset += self.ref_width

    for field in product.attributes:
      # rudimentary attribute handling
      type_name = str(field.type)
      assert type_name in runtime.BUILTIN_TYPES, type_name
      self.Emit("%s %s;" % (type_name, field.name), depth + 1)
    self.Emit("};", depth)
    self.Emit("", depth)

  def VisitField(self, field, type_name, offset, depth):
    """
    Even though they are inline, some of them can't be in the class {}, because
    static_cast<> requires inheritance relationships to be already declared.  We
    have to print all the classes first, then all the bodies that might use
    static_cast<>.

    http://stackoverflow.com/questions/5808758/why-is-a-static-cast-from-a-pointer-to-base-to-a-pointer-to-derived-invalid
    """
    ctype = self._GetCppType(field)
    name = field.name
    pointer_type = self.pointer_type
    # Either 'left' or 'BoolBinary::left', depending on whether it's inline.
    # Mutated later.
    maybe_qual_name = name

    func_proto = None
    func_header = None
    body_line1 = None
    inline_body = None

    if field.seq:  # Array/repeated
      # For size accessor, follow the ref, and then it's the first integer.
      size_header = (
          'inline int %(name)s_size(const %(pointer_type)s* base) const {')
      size_body = "return Ref(base, %(offset)d).Int(0);"

      self.Emit(size_header % locals(), depth)
      self.Emit(size_body % locals(), depth + 1)
      self.Emit("}", depth)

      ARRAY_OFFSET = 'int a = (index+1) * 3;'
      A_POINTER = (
          'inline const %(ctype)s %(maybe_qual_name)s('
          'const %(pointer_type)s* base, int index) const')

      if ctype in ('bool', 'int'):
        func_header = A_POINTER + ' {'
        body_line1 = ARRAY_OFFSET
        inline_body = 'return Ref(base, %(offset)d).Int(a);'

      elif ctype.endswith('_e') or ctype in self.enum_types:
        func_header = A_POINTER + ' {'
        body_line1 = ARRAY_OFFSET
        inline_body = (
            'return static_cast<const %(ctype)s>(Ref(base, %(offset)d).Int(a));')

      elif ctype == 'char*':
        func_header = A_POINTER + ' {'
        body_line1 = ARRAY_OFFSET
        inline_body = 'return Ref(base, %(offset)d).Str(base, a);'

      else:
        # Write function prototype now; write body later.
        func_proto = A_POINTER + ';'

        maybe_qual_name = '%s::%s' % (type_name, name)
        func_def = A_POINTER + ' {'
        # This static_cast<> (downcast) causes problems if put within "class
        # {}".
        func_body = (
            'return static_cast<const %(ctype)s>('
            'Ref(base, %(offset)d).Ref(base, a));')

        self.footer.extend(visitor.FormatLines(func_def % locals(), 0))
        self.footer.extend(visitor.FormatLines(ARRAY_OFFSET, 1))
        self.footer.extend(visitor.FormatLines(func_body % locals(), 1))
        self.footer.append('}\n\n')
        maybe_qual_name = name  # RESET for later

    else:  # not repeated
      SIMPLE = "inline %(ctype)s %(maybe_qual_name)s() const {"
      POINTER = (
          'inline const %(ctype)s %(maybe_qual_name)s('
          'const %(pointer_type)s* base) const')

      if ctype in ('bool', 'int'):
        func_header = SIMPLE
        inline_body = 'return Int(%(offset)d);'

      elif ctype.endswith('_e') or ctype in self.enum_types:
        func_header = SIMPLE
        inline_body = 'return static_cast<const %(ctype)s>(Int(%(offset)d));'

      elif ctype == 'char*':
        func_header = POINTER + " {"
        inline_body = 'return Str(base, %(offset)d);'

      else:
        # Write function prototype now; write body later.
        func_proto = POINTER + ";"

        maybe_qual_name = '%s::%s' % (type_name, name)
        func_def = POINTER + ' {'
        if field.opt:
          func_body = (
              'return static_cast<const %(ctype)s>(Optional(base, %(offset)d));')
        else:
          func_body = (
              'return static_cast<const %(ctype)s>(Ref(base, %(offset)d));')

        # depth 0 for bodies
        self.footer.extend(visitor.FormatLines(func_def % locals(), 0))
        self.footer.extend(visitor.FormatLines(func_body % locals(), 1))
        self.footer.append('}\n\n')
        maybe_qual_name = name  # RESET for later

    if func_proto:
      self.Emit(func_proto % locals(), depth)
    else:
      self.Emit(func_header % locals(), depth)
      if body_line1:
        self.Emit(body_line1, depth + 1)
      self.Emit(inline_body % locals(), depth + 1)
      self.Emit("}", depth)


def main(argv):
  try:
    action = argv[1]
  except IndexError:
    raise RuntimeError('Action required')

  # TODO: Also generate a switch/static_cast<> pretty printer in C++!  For
  # debugging.  Might need to detect cycles though.
  if action == 'cpp':
    schema_path = argv[2]

    # NOTE: This import can't be at the top level osh/asdl_gen.py depends on
    # this gen_cpp.py module.  We should move all the main() functions out of
    # asdl/ and into command line tools.

    from core.meta import Id
    app_types = {'id': meta.UserType('id_kind_asdl', 'Id_t')}
    with open(schema_path) as input_f:
      module, type_lookup = front_end.LoadSchema(input_f, app_types)

    # TODO: gen_cpp.py should be a library and the application should add Id?
    # Or we should enable ASDL metaprogramming, and let Id be a metaprogrammed
    # simple sum type.

    f = sys.stdout

    # How do mutation of strings, arrays, etc.  work?  Are they like C++
    # containers, or their own?  I think they mirror the oil language
    # semantics.
    # Every node should have a mirror.  MutableObj.  MutableRef (pointer).
    # MutableArithVar -- has std::string.  The mirrors are heap allocated.
    # All the mutable ones should support Dump()/Encode()?
    # You can just write more at the end... don't need to disturb existing
    # nodes?  Rewrite pointers.

    alignment = 4
    enc = encode.Params(alignment)
    d = {'pointer_type': enc.pointer_type}

    f.write("""\
#include <cstdint>

class Obj {
 public:
  // Decode a 3 byte integer from little endian
  inline int Int(int n) const;

  inline const Obj& Ref(const %(pointer_type)s* base, int n) const;

  inline const Obj* Optional(const %(pointer_type)s* base, int n) const;

  // NUL-terminated
  inline const char* Str(const %(pointer_type)s* base, int n) const;

 protected:
  uint8_t bytes_[1];  // first is ID; rest are a payload
};

""" % d)

    # Id should be treated as an enum.
    c = ChainOfVisitors(
        ForwardDeclareVisitor(f),
        ClassDefVisitor(f, enc, type_lookup, enum_types=['Id']))
    c.VisitModule(module)

    f.write("""\
inline int Obj::Int(int n) const {
  return bytes_[n] + (bytes_[n+1] << 8) + (bytes_[n+2] << 16);
}

inline const Obj& Obj::Ref(const %(pointer_type)s* base, int n) const {
  int offset = Int(n);
  return reinterpret_cast<const Obj&>(base[offset]);
}

inline const Obj* Obj::Optional(const %(pointer_type)s* base, int n) const {
  int offset = Int(n);
  if (offset) {
    return reinterpret_cast<const Obj*>(base + offset);
  } else {
    return nullptr;
  }
}

inline const char* Obj::Str(const %(pointer_type)s* base, int n) const {
  int offset = Int(n);
  return reinterpret_cast<const char*>(base + offset);
}
""" % d)
  # uint32_t* and char*/Obj* aren't related, so we need to use
  # reinterpret_cast<>.
  # http://stackoverflow.com/questions/10151834/why-cant-i-static-cast-between-char-and-unsigned-char

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
