"""front_end.py: Lexer and parser for the ASDL schema language."""
from __future__ import print_function

from asdl import ast
from asdl.ast import (Module, TypeDecl, SubTypeDecl, Field)
from asdl import parse
from asdl.parse import ASDLSyntaxError
from asdl.util import log

from typing import List, Dict, Tuple, IO, cast, TYPE_CHECKING

if TYPE_CHECKING:
    TypeLookup = Dict[str, ast.asdl_type_t]

_ = log

_PRIMITIVE_TYPES = [
    'string',
    'int',
    'uint16',  # used for Token length - should we generalize this?
    'BigInt',
    'float',
    'bool',

    # 'any' is used for value.{BuiltinProc,BuiltinFunc}, to cast from class
    # type
    'any',
]


def _ResolveType(typ, type_lookup):
    # type: (ast.type_expr_t, TypeLookup) -> None
    """Recursively attach a 'resolved' field to AST nodes."""
    if isinstance(typ, ast.NamedType):
        if typ.name not in _PRIMITIVE_TYPES:
            ast_node = type_lookup.get(typ.name)
            if ast_node is None:
                raise ASDLSyntaxError("Couldn't find type %r" % typ.name)
            typ.resolved = ast_node

    elif isinstance(typ, ast.ParameterizedType):
        for child in typ.children:
            _ResolveType(child, type_lookup)

        if typ.type_name == 'Optional':
            child = typ.children[0]
            if isinstance(child, ast.NamedType):
                if child.name in _PRIMITIVE_TYPES and child.name != 'string':
                    raise ASDLSyntaxError(
                        'Optional primitive type {} not allowed'.format(
                            child.name))

                if child.resolved and isinstance(child.resolved,
                                                 ast.SimpleSum):
                    raise ASDLSyntaxError(
                        'Optional simple sum type {} not allowed'.format(
                            child.name))

    else:
        raise AssertionError()


def _ResolveFields(field_ast_nodes, type_lookup):
    # type: (List[Field], TypeLookup) -> None
    """
    Args:
      type_lookup: Populated by name resolution
    """
    for field in field_ast_nodes:
        _ResolveType(field.typ, type_lookup)


def _ResolveModule(module, type_lookup):
    # type: (Module, TypeLookup) -> None
    """Name resolution for NamedType."""

    # Note: we don't actually load the type, and instead leave that to MyPy /
    # C++.  A consequence of this is TypeNameHeuristic().
    for u in module.uses:
        for type_name in u.type_names:
            type_lookup[type_name] = u

    # NOTE: We need two passes because types can be mutually recursive, e.g.
    # asdl/arith.asdl.

    # First pass: collect declared types and make entries for them.
    for ex in module.externs:
        last = ex.names[-1]  # e.g. _Callable
        if last in type_lookup:
            raise ASDLSyntaxError('Type %r was already defined' % last)
        type_lookup[last] = ex

    for d in module.dfns:

        if isinstance(d, SubTypeDecl):
            if d.name in type_lookup:
                raise ASDLSyntaxError('Type %r was already defined' % d.name)

            # e.g. CompoundWord < List[str]
            type_lookup[d.name] = ast.DummyType()  # this value isn't used?

        elif isinstance(d, TypeDecl):
            if d.name in type_lookup:
                raise ASDLSyntaxError('Type %r was already defined' % d.name)

            # e.g. Token = (str a)
            type_lookup[d.name] = d.value

        else:
            raise AssertionError()

    # Second pass: add NamedType.resolved field
    for d in module.dfns:
        if isinstance(d, SubTypeDecl):  # no fields
            _ResolveType(d.base_class, type_lookup)
            continue

        d = cast(ast.TypeDecl, d)

        ast_node = d.value
        if isinstance(ast_node, ast.Product):
            #log('fields %s', ast_node.fields)
            _ResolveFields(ast_node.fields, type_lookup)
            continue

        if isinstance(ast_node, ast.Sum):
            for cons in ast_node.types:
                _ResolveFields(cons.fields, type_lookup)
            continue

        raise AssertionError(ast_node)


def LoadSchema(f, verbose=False):
    # type: (IO[bytes], bool) -> Tuple[ast.Module, TypeLookup]
    """Returns an AST for the schema."""
    p = parse.ASDLParser()
    schema_ast = p.parse(f)
    if verbose:
        import sys
        schema_ast.Print(sys.stdout, 0)

    # Make sure all the names are valid
    type_lookup = {}  # type: TypeLookup
    _ResolveModule(schema_ast, type_lookup)
    return schema_ast, type_lookup
