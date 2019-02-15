#!/usr/bin/python
"""
meta.py

Another "thin waist" of the interpreter.  It can be happen at compile time!

We are following the code <-> data pattern, and this is the "data" module.
id_kind and asdl are the "code" modules.

Usage:
  from core.meta import syntax_asdl, Id, Kind, ID_SPEC
"""

import posix

from core import id_kind


_BOOTSTRAP_LEVEL = int(posix.environ.get('BOOTSTRAP_LEVEL', '1'))


# TODO: Should be py_meta.SimpleObj (or asdl_runtime.SimpleObj)
class Id(object):
  """Token and op type.

  The evaluator must consider all Ids.

  NOTE: We add a bunch of class attributes that are INSTANCES of this class,
  e.g. Id.Lit_Chars.
  """
  def __init__(self, enum_value):
    self.enum_value = enum_value

  def __repr__(self):
    return IdName(self)


# TODO: Should be py_meta.SimpleObj (or asdl_runtime.SimpleObj).  Right now it
# can't print itself, which is inconsistent with Id.
class Kind(object):
  """A coarser version of Id, used to make parsing decisions."""
  pass


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



_ASDL = False
#_ASDL = True


_ID_TO_KIND_INTEGERS = {}  # int Id -> int Kind

def LookupKind(id_):
  return _ID_TO_KIND_INTEGERS[id_.enum_value]

_ID_NAMES = {}  # int -> string

def IdName(id_):
  return _ID_NAMES[id_.enum_value]


# HACK.  Kind needs to be part of ASDL.
def KindName(kind_int):
  for name in dir(Kind):
    if name.startswith('__'):
      continue
    val = getattr(Kind, name)
    if val == kind_int:
      return name
  return '<Invalid Kind>'


# Keep one instance of each Id, to save memory and enable comparison by
# OBJECT IDENTITY.
# Do NOT create any any more instances of them!  Always used IdInstance().

# TODO: Fold Id into ASDL, which will enforce uniqueness?


_ID_INSTANCES = {}  # int -> Id_t
_KIND_INSTANCES = {}  # int -> Kind_t

if _ASDL:
  _CreateInstanceLookup(Id, Id_t, _ID_INSTANCES)
  _CreateInstanceLookup(Kind, Kind_t, _KIND_INSTANCES)

  def IdName(id_):
    return id_.name

  def KindName(k):
    return k.name

  def LookupKind(id_):
    """Id_t -> Kind_t"""
    return _KIND_INSTANCES[_ID_TO_KIND_INTEGERS[id_.enum_id]]


def IdInstance(i):
  return _ID_INSTANCES[i]


#
# Instantiate osh/types.asdl
#

from _devbuild.gen import types_asdl  # other modules import this
              


# Id -> bool_arg_type_e
BOOL_ARG_TYPES = {}  # type: dict

# Used by builtin_bracket.py
TEST_UNARY_LOOKUP = {}
TEST_BINARY_LOOKUP = {}
TEST_OTHER_LOOKUP = {}


#
# Add attributes to Id and Kind
#

ID_SPEC = id_kind.IdSpec(Id, Kind,
                         _ID_NAMES, _ID_INSTANCES, _ID_TO_KIND_INTEGERS,
                         BOOL_ARG_TYPES)

id_kind.AddKinds(ID_SPEC)
id_kind.AddBoolKinds(ID_SPEC, Id, types_asdl.bool_arg_type_e)  # must come second
# NOTE: Dependency on the types module here.  This is the root cause of the
# _BOOTSTRAP_LEVEL hack.
id_kind.SetupTestBuiltin(Id, Kind, ID_SPEC,
                         TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                         TEST_OTHER_LOOKUP,
                         types_asdl.bool_arg_type_e)

# Debug
_kind_sizes = ID_SPEC.kind_sizes


#
# Instantiate osh/osh.asdl
#

if _BOOTSTRAP_LEVEL > 0:
  from _devbuild.gen import syntax_asdl  # other modules import this
  _ = syntax_asdl  # shut up lint

#
# Instantiate core/runtime.asdl
#

if _BOOTSTRAP_LEVEL > 0:
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
