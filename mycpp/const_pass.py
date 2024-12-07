"""
const_pass.py - AST pass that collects string constants.

Instead of emitting a dynamic allocation StrFromC("foo"), we emit a
GLOBAL_STR(str99, "foo"), and then a reference to str99.
"""
import collections
import json
import hashlib
import string

from mypy.nodes import (Expression, StrExpr, CallExpr)
from mypy.types import Type

from mycpp import format_strings
from mycpp import util
from mycpp.util import log
from mycpp import visitor

from typing import Dict, List, Tuple, Counter, TextIO, Union

_ = log

_ALPHABET = string.ascii_lowercase + string.ascii_uppercase
_ALPHABET = _ALPHABET[:32]

AllStrings = Dict[Union[int, StrExpr], str]  # Node -> raw string
UniqueStrings = Dict[bytes, str]  # SHA1 digest -> raw string
HashedStrings = Dict[str, List[str]]  # short hash -> raw string
VarNames = Dict[str, str]  # raw string -> variable name


class GlobalStrings:

    def __init__(self) -> None:
        # SHA1 hash -> encoded bytes
        self.all_strings: AllStrings = {}
        self.var_names: VarNames = {}

        # OLD
        self.unique: Dict[bytes, bytes] = {}
        self.int_id_lookup: Dict[Expression, str] = {}
        self.pairs: List[Tuple[str, str]] = []

    def Add(self, key: Union[int, StrExpr], s: str) -> None:
        """
        key: int for tests
             StrExpr node for production
        """
        self.all_strings[key] = s

    def ComputeStableVarNames(self) -> None:
        unique = _MakeUniqueStrings(self.all_strings)
        hash15 = _HashAndCollect(unique)
        self.var_names = _HandleCollisions(hash15)

    def GetVarName(self, node: StrExpr) -> str:
        # StrExpr -> str -> variable names
        return self.var_names[self.all_strings[node]]

    def WriteConstants(self, out_f: TextIO) -> None:
        if util.SMALL_STR:
            macro_name = 'GLOBAL_STR2'
        else:
            macro_name = 'GLOBAL_STR'

        # sort by the string value itself
        for raw_string in sorted(self.var_names):
            var_name = self.var_names[raw_string]
            out_f.write('%s(%s, %s);\n' %
                        (macro_name, var_name, json.dumps(raw_string)))

        out_f.write('\n')


class Collect(visitor.TypedVisitor):

    def __init__(self, types: Dict[Expression, Type],
                 global_strings: GlobalStrings) -> None:
        visitor.TypedVisitor.__init__(self, types)
        self.global_strings = global_strings

        # Only generate unique strings.
        # Before this optimization, _gen/bin/oils_for_unix.mycpp.cc went up to:
        #     "str2824"
        # After:
        #     "str1789"
        #
        # So it saved over 1000 strings.
        #
        # The C++ compiler should also optimize it, but it's easy for us to
        # generate less source code.

        # unique string value -> id
        self.unique: Dict[str, str] = {}
        self.unique_id = 0

    def oils_visit_format_expr(self, left: Expression,
                                 right: Expression) -> None:
        if isinstance(left, StrExpr):
            # Do NOT visit the left, because we write it literally
            pass
        else:
            self.accept(left)
        self.accept(right)

    def visit_str_expr(self, o: StrExpr) -> None:
        raw_string = format_strings.DecodeMyPyString(o.value)
        self.global_strings.Add(o, raw_string)

    def oils_visit_probe_call(self, o: CallExpr) -> None:
        # Don't generate constants for DTRACE_PROBE()
        pass

    def oils_visit_log_call(self, fmt: StrExpr,
                            args: List[Expression]) -> None:
        if len(args) == 0:
            self.accept(fmt)
            return

        # Don't generate a string constant for the format string, which is an
        # inlined C string, not a mycpp GC string
        for i, arg in enumerate(args):
            self.accept(arg)


def _MakeUniqueStrings(all_strings: AllStrings) -> UniqueStrings:
    """
    Given all the strings, make a smaller set of unique strings.
    """
    unique: UniqueStrings = {}
    for _, raw_string in all_strings.items():
        b = raw_string.encode('utf-8')
        h = hashlib.sha1(b).digest()
        #print(repr(h))

        if h in unique:
            # extremely unlikely
            assert unique[h] == raw_string, ("SHA1 hash collision! %r and %r" %
                                             (unique[h], b))
        unique[h] = raw_string
    return unique


def _ShortHash15(h: bytes) -> str:
    """
    Given a SHA1, create a 15 bit hash value.

    We use three base-(2**5) aka base-32 digits, encoded as letters.
    """
    bits16 = h[0] | h[1] << 8

    assert 0 <= bits16 < 2**16, bits16

    # 5 least significant bits
    d1 = bits16 & 0b11111
    bits16 >>= 5
    d2 = bits16 & 0b11111
    bits16 >>= 5
    d3 = bits16 & 0b11111
    bits16 >>= 5

    return _ALPHABET[d1] + _ALPHABET[d2] + _ALPHABET[d3]


def _HashAndCollect(unique: UniqueStrings) -> HashedStrings:
    """
    Use the short hash.
    """
    hash15 = collections.defaultdict(list)
    for sha1, b in unique.items():
        short_hash = _ShortHash15(sha1)
        hash15[short_hash].append(b)
    return hash15


def _SummarizeCollisions(hash15: HashedStrings) -> None:
    collisions: Counter[int] = collections.Counter()
    for short_hash, strs in hash15.items():
        n = len(strs)
        #if n > 1:
        if 0:
            print(short_hash)
            print(strs)
        collisions[n] += 1

    log('%10s %s', 'COUNT', 'ITEM')
    for item, count in collisions.most_common():
        log('%10d %s', count, item)


def _HandleCollisions(hash15: HashedStrings) -> VarNames:
    var_names: VarNames = {}
    for short_hash, bytes_list in hash15.items():
        bytes_list.sort()  # stable order, will bump some of the strings
        for i, b in enumerate(bytes_list):
            if i == 0:
                var_names[b] = 'S_%s' % short_hash
            else:
                var_names[b] = 'S_%s_%d' % (short_hash, i)
    return var_names


def HashDemo() -> None:
    import sys

    # 5 bits
    #_ALPHABET = _ALPHABET.replace('l', 'Z')  # use a nicer one?
    log('alpha %r', _ALPHABET)

    global_strings = GlobalStrings()

    all_lines = sys.stdin.readlines()
    for i, line in enumerate(all_lines):
        global_strings.Add(i, line.strip())

    unique = _MakeUniqueStrings(global_strings.all_strings)
    hash15 = _HashAndCollect(unique)
    var_names = _HandleCollisions(hash15)

    if 0:
        for b, var_name in var_names.items():
            if var_name[-1].isdigit():
                log('%r %r', var_name, b)
            #log('%r %r', var_name, b)

    log('Unique %d' % len(unique))
    log('hash15 %d' % len(hash15))

    _SummarizeCollisions(hash15)


if __name__ == '__main__':
    HashDemo()
