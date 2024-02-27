"""
flag_util.py - API for builtin commands
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import ArgList
from core.error import e_usage
from frontend import args
from frontend import flag_spec
from mycpp import mylib

from typing import Tuple, Optional

if mylib.PYTHON:

    def LookupFlagSpec(name):
        # type: (str) -> flag_spec._FlagSpec
        return flag_spec.FLAG_SPEC[name]

    def LookupFlagSpec2(name):
        # type: (str) -> flag_spec._FlagSpecAndMore
        return flag_spec.FLAG_SPEC_AND_MORE[name]


def _DoesNotAccept(arg_list):
    # type: (Optional[ArgList]) -> None
    """ Copy from frontend/typed_args.py, to break dependency """
    if arg_list is not None:
        e_usage('got unexpected typed args', arg_list.left)


def ParseCmdVal(spec_name, cmd_val, accept_typed_args=False):
    # type: (str, cmd_value.Argv, bool) -> Tuple[args._Attributes, args.Reader]

    if not accept_typed_args:
        _DoesNotAccept(cmd_val.typed_args)

    arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
    arg_r.Next()  # move past the builtin name

    spec = LookupFlagSpec(spec_name)
    return args.Parse(spec, arg_r), arg_r


def ParseLikeEcho(spec_name, cmd_val):
    # type: (str, cmd_value.Argv) -> Tuple[args._Attributes, args.Reader]

    _DoesNotAccept(cmd_val.typed_args)

    arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
    arg_r.Next()  # move past the builtin name

    spec = LookupFlagSpec(spec_name)
    return args.ParseLikeEcho(spec, arg_r), arg_r


def Parse(spec_name, arg_r):
    # type: (str, args.Reader) -> args._Attributes
    """Parse argv using a given FlagSpec."""
    spec = LookupFlagSpec(spec_name)
    return args.Parse(spec, arg_r)


def ParseMore(spec_name, arg_r):
    # type: (str, args.Reader) -> args._Attributes
    """Parse argv using a given FlagSpecAndMore."""
    spec = LookupFlagSpec2(spec_name)
    return args.ParseMore(spec, arg_r)
