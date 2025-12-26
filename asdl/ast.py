"""AST for ASDL.

This is not self-hosted!  If it were, it would look something like this.

TODO: move it toward this schema

type_expr =
  NamedType(str name, asdl_type resolved)
| ParameterizedType(str type_name, List[type_expr] children)

Field = (type_expr typ, str name)

Constructor = (List[Field] fields, str name, str shared_type)

# TODO: use variant instead of constructor
variant =
  Simple(str name)
  Compound(str name, List[fields])
  SharedVariant(str tag_name, str shared_variant)

asdl_type =
    Sum(List[Constructor] variants, List[str] generate)
  | SimpleSum()  # This is just List[name]
  | Product(List[Field] fields)

Use = (List[str] module_parts, str type_names)
Extern = (List[str] names)

Module = (str name, List[Use] uses, List[Extern] externs, List[binding] defs)

# Note: binding and entry can be combined

binding = 
  TypeDecl(str name, asdl_type value)
| SubTypeDecl(str name, type_expr base_class)

entry =
  Use %Use
| Extern %Extern
| Binding(binding b)
"""
from __future__ import print_function

import cStringIO

from typing import List, Optional

# The following classes are the AST for the ASDL schema, i.e. the "meta-AST".
# See the EBNF at the top of the file to understand the logical connection
# between the various node types.


class _Printable(object):

    def Print(self, f, indent):
        raise NotImplementedError()

    def __str__(self):
        f = cStringIO.StringIO()
        self.Print(f, 0)
        return f.getvalue()


class Use(_Printable):

    def __init__(self, module_parts, type_names):
        # type: (List[str], List[str]) -> None
        self.module_parts = module_parts
        self.type_names = type_names

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sUse %s {\n' % (ind, ' '.join(self.module_parts)))
        f.write('  %s%s\n' % (ind, ', '.join(t for t in self.type_names)))
        f.write('%s}\n' % ind)


class Extern(_Printable):

    def __init__(self, names):
        # type: (List[str]) -> None
        self.names = names

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sExtern [ %s ]\n' % (ind, ' '.join(self.names)))


class Module(_Printable):

    def __init__(self, name, uses, externs, dfns):
        # type: (str, List[Use], List[Extern], List[binding_t]) -> None
        self.name = name
        self.uses = uses
        self.externs = externs
        self.dfns = dfns

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sModule %s {\n' % (ind, self.name))

        for u in self.uses:
            u.Print(f, indent + 1)
            f.write('\n')

        for e in self.externs:
            e.Print(f, indent + 1)
            f.write('\n')

        for d in self.dfns:
            d.Print(f, indent + 1)
            f.write('\n')
        f.write('%s}\n' % ind)


class binding_t(_Printable):
    pass


class TypeDecl(binding_t):
    """A binding of name to a Sum or Product type."""

    def __init__(self, name, value):
        # type: (str, asdl_type_t) -> None
        self.name = name
        self.value = value

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sType %s {\n' % (ind, self.name))
        self.value.Print(f, indent + 1)
        f.write('%s}\n' % ind)


class SubTypeDecl(binding_t):
    """A declaration of a subtype.

    CompoundWord < List[word_part]
    """

    def __init__(self, name, base_class):
        # type: (str, type_expr_t) -> None
        self.name = name
        self.base_class = base_class

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sType %s {\n' % (ind, self.name))
        self.base_class.Print(f, indent + 1)
        f.write('%s}\n' % ind)


class type_expr_t(object):
    pass


class NamedType(type_expr_t):
    """Int, string are resolved to a Primitive type 'Point' can be resolved to
    CompoundSum instance, etc."""

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

        # Mutated by _ResolveModule / _ResolveType
        self.resolved = None

    def Print(self, f, indent):
        """Printed on one line."""
        f.write('NamedType %s' % (self.name))  # printed after field
        f.write(' (%r)' % self.resolved)


class ParameterizedType(type_expr_t):
    """A parameterized type expression, e.g. the type of a field.

    e.g. Dict[string, int]   Dict[int, array[string]]

    self.children is empty if it's a leaf.

    Note:

    string*  <=>  array[string]
    mytype?  <=>  maybe[mytype]
    """

    def __init__(self, type_name, children):
        # type: (str, List[type_expr_t]) -> None
        self.type_name = type_name
        self.children = children

    def Print(self, f, indent):
        """Printed on one line."""
        f.write('%s' % (self.type_name))  # printed after field
        if self.children:
            f.write(' [ ')
            for i, child in enumerate(self.children):
                if i != 0:
                    f.write(', ')
                child.Print(f, indent + 1)
            f.write(' ]')


class Field(_Printable):

    def __init__(self, typ, name):
        # type: (type_expr_t, str) -> None
        self.typ = typ  # type expression
        self.name = name  # variable name

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sField %r ' % (ind, self.name))
        self.typ.Print(f, indent)
        f.write('\n')


class asdl_type_t(_Printable):
    pass


class _CompoundAST(asdl_type_t):
    """Either a Product or Constructor.

    encode.py and format.py need a reflection API.
    """

    def __init__(self, fields):
        # type: (List[Field]) -> None
        self.fields = fields or []


class Constructor(asdl_type_t):

    def __init__(self, name, shared_type, fields):
        # type: (str, Optional[type_expr_t], List[Field]) -> None
        self.name = name
        self.shared_type = shared_type  # for DoubleQuoted %DoubleQuoted
        self.fields = fields or []

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


class Sum(_Printable):

    def __init__(self, types, generate=None):
        # type: (List[Constructor], Optional[List[str]]) -> None
        self.types = types
        self.generate = generate or []  # type: List[str]

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sSum {\n' % ind)
        for t in self.types:
            t.Print(f, indent + 1)
        if self.generate:
            f.write('%s  generate %s\n' % (ind, self.generate))
        f.write('%s}\n' % ind)


class SimpleSum(Sum):
    pass


class Product(_CompoundAST):

    def __init__(self, fields):
        # type: (List[Field]) -> None
        self.fields = fields

    def Print(self, f, indent):
        ind = indent * '  '
        f.write('%sProduct {\n' % ind)
        for field in self.fields:
            field.Print(f, indent + 1)
        f.write('%s}\n' % ind)


#
# Helpers
#


def TypeNameHeuristic(t):
    # type: (str) -> str
    """For 'use'.

    We don't parse the imported file, so we have a heuristic based on
    the name!  e.g. re_t or BraceGroup
    """
    return '%s_t' % t if t[0].islower() else t


def MakeSimpleVariant(name):
    # type: (str) -> Constructor
    """
    Used by frontend/{consts,options}_gen.py
    """
    return Constructor(name, None, None)


def IsOptional(t):
    # type: (type_expr_t) -> bool
    if isinstance(t, NamedType):
        return False

    elif isinstance(t, ParameterizedType):
        return t.type_name == 'Optional'

    else:
        raise AssertionError()


def IsList(t):
    # type: (type_expr_t) -> bool
    if isinstance(t, NamedType):
        return False

    elif isinstance(t, ParameterizedType):
        if t.type_name == 'List':
            return True
        if t.type_name == 'Optional':
            return IsList(t.children[0])
        return False

    else:
        raise AssertionError()


def IsDict(t):
    # type: (type_expr_t) -> bool
    if isinstance(t, NamedType):
        return False

    elif isinstance(t, ParameterizedType):
        if t.type_name == 'Dict':
            return True
        if t.type_name == 'Optional':
            return IsDict(t.children[0])
        return False

    else:
        raise AssertionError()
