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


# The following classes are the AST for the ASDL schema, i.e. the "meta-AST".
# See the EBNF at the top of the file to understand the logical connection
# between the various node types.

class AST(object):
    def Print(self, f, indent):
        raise NotImplementedError()

    def __repr__(self):
        f = cStringIO.StringIO()
        self.Print(f, 0)
        return f.getvalue()


class Use(AST):
    def __init__(self, mod_name, type_names):
        self.mod_name = mod_name
        self.type_names = type_names

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sUse %s {\n' % (ind, self.mod_name))
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
          u.Print(f, indent+1)
          f.write('\n')

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


class Constructor(_CompoundAST):
    def __init__(self, name, shared_type=None, fields=None):
        _CompoundAST.__init__(self, fields)
        self.name = name
        self.shared_type = shared_type  # for DoubleQuoted %double_quoted

        # Add fake spids field.
        # TODO: Only do this if 'attributes' are set.
        if self.fields:
          #self.fields.append(Field('int', 'spids', seq=True))
          pass

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sConstructor %s' % (ind, self.name))
        if self.shared_type:
          f.write(' %%%s' % self.shared_type)

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
          f.write('\n')
          f.write('%s  (attributes)\n' % ind)
          for a in self.attributes:
            a.Print(f, indent+1)
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
          f.write('\n')
          f.write('%s  (attributes)\n' % ind)
          for a in self.attributes:
            a.Print(f, indent+1)
        f.write('%s}\n' % ind)
