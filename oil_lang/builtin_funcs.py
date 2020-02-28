#!/usr/bin/env python2
"""
builtin_funcs.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, scope_e
from _devbuild.gen.syntax_asdl import sh_lhs_expr
from core.util import e_die
from oil_lang import objects

from typing import Callable, Union, TYPE_CHECKING
if TYPE_CHECKING:
  from oil_lang.objects import ParameterizedArray
  from core.state import Mem


def SetGlobalFunc(mem, name, func):
  # type: (Mem, str, Union[Callable, ParameterizedArray, type]) -> None
  """Used by bin/oil.py to set split(), etc."""
  assert callable(func), func
  mem.SetVar(sh_lhs_expr.Name(name), value.Obj(func), scope_e.GlobalOnly)


def _Join(array, delim=''):
  """
  func join(items Array[Str]) Str ...
  """
  # default is not ' '?
  return delim.join(array)


def _Maybe(obj):
  """
  func join(items Array[Str]) Str ...
  """
  if obj is None:
    return []

  # TODO: Need proper span IDs
  if not isinstance(obj, str):
    raise e_die('maybe() passed arg of invalid type %r',
                obj.__class__.__name__)

  s = obj
  if len(s):
    return [s]
  else:
    return []


def Init(mem):
  # type: (Mem) -> None
  """Populate the top level namespace with some builtin functions."""

  #
  # Oil
  #

  SetGlobalFunc(mem, 'join', _Join)
  SetGlobalFunc(mem, 'maybe', _Maybe)
  # NOTE: split() is set in main(), since it depends on the Splitter() object /
  # $IFS.
  # TODO: How to ask for Python's split algorithm?  Or Awk's?

  #
  # Borrowed from Python
  #

  SetGlobalFunc(mem, 'Table', objects.Table)
  SetGlobalFunc(mem, 'Array', objects.ParameterizedArray())

  # Types:
  # TODO: Should these be Bool Int Float Str List Dict?
  SetGlobalFunc(mem, 'Bool', bool)
  SetGlobalFunc(mem, 'Int', int)

  # TODO: Enable float
  # OVM: PyOS_string_to_double()
  # osh: Python/ovm_stub_pystrtod.c:10: PyOS_string_to_double: Assertion `0' failed.
  SetGlobalFunc(mem, 'Float', float)

  SetGlobalFunc(mem, 'Tuple', tuple)
  SetGlobalFunc(mem, 'Str', str)
  SetGlobalFunc(mem, 'List', list)
  SetGlobalFunc(mem, 'Dict', dict)

  # Singleton tuple!
  SetGlobalFunc(mem, 'tup', lambda x: (x,))

  SetGlobalFunc(mem, 'len', len)
  SetGlobalFunc(mem, 'max', max)
  SetGlobalFunc(mem, 'min', min)
  # NOTE: cmp() deprecated in Python 3

  # Utilities
  SetGlobalFunc(mem, 'abs', abs)
  # round()
  # divmod() - probably useful?  Look at the implementation

  # Return an iterable like Python 3.  Used for 'step' param.
  SetGlobalFunc(mem, 'range', xrange)
  # For the 'step' param.
  SetGlobalFunc(mem, 'slice', slice)

  # Not the best API, but requires no new syntax, and is familiar to Python
  # users.
  SetGlobalFunc(mem, 'enumerate', enumerate)
  # I never use this, but it's familiar
  SetGlobalFunc(mem, 'zip', zip)

  SetGlobalFunc(mem, 'any', any)
  SetGlobalFunc(mem, 'all', all)
  SetGlobalFunc(mem, 'sum', sum)

  # We maintain the L.sort() and sorted(L) distinction.
  # TODO: How do these interact with rows of a data frame?
  SetGlobalFunc(mem, 'sorted', sorted)
  SetGlobalFunc(mem, 'reversed', reversed)

  # TODO: ord() should UTF-8 decode its argument
  # ord('\u100') -> 256
  #
  # This can be accomplished by the str.runes() iterator though?
  #
  #SetGlobalFunc(mem, 'ord', ord)
  # 
  # unichr should ENCODE its argument
  # >>> unichr(0x10000)
  # u'\U00010000'
  # >>> unichr(0x1000000)
  # Traceback (most recent call last):
  #   File "<stdin>", line 1, in <module>
  # ValueError: unichr() arg not in range(0x110000) (wide Python build)

  # bin(5) -> 0b101  TODO: Take over %b in printf
  # oct() -> '%o' % 9
  # hex(17) -> 0x11
  # NOTE: '%x' % 17 gives '11'.  Somehow there's no equivalent for binary?

  # Other builtins:

  # Exceptions:
  #   IndexError
  #   KeyError
  #   IOError (should be same as OSError)
  #   StopIteration
  #   RuntimeError

  # There's also float.hex() and float.fromhex()

  # Types:
  #   type()
  #   callable() -- test if it's callable
  #   isinstance()
  #   issubclass()
  #
  # All Objects:  (Ruby has Kernel?)
  #   id() - unique ID
  #   hash()
  #   object() -- what is this for?  For subtyping?
  #   repr() -- are we maintaining repr and str?  We also have a repr builtin.
  #
  # Introspection:
  #   intern()
  #   dir() -- list attributes names.  Might want this.
  #   globals(), locals()
  #
  # Iterators:
  #   iter([]) -> listiterator
  #   next() -- do we need it?
  # 
  # Attributes:
  #   delattr, hasattr, getattr, setattr

  # Not including:
  # - map, filter (use list comp), reduce
  # - open: use redirect
  # - pow() -- do 3^5, and there's no add()
  # - input(), raw_input() -- read builtin instead?
  # - super() -- object system is different
  # - python marks these as deprecated: apply, coerce, buffer, intern
  #
  # Other Types:
  # - set() -- I think the dict type will subsume this
  # - slice() -- never needed it
  # - these seem confusing
  #   - memoryview()
  #   - bytearray()
  #   - buffer() (deprecated by Python)

  # Modules that could be builtin:
  # - math -- sin(), a lot of floating point stuff like frexp()
  #   - new in Python 3.4: statistics
  # - hashlib, e.g. useful for writing a package manager or build system
  # - heapq, bisect: algorithms, somewhat rarely used
  # - datetime -- hm we need some sort of better replacement
  #   - strftime() because awk has it
  # - itertools, functools -- I don't really use these
  #
  # libc wrappers:
  # - normpath()
  # - replacement for $RANDOM.  rand() and srand()?
  # left to external utils:
  # - mkdir, readlink()

  # web formats:
  # - URL serialization: cleaned up urllib.quote_plus, cgi.parse_qs
  #   - encodeURIComponent()
  #   - generate a form that generates a URL
  # - cookie serialization
  # - HTML escaping
  #
  # - maybe: base64, although the external utility might be OK

  # Other serialization:
  # - POSIX shell code gen
  # - C code gen
  # - Python code gen, etc.
  # - JavaScript can use # JSON.

  # NOTE:
  # json and tsv2 are styled as BUILTINS
  #   python: json.load, dump
  #   js: JSON.parse, stringify
  #   better: read, write
  #
  # json read :x < foo.json
  # tsv2 read :x < foo.tsv2
  #
  # json write -indent 2 :mydict > out.txt
  # tsv2 write -indent 2 :mytable > out.txt
  #

  #
  # Awk
  #

  # https://www.gnu.org/software/gawk/manual/gawk.html#Library-Functions

  # Already covered: strtonum(), round()
  # need strftime
