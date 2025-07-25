"""
mylib.py: Python stubs/interfaces that are reimplemented in C++, not directly
translated.
"""
from __future__ import print_function

try:
    import cStringIO
except ImportError:
    # Python 3 doesn't have cStringIO.  Our yaks/ demo currently uses
    # mycpp/mylib.py with Python 3.
    cStringIO = None
    import io

import math
import sys

from pylib import collections_
try:
    import posix_ as posix
except ImportError:
    # Hack for tangled dependencies.
    import os
    posix = os

from typing import (Tuple, List, Dict, Optional, Iterator, Any, TypeVar,
                    Generic, cast, TYPE_CHECKING)
if TYPE_CHECKING:
    from mycpp import mops

# For conditional translation
CPP = False
PYTHON = True

# Use POSIX name directly
STDIN_FILENO = 0


# Avoid name conflicts with C Macros
def isinf_(x):
    # type: (float) -> bool
    return math.isinf(x)


def isnan_(x):
    # type: (float) -> bool
    return math.isnan(x)


def MaybeCollect():
    # type: () -> None
    pass


def PrintGcStats():
    # type: () -> None
    pass


def NewDict():
    # type: () -> Dict[str, Any]
    """Make dictionaries ordered in Python, e.g. for JSON.
  
    In C++, our Dict implementation should be ordered.
    """
    return collections_.OrderedDict()


def log(msg, *args):
    # type: (str, *Any) -> None
    """Print debug output to stderr."""
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


def print_stderr(s):
    # type: (str) -> None
    """Print a message to stderr for the user.

    This should be used sparingly, since it doesn't have location info, like
    ui.ErrorFormatter does.  We use it to print fatal I/O errors that were only
    caught at the top level.
    """
    print(s, file=sys.stderr)


#
# Byte Operations avoid excessive allocations with string algorithms
#


def ByteAt(s, i):
    # type: (str, int) -> int
    """i must be in bounds."""

    # This simplifies the C++ implementation
    assert 0 <= i, 'No negative indices'
    assert i < len(s), 'No negative indices'

    return ord(s[i])


def ByteEquals(byte, ch):
    # type: (int,  str) -> bool
    assert len(ch) == 1, ch
    assert 0 <= byte < 256, byte

    return byte == ord(ch)


def ByteInSet(byte, byte_set):
    # type: (int, str) -> bool
    assert 0 <= byte < 256, byte

    return chr(byte) in byte_set


def JoinBytes(byte_list):
    # type: (List[int]) -> str

    return ''.join(chr(b) for b in byte_list)


#
# For BashArray
#


def BigIntSort(keys):
    # type: (List[mops.BigInt]) -> None
    keys.sort(key=lambda big: big.i)


#
# Files
#


class LineReader:

    def readline(self):
        # type: () -> str
        raise NotImplementedError()

    def close(self):
        # type: () -> None
        raise NotImplementedError()

    def isatty(self):
        # type: () -> bool
        raise NotImplementedError()


if TYPE_CHECKING:

    class BufLineReader(LineReader):

        def __init__(self, s):
            # type: (str) -> None
            raise NotImplementedError()

    def open(path):
        # type: (str) -> LineReader

        # TODO: should probably return mylib.File
        # mylib.open() is currently only used in yaks/yaks_main and
        # bin.osh_parse
        raise NotImplementedError()

else:
    # Actual runtime
    if cStringIO:
        BufLineReader = cStringIO.StringIO
    else:  # Python 3
        BufLineReader = io.StringIO

    open = open


class Writer:

    def write(self, s):
        # type: (str) -> None
        raise NotImplementedError()

    def flush(self):
        # type: () -> None
        raise NotImplementedError()

    def isatty(self):
        # type: () -> bool
        raise NotImplementedError()

    def close(self):
        # type: () -> None
        raise NotImplementedError()


class BufWriter(Writer):
    """Mimic StringIO API, but add clear() so we can reuse objects.

    We can also add accelerators for directly writing numbers, to avoid
    allocations when encoding JSON.
    """

    def __init__(self):
        # type: () -> None
        self.parts = []

    def write(self, s):
        # type: (str) -> None
        self.parts.append(s)

    def isatty(self):
        # type: () -> bool
        return False

    def write_spaces(self, n):
        # type: (int) -> None
        """For JSON indenting.  Avoid intermediate allocations in C++."""
        self.parts.append(' ' * n)

    def getvalue(self):
        # type: () -> str
        return ''.join(self.parts)

    def clear(self):
        # type: () -> None
        del self.parts[:]

    def close(self):
        # type: () -> None

        # No-op for now - we could invalidate write()?
        pass


def Stdout():
    # type: () -> Writer
    return sys.stdout


def Stderr():
    # type: () -> Writer
    return sys.stderr


def Stdin():
    # type: () -> LineReader
    return sys.stdin


class switch(object):
    """Translates to C switch on int.

    with switch(i) as case:
        if case(42, 43):
            print('hi')
        elif case(99):
            print('two')
        else:
            print('neither')
    """

    def __init__(self, value):
        # type: (int) -> None
        self.value = value

    def __enter__(self):
        # type: () -> switch
        return self

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> bool
        return False  # Allows a traceback to occur

    def __call__(self, *cases):
        # type: (*Any) -> bool
        return self.value in cases


class str_switch(object):
    """Translates to fast dispatch on string length, then memcmp()."""

    def __init__(self, value):
        # type: (str) -> None
        self.value = value

    def __enter__(self):
        # type: () -> switch
        return self

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> bool
        return False  # Allows a traceback to occur

    def __call__(self, *cases):
        # type: (*Any) -> bool
        return self.value in cases


class tagswitch(object):
    """Translates to C switch(node->tag())"""

    def __init__(self, node):
        # type: (Any) -> None
        self.tag = node.tag()

    def __enter__(self):
        # type: () -> tagswitch
        return self

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> bool
        return False  # Allows a traceback to occur

    def __call__(self, *cases):
        # type: (*Any) -> bool
        return self.tag in cases


if TYPE_CHECKING:
    # Doesn't work
    T = TypeVar('T')

    class StackArray(Generic[T]):

        def __init__(self):
            self.items = []  # type: List[T]

        def append(self, item):
            # type: (T) -> None
            self.items.append(item)

        def pop(self):
            # type: () -> T
            return self.items.pop()

    # Doesn't work, this is only for primitive types
    #StackArray = NewType('StackArray', list)


def MakeStackArray(item_type):
    # type: (TypeVar) -> StackArray[item_type]
    """
    Convenience "constructor" used like this:

        myarray = MakeStackArray(int)

    The idiom could also be

        myarray = cast('StackArray[int]', [])

    But that's uglier.
    """
    return cast('StackArray[item_type]', [])


if TYPE_CHECKING:
    K = TypeVar('K')
    V = TypeVar('V')


def iteritems(d):
    # type: (Dict[K, V]) -> Iterator[Tuple[K, V]]
    """Make translation a bit easier."""
    return d.iteritems()


def split_once(s, delim):
    # type: (str, str) -> Tuple[str, Optional[str]]
    """Easier to call than split(s, 1) because of tuple unpacking."""

    parts = s.split(delim, 1)
    if len(parts) == 1:
        no_str = None  # type: Optional[str]
        return s, no_str
    else:
        return parts[0], parts[1]


def hex_lower(i):
    # type: (int) -> str
    return '%x' % i


def dict_erase(d, key):
    # type: (Dict[Any, Any], Any) -> None
    """
    Ensure that a key isn't in the Dict d.  This makes C++ translation easier.
    """
    try:
        del d[key]
    except KeyError:
        pass


def str_cmp(s1, s2):
    # type: (str, str) -> int
    if s1 == s2:
        return 0
    if s1 < s2:
        return -1
    else:
        return 1


class UniqueObjects(object):
    """A set of objects identified by their address in memory

    Python's id(obj) returns the address of any object.  But we don't simply
    implement it, because it requires a uint64_t on 64-bit systems, while mycpp
    only supports 'int'.

    So we have a whole class.

    Should be used for:

    - Cycle detection when pretty printing, as Python's repr() does
      - See CPython's Objects/object.c PyObject_Repr()
      /* These methods are used to control infinite recursion in repr, str, print,
          etc.  Container objects that may recursively contain themselves,
          e.g. builtin dictionaries and lists, should use Py_ReprEnter() and
          Py_ReprLeave() to avoid infinite recursion.
          */
      - e.g. dictobject.c dict_repr() calls Py_ReprEnter() to print {...}
      - In Python 2.7 a GLOBAL VAR is used

      - It also checks for STACK OVERFLOW

    - Packle serialization
    """

    def __init__(self):
        # 64-bit id() -> small integer ID
        self.addresses = {}  # type: Dict[int, int]

    def Contains(self, obj):
        # type: (Any) -> bool
        """ Convenience? """
        return self.Get(obj) != -1

    def MaybeAdd(self, obj):
        # type: (Any) -> None
        """ Convenience? """

    # def AddNewObject(self, obj):
    def Add(self, obj):
        # type: (Any) -> None
        """
        Assert it isn't already there, and assign a new ID!

        # Lib/pickle does:

            self.memo[id(obj)] = memo_len, obj

        I guess that's the object ID and a void*

        Then it does:

            x = self.memo.get(id(obj))

        and

            # If the object is already in the memo, this means it is
            # recursive. In this case, throw away everything we put on the
            # stack, and fetch the object back from the memo.
            if id(obj) in self.memo:
                write(POP + self.get(self.memo[id(obj)][0]))

        BUT It only uses the numeric ID!
        """
        addr = id(obj)
        assert addr not in self.addresses
        self.addresses[addr] = len(self.addresses)

    def Get(self, obj):
        # type: (Any) -> int
        """
        Returns unique ID assigned

        Returns -1 if it doesn't exist?
        """
        addr = id(obj)
        return self.addresses.get(addr, -1)

    # Note: self.memo.clear() doesn't appear to be used


def probe(provider, name, *args):
    # type: (str, str, Any) -> None
    """Create a probe for use with profilers like linux perf and ebpf or dtrace."""
    # Noop. Just a marker for mycpp to emit a DTRACE_PROBE()
    return


class File:
    """
    TODO: This should define a read/write interface, and then LineReader() and
    Writer() can possibly inherit it, with runtime assertions

    Then we allow downcasting from File -> LineReader, like we currently do in
    C++ in gc_mylib.h.

    Inheritance can't express the structural Reader/Writer pattern of Go, which
    would be better.  I suppose we could use File* everywhere, but having
    fine-grained types is nicer.  And there will be very few casts.
    """
    pass
