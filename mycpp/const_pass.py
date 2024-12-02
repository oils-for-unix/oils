"""
const_pass.py - AST pass that collects string constants.

Instead of emitting a dynamic allocation StrFromC("foo"), we emit a
GLOBAL_STR(str99, "foo"), and then a reference to str99.
"""
import collections
import string

from mypy.nodes import (Expression, StrExpr, CallExpr, NameExpr)

from mycpp import format_strings
from mycpp.util import log
from mycpp import visitor

from typing import Dict, List, Tuple, Iterator, Counter

_ = log

_ALPHABET = string.ascii_lowercase + string.ascii_uppercase
_ALPHABET = _ALPHABET[:32]


class Collect(visitor.SimpleVisitor):

    def __init__(self, const_lookup: Dict[Expression, str],
                 global_strings: List[Tuple[str, str]]) -> None:
        visitor.SimpleVisitor.__init__(self)
        self.const_lookup = const_lookup
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

    def visit_str_expr(self, o: StrExpr) -> None:
        str_val = o.value

        # Optimization to save code
        str_id = self.unique.get(str_val)
        if str_id is None:
            str_id = 'str%d' % self.unique_id
            self.unique_id += 1

            self.unique[str_val] = str_id

            raw_string = format_strings.DecodeMyPyString(str_val)
            self.global_strings.append((str_id, raw_string))

        # Different nodes can refer to the same string ID
        self.const_lookup[o] = str_id

    def visit_call_expr(self, o: CallExpr) -> None:
        # Don't generate constants for probe names
        if isinstance(o.callee, NameExpr) and o.callee.name == 'probe':
            return

        self.accept(o.callee)  # could be f() or obj.method()

        # This is what the SimpleVisitor superclass does
        for arg in o.args:
            self.accept(arg)


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


def _CollectHashes(unique: Dict[bytes, bytes]) -> Dict[str, List[bytes]]:
    import pprint

    hash15 = collections.defaultdict(list)

    for h, the_string in unique.items():
        if 0:
            pprint.pprint(h)
            pprint.pprint(the_string)
            print('')

        short_hash = _ShortHash15(h)
        hash15[short_hash].append(the_string)
    return hash15


def _SummarizeCollisions(hash15: Dict[str, List[bytes]]) -> None:
    collisions: Counter[int] = collections.Counter()
    for short_hash, strs in hash15.items():
        n = len(strs)
        #if n > 1:
        if 0:
            print(short_hash)
            print(strs)
        collisions[n] += 1

    log('COUNT ITEM')
    for item, count in collisions.most_common():
        log('%10d %s', count, item)


def _ResolveCollisions(
        hash15: Dict[str, List[bytes]]) -> Iterator[Tuple[str, bytes]]:
    for short_hash, strs in hash15.items():
        strs.sort()
        for i, s in enumerate(strs):
            if i == 0:
                yield 'S_%s' % short_hash, s
            else:
                yield 'S_%s_%d' % (short_hash, i), s


def HashDemo() -> None:
    import hashlib
    import sys

    # 5 bits
    #_ALPHABET = _ALPHABET.replace('l', 'Z')  # use a nicer one?
    log('alpha %r', _ALPHABET)

    unique: Dict[bytes, bytes] = {}
    for line in sys.stdin:
        b = line.strip().encode('utf-8')
        h = hashlib.sha1(b).digest()
        #print(repr(h))

        if h in unique:
            # extremely unlikely
            assert unique[h] == b, ("SHA1 hash collision! %r and %r" %
                                    (unique[h], b))
        unique[h] = b

    hash15 = _CollectHashes(unique)

    if 0:
        for var_name, s in _ResolveCollisions(hash15):
            if var_name[-1].isdigit():
                log('%r %r', var_name, s)

    log('Unique %d' % len(unique))
    log('hash15 %d' % len(hash15))

    _SummarizeCollisions(hash15)


if __name__ == '__main__':
    HashDemo()
