#-------------------------------------------------------------------------------
# Parser for ASDL [1] definition files. Reads in an ASDL description and parses
# it into an AST that describes it.
#
# The EBNF we're parsing here: Figure 1 of the paper [1]. Extended to support
# modules and attributes after a product. Words starting with Capital letters
# are terminals. Literal tokens are in "double quotes". Others are
# non-terminals. Id is either TokenId or ConstructorId.
#
# module        ::= "module" Id "{" [definitions] "}"
# definitions   ::= { TypeId "=" type }
# type          ::= product | sum
# product       ::= fields ["attributes" fields]
# fields        ::= "(" { field, "," } field ")"
# field         ::= TypeId ["?" | "*"] [Id]
# sum           ::= constructor { "|" constructor } ["attributes" fields]
# constructor   ::= ConstructorId [fields]
#
# [1] "The Zephyr Abstract Syntax Description Language" by Wang, et. al. See
#     http://asdl.sourceforge.net/
#-------------------------------------------------------------------------------
from __future__ import print_function

import cStringIO


# TODO: There should be SimpleSumType(_SumType) and CompoundSumType(_SumType)
# That can be determined at compile time with this function.  is_simple()
# should move to front_end.py.

# PATCH: Moved this function from asdl_c.py.
def is_simple(sum):
  """Return True if a sum is a simple.

    A sum is simple if its types have no fields, e.g.
    unaryop = Invert | Not | UAdd | USub
    """
  for t in sum.types:
    if t.fields:
      return False
  return True


#
# Type Descriptors
#
# These are more convenient than using the AST directly, since it still has
# string type names?
#
# Although we share Product and Sum.

class _RuntimeType(object):
  """A node hierarchy that exists at runtime."""
  pass


class StrType(_RuntimeType):
  def __repr__(self):
    return '<Str>'


class IntType(_RuntimeType):
  def __repr__(self):
    return '<Int>'


class BoolType(_RuntimeType):
  def __repr__(self):
    return '<Bool>'


class ArrayType(_RuntimeType):
  def __init__(self, desc):
    self.desc = desc

  def __repr__(self):
    return '<Array %s>' % self.desc


class MaybeType(_RuntimeType):
  def __init__(self, desc):
    self.desc = desc  # another descriptor

  def __repr__(self):
    return '<Maybe %s>' % self.desc


class UserType(_RuntimeType):
  def __init__(self, typ):
    assert isinstance(typ, type), typ
    self.typ = typ

  def __repr__(self):
    return '<UserType %s>' % self.typ


class SumType(_RuntimeType):
  """Dummy node that doesn't require any reflection.

  obj.ASDL_TYPE points directly to the constructor, which you reflect on.
  """
  def __init__(self):
    pass

  def __repr__(self):
    return '<SumType>'  # We need an entry for this but we don't use it?


class CompoundType(_RuntimeType):
  """A product or Constructor instance.  Both have fields."""
  def __init__(self, fields):
    # List of (name, _RuntimeType) tuples.
    # NOTE: This list may be mutated after its set.
    self.fields = fields

  def __repr__(self):
    return '<CompoundType %s>' % self.fields

  def GetFieldNames(self):
    for field_name, _ in self.fields:
      yield field_name

  def GetFields(self):
    for field_name, descriptor in self.fields:
      yield field_name, descriptor

  def LookupFieldType(self, field_name):
    """
    NOTE: Only used by py_meta.py.
    """
    for n, descriptor in self.fields:
      if n == field_name:
        return descriptor
    raise AssertionError(field_name)


BUILTIN_TYPES = {
    'string': StrType(),
    'int': IntType(),
    'bool': BoolType(),
}


# TODO: Rename this to Reflection?
class TypeLookup(object):
  """Look up types by name.

  They are put in a flat namespace.
  """
  def __init__(self, runtime_type_lookup):
    self.runtime_type_lookup = runtime_type_lookup  # type name -> RuntimeType

  def ByTypeName(self, type_name):
    """Given a string, return a type descriptor.

    Used by generated code, e.g. in _devbuild/gen/osh_asdl.py.
    Args:
      type_name: string, e.g. 'word_part' or 'LiteralPart'
    """
    #if not type_name in self.compound_types:
    #  print('FATAL: %s' % self.compound_types.keys())
    #return self.compound_types[type_name]
    if not type_name in self.runtime_type_lookup:
      print('FATAL: %s' % self.runtime_type_lookup.keys())
    return self.runtime_type_lookup[type_name]

  def __repr__(self):
    return repr(self.runtime_type_lookup)


# The following classes are the AST for the ASDL schema, i.e. the "meta-AST".
# See the EBNF at the top of the file to understand the logical connection
# between the various node types.

class AST(object):
    def Print(self, f, indent):
        raise NotImplementedError

    def __repr__(self):
        f = cStringIO.StringIO()
        self.Print(f, 0)
        return f.getvalue()


class Module(AST):
    def __init__(self, name, dfns):
        self.name = name
        self.dfns = dfns

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sModule %s {\n' % (ind, self.name))

        for d in self.dfns:
          d.Print(f, indent+1)
          f.write('\n')
        f.write('%s}\n' % ind)


class Type(AST):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sType %s {\n' % (ind, self.name))
        self.value.Print(f, indent+1)
        f.write('%s}\n' % ind)


class Field(AST):
    def __init__(self, type, name=None, seq=False, opt=False):
        self.type = type
        self.name = name
        self.seq = seq
        self.opt = opt

    def Print(self, f, indent):
        extra = []
        if self.seq:
            extra.append('seq=True')
        elif self.opt:
            extra.append('opt=True')
        else:
            extra = ""

        ind = indent * '  '
        f.write('%sField %s %s' % (ind, self.name, self.type))
        if extra:
          f.write(' (')
          f.write(', '.join(extra))
          f.write(')')
        f.write('\n')


class _CompoundAST(AST):
    """Either a Product or Constructor.

    encode.py and format.py need a reflection API.
    """

    def __init__(self, fields):
        self.fields = fields or []

        # Add fake spids field.
        # TODO: Only do this if 'attributes' are set.
        if self.fields:
          self.fields.append(Field('int', 'spids', seq=True))


class Constructor(_CompoundAST):
    def __init__(self, name, fields=None):
        _CompoundAST.__init__(self, fields)
        self.name = name

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sConstructor %s' % (ind, self.name))

        if self.fields:
          f.write(' {\n')
          for field in self.fields:
            field.Print(f, indent+1)
          f.write('%s}' % ind)

        f.write('\n')


class Sum(AST):
    def __init__(self, types, attributes=None):
        self.types = types  # List[Constructor]
        self.attributes = attributes or []

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sSum {\n' % ind)
        for t in self.types:
          t.Print(f, indent+1)
        if self.attributes:
          f.write('%s\n' % self.attributes)
        f.write('%s}\n' % ind)


class Product(_CompoundAST):
    def __init__(self, fields, attributes=None):
        _CompoundAST.__init__(self, fields)
        self.attributes = attributes or []

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sProduct {\n' % ind)
        for field in self.fields:
          field.Print(f, indent+1)
        if self.attributes:
          f.write('%s\n' % self.attributes)
        f.write('%s}\n' % ind)
