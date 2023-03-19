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

from typing import List

# The following classes are the AST for the ASDL schema, i.e. the "meta-AST".
# See the EBNF at the top of the file to understand the logical connection
# between the various node types.


class AST(object):

  def Print(self, f, indent):
    raise NotImplementedError()

  def __str__(self):
    f = cStringIO.StringIO()
    self.Print(f, 0)
    return f.getvalue()


class Use(AST):

  def __init__(self, module_parts, type_names):
    self.module_parts = module_parts
    self.type_names = type_names

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sUse %s {\n' % (ind, ' '.join(self.module_parts)))
    f.write('  %s%s\n' % (ind, ', '.join(t for t in self.type_names)))
    f.write('%s}\n' % ind)


class Module(AST):

  def __init__(self, name, uses, dfns):
    self.name = name
    self.uses = uses
    self.dfns = dfns

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sModule %s {\n' % (ind, self.name))

    for u in self.uses:
      u.Print(f, indent + 1)
      f.write('\n')

    for d in self.dfns:
      d.Print(f, indent + 1)
      f.write('\n')
    f.write('%s}\n' % ind)


class TypeDecl(AST):
  """A binding of name to a Sum or Product type."""

  def __init__(self, name, value):
    self.name = name  # type: str
    self.value = value  # type: AST

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sType %s {\n' % (ind, self.name))
    self.value.Print(f, indent + 1)
    f.write('%s}\n' % ind)


class NamedType(AST):
  """ 
  int, string are resolved to a Primitive type
  'Point' can be resolved to CompoundSum instance, etc.
  """

  def __init__(self, name):
    # type: (str) -> None
    self.name = name

    # Mutated by _ResolveModule / _ResolveType
    self.resolved = None

  def Print(self, f, indent):
    """Printed on one line."""
    ind = indent * '  '
    f.write('NamedType %s' % (self.name))  # printed after field
    f.write(' (%r)' % self.resolved)

  def IsOptional(self):
    return False

  def IsList(self):
    return False

  def IsDict(self):
    return False


class ParameterizedType(AST):
  """A parameterized type expression, e.g. the type of a field.

  e.g. Dict[string, int]   Dict[int, array[string]]

  self.children is empty if it's a leaf.

  Note:

  string*  <=>  array[string]
  mytype?  <=>  maybe[mytype]
  """

  def __init__(self, type_name, children):
    self.type_name = type_name  # type: str
    self.children = children  # type: List[AST]

  def Print(self, f, indent):
    """Printed on one line."""
    ind = indent * '  '
    f.write('%s' % (self.type_name))  # printed after field
    if self.children:
      f.write(' [ ')
      for i, child in enumerate(self.children):
        if i != 0:
          f.write(', ')
        child.Print(f, indent + 1)
      f.write(' ]')

  def IsOptional(self):
    return self.type_name == 'Optional'

  def IsList(self):
    if self.type_name == 'List':
      return True
    if self.type_name == 'Optional':
      return self.children[0].IsList()
    return False

  def IsDict(self):
    if self.type_name == 'Dict':
      return True
    if self.type_name == 'Optional':
      return self.children[0].IsDict()
    return False


class Field(AST):

  def __init__(self, typ, name):
    # type: (AST, str) -> None
    self.typ = typ  # type expression
    self.name = name  # variable name

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sField %r ' % (ind, self.name))
    self.typ.Print(f, indent)
    f.write('\n')


class _CompoundAST(AST):
  """Either a Product or Constructor.

  encode.py and format.py need a reflection API.
  """

  def __init__(self, fields):
    self.fields = fields or []


class Constructor(_CompoundAST):

  def __init__(self, name, shared_type=None, fields=None):
    _CompoundAST.__init__(self, fields)
    self.name = name
    self.shared_type = shared_type  # for DoubleQuoted %double_quoted

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sConstructor %s' % (ind, self.name))
    if self.shared_type:
      f.write(' %%%s' % self.shared_type)

    if self.fields:
      f.write(' {\n')
      for field in self.fields:
        field.Print(f, indent + 1)
      f.write('%s}' % ind)

    f.write('\n')


class Sum(AST):

  def __init__(self, types, attributes=None, generate=None):
    self.types = types  # type: List[Constructor]
    self.attributes = attributes or []
    self.generate = generate or []

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sSum {\n' % ind)
    for t in self.types:
      t.Print(f, indent + 1)
    if self.attributes:
      f.write('\n')
      f.write('%s  (attributes)\n' % ind)
      for a in self.attributes:
        a.Print(f, indent + 1)
    if self.generate:
      f.write('%s  generate %s\n' % (ind, self.generate))
    f.write('%s}\n' % ind)


class SimpleSum(Sum):
  pass


class Product(_CompoundAST):

  def __init__(self, fields, attributes=None):
    _CompoundAST.__init__(self, fields)
    self.attributes = attributes or []

  def Print(self, f, indent):
    ind = indent * '  '
    f.write('%sProduct {\n' % ind)
    for field in self.fields:
      field.Print(f, indent + 1)
    if self.attributes:
      f.write('\n')
      f.write('%s  (attributes)\n' % ind)
      for a in self.attributes:
        a.Print(f, indent + 1)
    f.write('%s}\n' % ind)


#
# Helpers
#


def TypeNameHeuristic(t):
  # type: (str) -> str
  """
  For 'use'.  We don't parse the imported file, so we have a heuristic based on
  the name!  e.g. re_t or BraceGroup
  """
  return '%s_t' % t if t[0].islower() else t
