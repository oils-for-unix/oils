#!/usr/bin/python
"""
meta.py

Another "thin waist" of the interpreter.  It can be happen at compile time!

We are following the code <-> data pattern, and this is the "data" module.
id_kind and asdl are the "code" modules.

Usage:
  from core.meta import syntax_asdl, Id, Kind, ID_SPEC
"""

from _devbuild.gen.types_asdl import bool_arg_type_t, redir_arg_type_e
from _devbuild.gen.id_kind_asdl import (
    Id, Id_t, Kind_t, ID_INSTANCES, KIND_INSTANCES
)
from core import id_kind

from typing import Dict


_ID_TO_KIND_INTEGERS = {}  # type: Dict[int, int]


def LookupKind(id_):
  # type: (Id_t) -> Kind_t
  """Id_t -> Kind_t"""
  return KIND_INSTANCES[_ID_TO_KIND_INTEGERS[id_.enum_id]]


# Do NOT create any any more instances of Id.  Always use IdInstance().
def IdInstance(i):
  # type: (int) -> Id_t
  return ID_INSTANCES[i]


BOOL_ARG_TYPES = {}  # type: Dict[int, bool_arg_type_t]

# Used by builtin_bracket.py
TEST_UNARY_LOOKUP = {}  # type: Dict[str, int]
TEST_BINARY_LOOKUP = {}  # type: Dict[str, int]
TEST_OTHER_LOOKUP = {}  # type: Dict[str, int]


#
# Initialize Id and Kind
#

ID_SPEC = id_kind.IdSpec(_ID_TO_KIND_INTEGERS, BOOL_ARG_TYPES)

id_kind.AddKinds(ID_SPEC)
id_kind.AddBoolKinds(ID_SPEC)  # must come second
id_kind.SetupTestBuiltin(ID_SPEC,
                         TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                         TEST_OTHER_LOOKUP)

# Debug Stats
_kind_sizes = ID_SPEC.kind_sizes


#
# Redirect Tables associated with IDs
#
# These might be osh specific.
#

REDIR_DEFAULT_FD = {
    # filename
    Id.Redir_Less: 0,  # cat <input.txt means cat 0<input.txt
    Id.Redir_Great: 1,
    Id.Redir_DGreat: 1,
    Id.Redir_Clobber: 1,
    Id.Redir_LessGreat: 1,  # TODO: What does echo <>foo do?
    # bash &> and &>>
    Id.Redir_AndGreat: 1,
    Id.Redir_AndDGreat: 1,

    # descriptor
    Id.Redir_GreatAnd: 1,  # echo >&2  means echo 1>&2
    Id.Redir_LessAnd: 0,   # echo <&3 means echo 0<&3, I think

    Id.Redir_TLess: 0,  # here word

    # here docs included
    Id.Redir_DLess: 0,
    Id.Redir_DLessDash: 0,
}

REDIR_ARG_TYPES = {
    # filename
    Id.Redir_Less: redir_arg_type_e.Path,
    Id.Redir_Great: redir_arg_type_e.Path,
    Id.Redir_DGreat: redir_arg_type_e.Path,
    Id.Redir_Clobber: redir_arg_type_e.Path,
    Id.Redir_LessGreat: redir_arg_type_e.Path,
    # bash &> and &>>
    Id.Redir_AndGreat: redir_arg_type_e.Path,
    Id.Redir_AndDGreat: redir_arg_type_e.Path,

    # descriptor
    Id.Redir_GreatAnd: redir_arg_type_e.Desc,
    Id.Redir_LessAnd: redir_arg_type_e.Desc,

    Id.Redir_TLess: redir_arg_type_e.Here,  # here word
    # note: here docs aren't included
}
