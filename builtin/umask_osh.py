#!/usr/bin/env python2
"""
umask_osh.py - Implements the umask builtin, including parsing
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value
from core import vm
from frontend import flag_util
from mycpp.mylib import print_stderr

import posix_ as posix

from typing import List, Tuple

_WHO = "ugoa"
_OP = "+-="
_PERM_U_PERMCOPY = "rwxXstugo"

# NOTE: bitsets are a great way to store fixed width sets & add / remove
# items easily. Thus, we use different bitsets for $wholist, $permlist,
# $perm, and $mask.


def _WhoCharToBitset(who_ch):
    # type: (str) -> int
    if who_ch == "u":
        return 0o4
    elif who_ch == "g":
        return 0o2
    elif who_ch == "o":
        return 0o1
    elif who_ch == "a":
        return 0o7
    else:
        assert False, "unreachable"
        return 0o0


def _PermlistCharToBitset(permlist_ch):
    # type: (str) -> int
    if permlist_ch == "r":
        return 0o400
    elif permlist_ch == "w":
        return 0o200
    elif permlist_ch == "x":
        return 0o100
    elif permlist_ch == "X":
        return 0o040
    elif permlist_ch == "s":
        return 0o020
    elif permlist_ch == "t":
        return 0o010
    elif permlist_ch == "u":
        return 0o004
    elif permlist_ch == "g":
        return 0o002
    elif permlist_ch == "o":
        return 0o001
    else:
        assert False, "unreachable"
        return 0o0


# perm = [rwx][Xst][ugo]
def _PermlistToBits(permlist, initial_mask):
    # type: (int, int) -> int
    perm = 0o0
    if (permlist & 0o400) != 0:
        perm |= 0o4  # r
    if (permlist & 0o200) != 0:
        perm |= 0o2  # w
    if (permlist & 0o100) != 0:
        perm |= 0o1  # x
    if (permlist & 0o040) != 0 and (initial_mask & 0o111) != 0:
        # X == x iff one of the execute bits are set on the mask
        perm |= 0o1  # X
    if (permlist & 0o020) != 0:
        # does nothing b/c umask ignores the set-on-execution bits
        perm |= 0o0  # s
    if (permlist & 0o010) != 0:
        # also does nothing
        perm |= 0o0  # t
    if (permlist & 0o4) != 0:
        perm |= (~initial_mask & 0o700) >> 6  # u
    if (permlist & 0o2) != 0:
        perm |= (~initial_mask & 0o070) >> 3  # g
    if (permlist & 0o1) != 0:
        perm |= (~initial_mask & 0o007) >> 0  # o
    return perm


def _SetMask(wholist, perm, mask):
    # type: (int, int, int) -> int
    if (wholist & 0o4) != 0:
        mask |= perm << 6
    if (wholist & 0o2) != 0:
        mask |= perm << 3
    if (wholist & 0o1) != 0:
        mask |= perm << 0
    return mask


# can these be done with |= ?
def _ClearMask(wholist, perm, mask):
    # type: (int, int, int) -> int
    if (wholist & 0o4) != 0:
        mask &= 0o777 - (perm << 6)
    if (wholist & 0o2) != 0:
        mask &= 0o777 - (perm << 3)
    if (wholist & 0o1) != 0:
        mask &= 0o777 - (perm << 0)
    return mask


class SymbolicClauseParser:

    def __init__(self, clause):
        # type: (str) -> None
        self.clause = clause
        self.i = 0

    def AtEnd(self):
        # type: () -> bool
        return self.i >= len(self.clause)

    def Ch(self):
        # type: () -> str
        return self.clause[self.i]

    def ParseWholist(self):
        # type: () -> int
        if self.Ch() not in _WHO:
            return 0o7

        wholist = 0o0
        while not self.AtEnd():
            if self.Ch() not in _WHO:
                break

            wholist |= _WhoCharToBitset(self.Ch())
            self.i += 1

        return wholist

    # An actionlist is a sequence of actions. An action always starts with an op.
    # returns success
    def ParseNextAction(self, wholist, mask, initial_mask):
        # type: (int, int, int) -> Tuple[bool, int]

        op = self.Ch()
        if op not in _OP:
            print_stderr(
                "oils warning: expected one of `%s` at start of action instead of `%s`"
                % (_OP, op))
            return False, 0

        self.i += 1

        if op == "=":
            mask = _SetMask(wholist, 0o7, mask)

        if self.AtEnd() or self.Ch() not in _PERM_U_PERMCOPY:
            if op == "+" or op == "=":
                return True, mask
            elif op == "-":
                return True, mask

        # perm represents the bits [rwx] for a single permission
        perm = 0o0

        # permlist = [rwx][Xst][ugo]
        permlist = 0o000
        while not (self.AtEnd() or self.Ch() in _OP):
            # While a list of permcopy chars mixed with permlist is not posix, both dash and mksh
            # support it.
            if self.Ch() not in _PERM_U_PERMCOPY:
                print_stderr(
                    "oil warning: expected one of `%s` in permlist instead of `%s`"
                    % (_PERM_U_PERMCOPY, self.Ch()))
                return False, 0

            permlist |= _PermlistCharToBitset(self.Ch())
            self.i += 1

        perm = _PermlistToBits(permlist, initial_mask)

        if op == "+" or op == "=":
            return True, _ClearMask(wholist, perm, mask)
        elif op == "-":
            return True, _SetMask(wholist, perm, mask)

        assert False, "unreachable"
        return False, 0


def _ParseClause(mask, initial_mask, clause):
    # type: (int, int, str) -> Tuple[bool, int]
    if len(clause) == 0:
        # TODO: location highlighting would be nice
        print_stderr(
            "oils warning: symbolic mode operator cannot be empty")
        return False, 0

    parser = SymbolicClauseParser(clause)
    wholist = parser.ParseWholist()
    if parser.AtEnd():
        print_stderr("oils warning: actionlist is required")
        return False, 0

    while True:
        ok, mask = parser.ParseNextAction(wholist, mask, initial_mask)
        if not ok:
            return False, 0
        elif parser.AtEnd():
            return True, mask


def _ParseClauseList(initial_mask, clause_list):
    # type: (int, List[str]) -> Tuple[bool, int]
    mask = initial_mask
    for clause in clause_list:
        ok, mask = _ParseClause(mask, initial_mask, clause)
        if not ok:
            return False, 0

    return True, mask


class Umask(vm._Builtin):

    def __init__(self):
        # type: () -> None
        """Dummy constructor for mycpp."""
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        # see https://pubs.opengroup.org/onlinepubs/009696899/utilities/chmod.html for more details

        attrs, arg_r = flag_util.ParseCmdVal('umask', cmd_val)

        if arg_r.AtEnd():  # no args
            # umask() has a dumb API: to get the umask, we must modify it
            # see: https://man7.org/linux/man-pages/man2/umask.2.html
            # NOTE: dash disables interrupts around the two umask() calls, but that
            # shouldn't be a concern for us.  Signal handlers won't call umask().
            mask = posix.umask(0)
            posix.umask(mask)
            print('0%03o' % mask)  # octal format
            return 0

        first_arg, first_loc = arg_r.ReadRequired2('expected an argument')
        arg_r.Done()  # only one arg

        if first_arg[0].isdigit():
            try:
                new_mask = int(first_arg, 8)
            except ValueError:
                # NOTE: This also happens when we have '8' or '9' in the input.
                print_stderr("oils warning: `%s` is not an octal number" %
                             first_arg)
                return 1

            posix.umask(new_mask)
            return 0

        # NOTE: it's possible to avoid this extra syscall in cases where we don't care about
        # the initial value (ex: umask ...,a=rwx) although it's non-trivial to determine
        # when, so it's probably not worth it
        initial_mask = posix.umask(0)
        try:
            ok, new_mask = _ParseClauseList(initial_mask, first_arg.split(","))
            if not ok:
                posix.umask(initial_mask)
                return 1

            posix.umask(new_mask)
            return 0

        except Exception as e:
            # this guard protects the umask value against any accidental exceptions
            posix.umask(initial_mask)
            raise
