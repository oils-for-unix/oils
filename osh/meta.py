#!/usr/bin/python
"""
meta.py

Another "thin waist" of the interpreter.  It can be happen at compile time!

We are following the code <-> data pattern, and this is the "data" module.
id_kind and ASDL are the code.

Usage:
  from osh.meta import Id, Kind, ast, ID_SPEC
"""

import sys

# These are metaprogramming libraries.  Everything can happen at compile time.
# Could move these to a dir like meta?  From meta import id_kind?  From meta
# import asdl?
from core import id_kind 
#from osh import ast_  # TODO: could be ast_lib?


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


_ID_TO_KIND = {}  # int -> Kind

def LookupKind(id_):
  return _ID_TO_KIND[id_.enum_value]


_ID_NAMES = {}  # int -> string

def IdName(id_):
  return _ID_NAMES[id_.enum_value]


# Keep one instance of each Id, to save memory and enable comparison by
# OBJECT IDENTITY.
# Do NOT create any any more instances of them!  Always used IdInstance().

# TODO: Fold this into ASDL, which will enforce this?

_ID_INSTANCES = {}  # int -> Id

def IdInstance(i):
  return _ID_INSTANCES[i]


# Id -> OperandType
BOOL_OPS = {}  # type: dict

# Used by test_builtin.py
TEST_UNARY_LOOKUP = {}
TEST_BINARY_LOOKUP = {}
TEST_OTHER_LOOKUP = {}



#
# Instantiate the spec
#


ID_SPEC = id_kind.IdSpec(Id, Kind,
                         _ID_NAMES, _ID_INSTANCES, _ID_TO_KIND,
                         BOOL_OPS)

id_kind._AddKinds(ID_SPEC)
id_kind._AddBoolKinds(ID_SPEC, Id)  # must come second
id_kind._SetupTestBuiltin(Id, Kind, ID_SPEC,
                          TEST_UNARY_LOOKUP, TEST_BINARY_LOOKUP,
                          TEST_OTHER_LOOKUP)

# Debug
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

    # descriptor
    Id.Redir_GreatAnd: 1,  # echo >&2  means echo 1>&2
    Id.Redir_LessAnd: 0,   # echo <&3 means echo 0<&3, I think

    Id.Redir_TLess: 0,  # here word

    # here docs included
    Id.Redir_DLess: 0,
    Id.Redir_DLessDash: 0,
}


def _InitRedirType():
  # To break circular import.  TODO: Id should really be metaprogrammed in the
  # same module!
  from osh import ast_ as ast
  redir_type_e = ast.redir_type_e

  return {
      # filename
      Id.Redir_Less: redir_type_e.Path,
      Id.Redir_Great: redir_type_e.Path,
      Id.Redir_DGreat: redir_type_e.Path,
      Id.Redir_Clobber: redir_type_e.Path,
      Id.Redir_LessGreat: redir_type_e.Path,

      # descriptor
      Id.Redir_GreatAnd: redir_type_e.Desc,
      Id.Redir_LessAnd: redir_type_e.Desc,

      Id.Redir_TLess: redir_type_e.Here,  # here word
      # note: here docs aren't included
  }
