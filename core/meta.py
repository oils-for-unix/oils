#!/usr/bin/python
"""
meta.py

Another "thin waist" of the interpreter.  It can be happen at compile time!

We are following the code <-> data pattern, and this is the "data" module.
id_kind and asdl are the "code" modules.

Usage:
  from core.meta import syntax_asdl, Id, Kind, ID_SPEC
"""

from core import id_kind
from _devbuild.gen.id_kind_asdl import (Id, Id_t, Kind, Kind_t)


def _CreateInstanceLookup(id_enum, id_type, instances):
  """
  Args:
    id_enum: Id or Kind
    id_type: Id_t or Kind_t
    instances: dictionary to mutate
  """
  for name in dir(id_enum):
    val = getattr(id_enum, name)
    if isinstance(val, id_type):
      instances[val.enum_id] = val


_ID_INSTANCES = {}  # int -> Id_t
_KIND_INSTANCES = {}  # int -> Kind_t

_CreateInstanceLookup(Id, Id_t, _ID_INSTANCES)
_CreateInstanceLookup(Kind, Kind_t, _KIND_INSTANCES)


_ID_TO_KIND_INTEGERS = {}  # int Id -> int Kind


def LookupKind(id_):
  """Id_t -> Kind_t"""
  return _KIND_INSTANCES[_ID_TO_KIND_INTEGERS[id_.enum_id]]


# Do NOT create any any more instances of Id.  Always used IdInstance().
def IdInstance(i):
  return _ID_INSTANCES[i]


#
# Instantiate osh/types.asdl
#

from _devbuild.gen import types_asdl  # other modules import this
              

# int -> bool_arg_type_e
BOOL_ARG_TYPES = {}  # type: dict

# Used by builtin_bracket.py
TEST_UNARY_LOOKUP = {}
TEST_BINARY_LOOKUP = {}
TEST_OTHER_LOOKUP = {}


#
# Add attributes to Id and Kind
#

ID_SPEC = id_kind.IdSpec(_ID_TO_KIND_INTEGERS, BOOL_ARG_TYPES)

id_kind.AddKinds(ID_SPEC)
id_kind.AddBoolKinds(ID_SPEC, types_asdl.bool_arg_type_e)  # must come second
id_kind.SetupTestBuiltin(ID_SPEC,
                         TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                         TEST_OTHER_LOOKUP,
                         types_asdl.bool_arg_type_e)

# Debug
_kind_sizes = ID_SPEC.kind_sizes


#
# Instantiate osh/osh.asdl
#

from _devbuild.gen import syntax_asdl  # other modules import this
_ = syntax_asdl  # shut up lint

#
# Instantiate core/runtime.asdl
#

from _devbuild.gen import runtime_asdl  # other modules import this
_ = runtime_asdl  # shut up lint

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

redir_arg_type_e = types_asdl.redir_arg_type_e

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
