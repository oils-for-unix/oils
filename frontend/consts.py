#!/usr/bin/env python2
"""
lookup.py
"""
from __future__ import print_function

from _devbuild.gen.types_asdl import (
    redir_arg_type_e, redir_arg_type_t, bool_arg_type_t
)
from _devbuild.gen.id_kind_asdl import Id, Id_t, Kind_t
from frontend import builtin_def
from frontend import option_def 

from typing import Tuple, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.option_asdl import builtin_t


NO_INDEX = 0  # for Resolve


# Used as consts::STRICT_ALL, etc.  Do it explicitly to satisfy MyPy.
STRICT_ALL = option_def.STRICT_ALL
OIL_BASIC = option_def.OIL_BASIC
OIL_ALL = option_def.OIL_ALL
DEFAULT_TRUE = option_def.DEFAULT_TRUE

# TODO: These could be changed to numbers
SET_OPTION_NAMES = option_def.SET_OPTION_NAMES
SHOPT_OPTION_NAMES = option_def.SHOPT_OPTION_NAMES
VISIBLE_SHOPT_NAMES = option_def.VISIBLE_SHOPT_NAMES
PARSE_OPTION_NAMES = option_def.PARSE_OPTION_NAMES

BUILTIN_NAMES = builtin_def.BUILTIN_NAMES


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


#
# Builtins
#


_BUILTIN_DICT = builtin_def.BuiltinDict()

def LookupSpecialBuiltin(argv0):
  # type: (str) -> builtin_t
  """Is it a special builtin?"""
  b = _BUILTIN_DICT.get(argv0)
  if b and b.kind == 'special':
    return b.index
  else:
    return NO_INDEX


def LookupAssignBuiltin(argv0):
  # type: (str) -> builtin_t
  """Is it an assignment builtin?"""
  b = _BUILTIN_DICT.get(argv0)
  if b and b.kind == 'assign':
    return b.index
  else:
    return NO_INDEX


def LookupNormalBuiltin(argv0):
  # type: (str) -> builtin_t
  """Is it any other builtin?"""
  b = _BUILTIN_DICT.get(argv0)
  if b and b.kind == 'normal':
    return b.index
  else:
    return NO_INDEX


#
# Constants used by osh/split.py
#

# IFS splitting is complicated in general.  We handle it with three concepts:
#
# - CH.* - Kinds of characters (edge labels)
# - ST.* - States (node labels)
# - EMIT.*  Actions
#
# The Split() loop below classifies characters, follows state transitions, and
# emits spans.  A span is a (ignored Bool, end_index Int) pair.

# As an example, consider this string:
# 'a _ b'
#
# The character classes are:
#
# a      ' '        _        ' '        b
# Black  DE_White   DE_Gray  DE_White   Black
#
# The states are:
#
# a      ' '        _        ' '        b
# Black  DE_White1  DE_Gray  DE_White2  Black
#
# DE_White2 is whitespace that follows a "gray" non-whitespace IFS character.
#
# The spans emitted are:
#
# (part 'a', ignored ' _ ', part 'b')

# SplitForRead() will check if the last two spans are a \ and \\n.  Easy.


# Shorter names for state machine enums
from _devbuild.gen.runtime_asdl import state_t, emit_t, char_kind_t
from _devbuild.gen.runtime_asdl import emit_e as EMIT
from _devbuild.gen.runtime_asdl import char_kind_e as CH
from _devbuild.gen.runtime_asdl import state_e as ST

_IFS_EDGES = {
    # Whitespace should have been stripped
    (ST.Start, CH.DE_White):  (ST.Invalid,   EMIT.Nothing),      # ' '
    (ST.Start, CH.DE_Gray):   (ST.DE_Gray,   EMIT.Empty),        # '_'
    (ST.Start, CH.Black):     (ST.Black,     EMIT.Nothing),      # 'a'
    (ST.Start, CH.Backslash): (ST.Backslash, EMIT.Nothing),      # '\'
    (ST.Start, CH.Sentinel):  (ST.Done,      EMIT.Nothing),      # ''

    (ST.DE_White1, CH.DE_White):  (ST.DE_White1, EMIT.Nothing),  # '  '
    (ST.DE_White1, CH.DE_Gray):   (ST.DE_Gray,   EMIT.Nothing),  # ' _'
    (ST.DE_White1, CH.Black):     (ST.Black,     EMIT.Delim),    # ' a'
    (ST.DE_White1, CH.Backslash): (ST.Backslash, EMIT.Delim),    # ' \'
    # Ignore trailing IFS whitespace too.  This is necessary for the case:
    # IFS=':' ; read x y z <<< 'a : b : c :'.
    (ST.DE_White1, CH.Sentinel):  (ST.Done,      EMIT.Nothing),  # 'zz '

    (ST.DE_Gray, CH.DE_White):  (ST.DE_White2, EMIT.Nothing),    # '_ '
    (ST.DE_Gray, CH.DE_Gray):   (ST.DE_Gray,   EMIT.Empty),      # '__'
    (ST.DE_Gray, CH.Black):     (ST.Black,     EMIT.Delim),      # '_a'
    (ST.DE_Gray, CH.Backslash): (ST.Black,     EMIT.Delim),      # '_\'
    (ST.DE_Gray, CH.Sentinel):  (ST.Done,      EMIT.Delim),   # 'zz:' IFS=': '

    (ST.DE_White2, CH.DE_White):  (ST.DE_White2, EMIT.Nothing),  # '_  '
    (ST.DE_White2, CH.DE_Gray):   (ST.DE_Gray,   EMIT.Empty),    # '_ _'
    (ST.DE_White2, CH.Black):     (ST.Black,     EMIT.Delim),    # '_ a'
    (ST.DE_White2, CH.Backslash): (ST.Backslash, EMIT.Delim),    # '_ \'
    (ST.DE_White2, CH.Sentinel):  (ST.Done,      EMIT.Delim), # 'zz: ' IFS=': '

    (ST.Black, CH.DE_White):  (ST.DE_White1, EMIT.Part),         # 'a '
    (ST.Black, CH.DE_Gray):   (ST.DE_Gray,   EMIT.Part),         # 'a_'
    (ST.Black, CH.Black):     (ST.Black,     EMIT.Nothing),      # 'aa'
    (ST.Black, CH.Backslash): (ST.Backslash, EMIT.Part),         # 'a\'
    (ST.Black, CH.Sentinel):  (ST.Done,      EMIT.Part),         # 'zz' IFS=': '

    # Here we emit an ignored \ and the second character as well.
    # We're emitting TWO spans here; we don't wait until the subsequent
    # character.  That is OK.
    #
    # Problem: if '\ ' is the last one, we don't want to emit a trailing span?
    # In all other cases we do.

    (ST.Backslash, CH.DE_White):  (ST.Black,     EMIT.Escape),   # '\ '
    (ST.Backslash, CH.DE_Gray):   (ST.Black,     EMIT.Escape),   # '\_'
    (ST.Backslash, CH.Black):     (ST.Black,     EMIT.Escape),   # '\a'
    # NOTE: second character is a backslash, but new state is ST.Black!
    (ST.Backslash, CH.Backslash): (ST.Black,     EMIT.Escape),   # '\\'
    (ST.Backslash, CH.Sentinel):  (ST.Done,      EMIT.Escape),   # 'zz\'
}


def IfsEdge(state, ch):
  # type: (state_t, char_kind_t) -> Tuple[state_t, emit_t]
  """Follow edges of the IFS state machine."""
  return _IFS_EDGES[state, ch]
