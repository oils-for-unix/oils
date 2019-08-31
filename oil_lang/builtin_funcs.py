#!/usr/bin/env python2
"""
builtin_funcs.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, scope_e
from _devbuild.gen.syntax_asdl import lhs_expr


def SetGlobalFunc(mem, name, func):
  """Used by bin/oil.py to set split(), etc."""
  assert callable(func), func
  mem.SetVar(lhs_expr.LhsName(name), value.Obj(func), (), scope_e.GlobalOnly)


def _Join(array, delim=''):
  """
  func join(items Array[Str]) Str ...
  """
  # default is not ' '?
  return delim.join(array)


def Init(mem):
  """Populate the top level namespace with some builtin functions."""

  SetGlobalFunc(mem, 'len', len)
  SetGlobalFunc(mem, 'max', max)
  SetGlobalFunc(mem, 'min', min)
  # NOTE: cmp() deprecated in Python 3

  # Utilities
  SetGlobalFunc(mem, 'abs', abs)
  # round()
  # divmod() - probably useful?  Look at the implementation
  # chr() and ord() are similar "utilities"
  #   have only ONE of chr() and unichr()

  SetGlobalFunc(mem, 'any', any)
  SetGlobalFunc(mem, 'all', all)
  SetGlobalFunc(mem, 'sum', sum)

  # Return an iterable like Python 3.
  SetGlobalFunc(mem, 'range', xrange)

  SetGlobalFunc(mem, 'join', _Join)

  # Types:
  # TODO: Should these be Bool Int Float Str List Dict?
  SetGlobalFunc(mem, 'bool', bool)
  SetGlobalFunc(mem, 'int', int)
  SetGlobalFunc(mem, 'float', float)
  SetGlobalFunc(mem, 'tuple', tuple)
  SetGlobalFunc(mem, 'str', str)
  SetGlobalFunc(mem, 'list', list)
  SetGlobalFunc(mem, 'dict', dict)

  # We maintain the L.sort() and sorted(L) distinction.
  # TODO: How do these interact with rows of a data frame?
  SetGlobalFunc(mem, 'sorted', sorted)
  SetGlobalFunc(mem, 'reversed', reversed)

  # NOTE: split() is set in main(), since it depends on the Splitter() object /
  # $IFS.

  # Other builtins:

  # bin(5) -> 0b101
  # oct() -> '%o' % 9
  # hex(17) -> 0x11
  # NOTE: '%x' % 17 gives '11'.  Somehow there's no equivalent for binary?

  # There's also float.hex() and float.fromhex()


  # Types:
  #   type()
  #   callable() -- test if it's callable
  #   isinstance()
  #   issubclass()
  #
  # Iterators:
  #   iter([]) -> listiterator
  #   next() -- do we need it?
  # 
  #   range() -- done
  #   enumerate() -- I would like something simpler here
  #   zip()
  #
  # Attributes:
  #   delattr, hasattr, getattr, setattr
  #
  # All Objects:  (Ruby has Kernel?)
  #   id() - unique ID
  #   hash()
  #   object() -- what is this for?  For subtyping?
  #   repr() -- are we maintaining repr and str?
  #
  # Introspection:
  #   intern()
  #   dir() -- list attributes names.  Might want this.
  #   globals(), locals()

  # types:
  # - set() -- I think the dict type will subsume this
  # - slice() -- never needed it
  # - these seem confusing
  #   - memoryview()
  #   - bytearray()
  #   - buffer()

  # Not including:
  # - map, filter (use list comp), reduce
  # - open: use redirect
  # - pow() -- do 3^5, and there's no add()
  # - input(), raw_input() -- read builtin instead?
  # - super() -- object system is different
  # - python marks these as deprecated: apply, coerce, buffer, intern

  # Exceptions:
  #   IndexError
  #   KeyError
  #   IOError (should be same as OSError)
  #   StopIteration
  #   RuntimeError
