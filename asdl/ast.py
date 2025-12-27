"""AST type definitions for Zephyr ASDL itself.

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

Use = (List[str] module_parts, str type_names)
Extern = (List[str] names)

asdl_type =
    Sum(List[Constructor] variants, List[str] generate)
  | SimpleSum()  # This is just List[name]
  | Product(List[Field] fields)

    # These go in the TypeLookup dict!
    # Shouldn't they be a BINDING?
  | Use %Use
  | Extern %Extern

binding = 
  TypeDecl(str name, asdl_type value)
| SubTypeDecl(str name, type_expr base_class)

Module = (
  str name,
  List[Use] uses,
  List[Extern] externs,
  # Are Type and SubType ordered?  Right now they are.  C++ and Python may
  # differ in terms of order.
  List[binding] defs
)
"""
from __future__ import print_function

import cStringIO

from typing import List, Optional, Tuple, IO


class _Printable(object):

    def Print(self, f, indent):
        raise NotImplementedError()

    def __str__(self):
        # type: () -> str
        f = cStringIO.StringIO()
        self.Print(f, 0)
        return f.getvalue()


class asdl_type_t(_Printable):
    pass


class DummyType(asdl_type_t):
    """
    Dummy value for subtyping: List_of_command < List[command]

    TODO: Improve this representation
    """
    pass


class Use(asdl_type_t):

    def __init__(self, module_parts, type_names):
        # type: (List[str], List[str]) -> None
        self.module_parts = module_parts
        self.type_names = type_names

    def Print(self, f, indent):
        # type: (IO, int) -> None
        ind = indent * '  '
        f.write('%sUse %s {\n' % (ind, ' '.join(self.module_parts)))
        f.write('  %s%s\n' % (ind, ', '.join(t for t in self.type_names)))
        f.write('%s}\n' % ind)


class Extern(asdl_type_t):

    def __init__(self, names):
        # type: (List[str]) -> None
        self.names = names

    def Print(self, f, indent):
        # type: (IO, int) -> None
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
        # type: (IO, int) -> None
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
        # type: (IO, int) -> None
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
        # type: (IO, int) -> None
        ind = indent * '  '
        f.write('%sType %s {\n' % (ind, self.name))
        self.base_class.Print(f, indent + 1)
        f.write('%s}\n' % ind)


class type_expr_t(_Printable):
    pass


class NamedType(type_expr_t):
    """Int, string are resolved to a Primitive type 'Point' can be resolved to
    CompoundSum instance, etc."""

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

        # Mutated by _ResolveModule / _ResolveType
        self.resolved = None  # type: Optional[asdl_type_t]

    def Print(self, f, indent):
        # type: (IO, int) -> None
        f.write('NamedType %s' % (self.name))  # printed after field
        f.write(' (%r)' % self.resolved)


class ParameterizedType(type_expr_t):
    """A parameterized type expression, e.g. the type of a field.

    Examples:
        List[mytype]       # used to be mytype*
        Optional[mytype]   # used to by mytype?
        Dict[str, int]
        Dict[int, List[str]]
    """

    def __init__(self, type_name, children):
        # type: (str, List[type_expr_t]) -> None
        self.type_name = type_name
        self.children = children

    def Print(self, f, indent):
        # type: (IO, int) -> None
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
        # type: (IO, int) -> None
        ind = indent * '  '
        f.write('%sField %r ' % (ind, self.name))
        self.typ.Print(f, indent)
        f.write('\n')


class Constructor(asdl_type_t):

    def __init__(self, name, shared_type, fields):
        # type: (str, Optional[str], List[Field]) -> None
        self.name = name
        self.shared_type = shared_type  # for DoubleQuoted %DoubleQuoted
        self.fields = fields or []

    def Print(self, f, indent):
        # type: (IO, int) -> None
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
        # type: (IO[bytes], int) -> None
        ind = indent * '  '
        f.write('%sSum {\n' % ind)
        for t in self.types:
            t.Print(f, indent + 1)
        if self.generate:
            f.write('%s  generate %s\n' % (ind, self.generate))
        f.write('%s}\n' % ind)


class SimpleSum(Sum):
    pass


class Product(_Printable):

    def __init__(self, fields):
        # type: (List[Field]) -> None
        self.fields = fields

    def Print(self, f, indent):
        # type: (IO[bytes], int) -> None
        ind = indent * '  '
        f.write('%sProduct {\n' % ind)
        for field in self.fields:
            field.Print(f, indent + 1)
        f.write('%s}\n' % ind)


#
# Helpers
#


def TypeNameHeuristic(asdl_name):
    # type: (str) -> Tuple[str, bool]
    """For 'use'.

    We don't parse the imported file, so we have a heuristic based on
    the name!  e.g. re_t or BraceGroup
    """
    is_pointer = True

    if asdl_name == 'id':
        py_name = 'Id_t'
        is_pointer = False

    elif asdl_name == 'kind':
        py_name = 'Kind_t'
        is_pointer = False

    elif asdl_name[0].islower():
        py_name = '%s_t' % asdl_name

    else:
        py_name = asdl_name

    return py_name, is_pointer


def NameHack(sum_name):
    if sum_name == 'id':
        return 'Id'
    elif sum_name == 'kind':
        return 'Kind'
    return sum_name


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
