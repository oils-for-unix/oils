#!/usr/bin/env python2
"""
lookup.py
"""
from __future__ import print_function

from _devbuild.gen.types_asdl import (
    redir_arg_type_e, redir_arg_type_t, bool_arg_type_t
)
from _devbuild.gen.id_kind_asdl import Id, Id_t, Kind_t
from frontend import option_def 


# Used as consts::STRICT_ALL, etc.  Do it explicitly to satisfy MyPy.
STRICT_ALL = option_def.STRICT_ALL
OIL_BASIC = option_def.OIL_BASIC
OIL_ALL = option_def.OIL_ALL

# TODO: These could be changed to numbers
SET_OPTION_NAMES = option_def.SET_OPTION_NAMES
SHOPT_OPTION_NAMES = option_def.SHOPT_OPTION_NAMES
VISIBLE_SHOPT_NAMES = option_def.VISIBLE_SHOPT_NAMES
PARSE_OPTION_NAMES = option_def.PARSE_OPTION_NAMES


def GetKind(id_):
  # type: (Id_t) -> Kind_t
  """To make coarse-grained parsing decisions."""

  from _devbuild.gen.id_kind import ID_TO_KIND  # break circular dep
  return ID_TO_KIND[id_]


def BoolArgType(id_):
  # type: (Id_t) -> bool_arg_type_t

  from _devbuild.gen.id_kind import BOOL_ARG_TYPES  # break circular dep
  return BOOL_ARG_TYPES[id_]


#
# Redirect Tables associated with IDs
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


def RedirArgType(id_):
  # type: (Id_t) -> redir_arg_type_t
  return REDIR_ARG_TYPES[id_]


def RedirDefaultFd(id_):
  # type: (Id_t) -> int
  return REDIR_DEFAULT_FD[id_]
