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


class StrType(object):
  def __repr__(self):
    return '<Str>'

class IntType(object):
  def __repr__(self):
    return '<Int>'

class BoolType(object):
  def __repr__(self):
    return '<Bool>'


class ArrayType(object):
  def __init__(self, desc):
    self.desc = desc

  def __repr__(self):
    return '<Array %s>' % self.desc

class MaybeType(object):
  def __init__(self, desc):
    self.desc = desc  # another descriptor

  def __repr__(self):
    return '<Maybe %s>' % self.desc

class UserType(object):
  def __init__(self, typ):
    assert isinstance(typ, type), typ
    self.typ = typ

  def __repr__(self):
    return '<UserType %s>' % self.typ


# The following classes define nodes into which the ASDL description is parsed.
# Note: this is a "meta-AST". ASDL files (such as Python.asdl) describe the AST
# structure used by a programming language. But ASDL files themselves need to be
# parsed. This module parses ASDL files and uses a simple AST to represent them.
# See the EBNF at the top of the file to understand the logical connection
# between the various node types.

builtin_types = {'string', 'int', 'bool'}

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


class _CompoundType(AST):
    """Either a Product or Constructor.

    encode.py and format.py need a reflection API.
    """

    def __init__(self, fields):
        self.fields = fields or []

        # Add fake spids field.
        # TODO: Only do this if 'attributes' are set.
        if self.fields:
          self.fields.append(Field('int', 'spids', seq=True))

        self.field_lookup = {f.name: f for f in self.fields}
        self.type_lookup = None  # set by ResolveTypes()

        self.type_cache = {}

    def GetFieldNames(self):
        for f in self.fields:
          yield f.name

    def GetFields(self):
        for f in self.fields:
          field_name = f.name
          yield field_name, self.LookupFieldType(field_name)

    def LookupFieldType(self, field_name):
        # Cache and return it.  We don't want to create new instances every
        # time we iterate over the fields.
        try:
          return self.type_cache[field_name]
        except KeyError:
          field = self.field_lookup[field_name]
          desc = self.type_lookup.ByFieldInstance(field)
          self.type_cache[field_name] = desc
          return desc


class Constructor(_CompoundType):
    def __init__(self, name, fields=None):
        _CompoundType.__init__(self, fields)
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


class Product(_CompoundType):
    def __init__(self, fields, attributes=None):
        _CompoundType.__init__(self, fields)
        self.attributes = attributes or []

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sProduct {\n' % ind)
        for field in self.fields:
          field.Print(f, indent+1)
        if self.attributes:
          f.write('%s\n' % self.attributes)
        f.write('%s}\n' % ind)

