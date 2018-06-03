#!/usr/bin/python
"""
meta.py

Another "thin waist" of the interpreter.  It can be happen at compile time!

We are following the code <-> data pattern, and this is the "data" module.
id_kind and asdl are the "code" modules.

Usage:
  from osh.meta import Id, Kind, ast, ID_SPEC
"""

from asdl import py_meta
from asdl import asdl_ as asdl

from core import id_kind
from core import util


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


class Kind(object):
  """A coarser version of Id, used to make parsing decisions."""

  # TODO: The Kind type should be folded into ASDL.  It can't print itself,
  # which is inconsistent with Id.
  pass


class _AsdlModule(object):
  """Dummy object to copy attributes onto."""
  pass


_ID_TO_KIND = {}  # int -> Kind

def LookupKind(id_):
  return _ID_TO_KIND[id_.enum_value]


_ID_NAMES = {}  # int -> string

def IdName(id_):
  return _ID_NAMES[id_.enum_value]


# Keep one instance of each Id, to save memory and enable comparison by
# OBJECT IDENTITY.
# Do NOT create any any more instances of them!  Always used IdInstance().

# TODO: Fold Id into ASDL, which will enforce uniqueness?

_ID_INSTANCES = {}  # int -> Id

def IdInstance(i):
  return _ID_INSTANCES[i]


#
# Instantiate osh/types.asdl
#

f = util.GetResourceLoader().open('osh/types.asdl')
_asdl_module, _type_lookup = asdl.LoadSchema(f, {})  # no app_types

types = _AsdlModule()
if 0:
  py_meta.MakeTypes(_asdl_module, types, _type_lookup)
else:
  # Exported for the generated code to use
  TYPES_TYPE_LOOKUP = _type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import types_asdl
  py_meta.AssignTypes(types_asdl, types)

f.close()


# Id -> bool_arg_type_e
BOOL_ARG_TYPES = {}  # type: dict

# Used by test_builtin.py
TEST_UNARY_LOOKUP = {}
TEST_BINARY_LOOKUP = {}
TEST_OTHER_LOOKUP = {}


#
# Instantiate the spec
#

ID_SPEC = id_kind.IdSpec(Id, Kind,
                         _ID_NAMES, _ID_INSTANCES, _ID_TO_KIND,
                         BOOL_ARG_TYPES)

id_kind.AddKinds(ID_SPEC)
id_kind.AddBoolKinds(ID_SPEC, Id, types.bool_arg_type_e)  # must come second
id_kind.SetupTestBuiltin(Id, Kind, ID_SPEC,
                         TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                         TEST_OTHER_LOOKUP,
                         types.bool_arg_type_e)

# Debug
_kind_sizes = ID_SPEC.kind_sizes


APP_TYPES = {'id': asdl.UserType(Id)}

#
# Instantiate osh/osh.asdl
#

f = util.GetResourceLoader().open('osh/osh.asdl')
_asdl_module, _type_lookup = asdl.LoadSchema(f, APP_TYPES)

ast = _AsdlModule()
if 0:
  py_meta.MakeTypes(_asdl_module, ast, _type_lookup)
else:
  # Exported for the generated code to use
  OSH_TYPE_LOOKUP = _type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import osh_asdl
  py_meta.AssignTypes(osh_asdl, ast)

f.close()

#
# Instantiate osh/glob.asdl
#

f = util.GetResourceLoader().open('osh/glob.asdl')
_asdl_module, _type_lookup = asdl.LoadSchema(f, APP_TYPES)

glob = _AsdlModule()
if 0:
  py_meta.MakeTypes(_asdl_module, glob, _type_lookup)
else:
  # Exported for the generated code to use
  GLOB_TYPE_LOOKUP = _type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import glob_asdl
  py_meta.AssignTypes(glob_asdl, glob)

f.close()

#
# Instantiate core/runtime.asdl
#

f = util.GetResourceLoader().open('core/runtime.asdl')
_asdl_module, _type_lookup = asdl.LoadSchema(f, APP_TYPES)

runtime = _AsdlModule()
if 0:
  py_meta.MakeTypes(_asdl_module, runtime, _type_lookup)
else:
  # Exported for the generated code to use
  RUNTIME_TYPE_LOOKUP = _type_lookup

  # Get the types from elsewhere
  from _devbuild.gen import runtime_asdl
  py_meta.AssignTypes(runtime_asdl, runtime)

f.close()

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

redir_arg_type_e = types.redir_arg_type_e

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
