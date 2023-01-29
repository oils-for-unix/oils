#!/usr/bin/env python2
"""
builtin_funcs.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import value, scope_e
from _devbuild.gen.syntax_asdl import sh_lhs_expr
from core import error
from core.pyerror import log
from frontend import lexer
from oil_lang import expr_eval

from typing import Callable, Union, TYPE_CHECKING
if TYPE_CHECKING:
  from core import state
  from osh import glob_
  from osh import split
  from oil_lang import funcs

_ = log


def SetGlobalFunc(mem, name, func):
  # type: (state.Mem, str, Union[Callable, type]) -> None
  """Used by bin/oil.py to set split(), etc."""
  assert callable(func), func

  # TODO: Fix this location info
  left = lexer.DummyToken(Id.Undefined_Tok, '')
  mem.SetValue(sh_lhs_expr.Name(left, name), value.Obj(func), scope_e.GlobalOnly)


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
    raise error.Expr('maybe() passed arg of invalid type %r' % obj.__class__.__name__)

  s = obj
  if len(s):
    return [s]
  else:
    return []


def _Append(L, arg):
  L.append(arg)


def _Extend(L, arg):
  L.extend(arg)


def _Pop(L):
  L.pop()


class _Match(object):
  """
  _match(0) or _match():   get the whole match
  _match(1) .. _match(N):  submatch
  """
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, *args):
    if len(args) == 0:
      return self.mem.GetMatch(0)

    if len(args) == 1:
      arg = args[0]
      if isinstance(arg, int):
        s = self.mem.GetMatch(arg)
        # Oil code doesn't deal well with exceptions!
        #if s is None:
        #  raise IndexError('No such group')
        return s

      # TODO: Support strings
      raise TypeError('Expected an integer, got %r' % arg)

    raise TypeError('Too many arguments')


class _Start(object):
  """
  Same signature as _match(), but for start positions
  """
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, *args):
    raise NotImplementedError('_start')


class _End(object):
  """
  Same signature as _match(), but for end positions
  """
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, *args):
    raise NotImplementedError('_end')


class _Shvar_get(object):
  """Look up with dynamic scope."""
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, *args):
    name = args[0]
    return expr_eval.LookupVar(self.mem, name, scope_e.Dynamic)


class _VmEval(object):
  """ _vm_eval() """
  def __init__(self, mem):
    self.mem = mem

  def __call__(self, *args):

    source_path = args[0]
    first_words = args[1]
    log('source %s', source_path)
    log('words %s', first_words)

    # Notes on logic for the 'source' builtin:
    # - no search_path lookup
    # - dev.ctx_Tracer('vm_eval')
    # - add PushTemp(), and return the namespace like EvalBlock()
    #   - and it should only return the CONSTS?
    #   - and you need location info for further validation
    # - 'source' uses cmd_ev.mem.  We do NOT want to share that, but we do want
    #   to share fd_state, because it's the same process.

    # But this is NOT like source because it should use a totally different
    # VM!  It's a subinterpreter.
    #
    # vm_eval() ?
    # - but it gets references to procs in the parent interpreter.  So it's
    #   not totally isolated.
    #
    # Idea: Instead of 'first_words', should we have a 'predicate' proc that
    #   returns 0 or 1?  It is a plugin that becomes plugged into
    #   Executor::RunSimpleCommand()?
    #   - You want to abstract that a bit
    # - So this is reflection on executor.builtins and cmd_ev.procs
    #   - what about cmd_ev.assign_builtins?
    #
    # Idea: for untrusted config eval, do we want a process boundary?  I think
    # pure Oil is pretty safe, even against timing attacks, since there's no
    # way to tie.

    return {'key': 'value'}
    raise NotImplementedError()


def Init2(mem, splitter, globber):
  # type: (state.Mem, split.SplitContext, glob_.Globber) -> None

  # split() builtin
  # TODO: Accept IFS as a named arg?  split('a b', IFS=' ')
  SetGlobalFunc(mem, 'split', splitter.SplitFuncBuiltin)

  # glob() builtin
  SetGlobalFunc(mem, 'glob', lambda s: globber.OilFuncCall(s))


def Init3(mem, config_parser, eval_to_dict, block_as_str, hay_result):
  # type: (state.Mem, funcs.ParseHay, funcs.EvalHay, funcs.BlockAsStr, funcs.HayResult) -> None
  SetGlobalFunc(mem, 'parse_hay', config_parser.Call)
  SetGlobalFunc(mem, 'eval_hay', eval_to_dict.Call)

  # For interactive debugging.  'eval_hay()' and 'hay eval' are the main APIs.
  SetGlobalFunc(mem, '_hay', hay_result.Call)

  # for upper case TASK blocks: command_t -> Str
  SetGlobalFunc(mem, 'block_as_str', block_as_str.Call)



def Init(mem):
  # type: (state.Mem) -> None
  """Populate the top level namespace with some builtin functions."""

  #
  # Oil
  #

  SetGlobalFunc(mem, 'join', _Join)
  SetGlobalFunc(mem, 'maybe', _Maybe)
  # NOTE: split() is set in main(), since it depends on the Splitter() object /
  # $IFS.
  # TODO: How to ask for Python's split algorithm?  Or Awk's?

  SetGlobalFunc(mem, '_match', _Match(mem))
  SetGlobalFunc(mem, '_start', _Start(mem))
  SetGlobalFunc(mem, '_end', _End(mem))

  SetGlobalFunc(mem, 'shvar_get', _Shvar_get(mem))

  #
  # Borrowed from Python
  #

  # Types:
  # Should the constructors be Python compatible, and types be capital?
  SetGlobalFunc(mem, 'Bool', bool)
  SetGlobalFunc(mem, 'Int', int)

  SetGlobalFunc(mem, 'Float', float)

  SetGlobalFunc(mem, 'Str', str)
  SetGlobalFunc(mem, 'List', list)
  SetGlobalFunc(mem, 'Dict', dict)

  # For compositionality and testing
  SetGlobalFunc(mem, 'identity', lambda x: x)

  # Singleton tuple!
  # TODO: remove this and the trailing comma message for 3,
  # A trailing comma can just be a syntax error?
  SetGlobalFunc(mem, 'tup', lambda x: (x,))

  SetGlobalFunc(mem, 'len', len)
  SetGlobalFunc(mem, 'max', max)
  SetGlobalFunc(mem, 'min', min)
  # NOTE: cmp() deprecated in Python 3

  # Utilities
  SetGlobalFunc(mem, 'abs', abs)
  # round()
  # divmod() - probably useful?  Look at the implementation

  # TODO: Consolidate with explicit 1:2 syntax
  # Return an iterable like Python 3.  Used for 'step' param.
  SetGlobalFunc(mem, 'range', xrange)
  # For the 'step' param.
  SetGlobalFunc(mem, 'slice', slice)

  SetGlobalFunc(mem, 'any', any)
  SetGlobalFunc(mem, 'all', all)
  SetGlobalFunc(mem, 'sum', sum)

  # We maintain the L.sort() aka sort(L) and sorted(L) distinction.
  # TODO: How do these interact with rows of a data frame?
  SetGlobalFunc(mem, 'sorted', sorted)
  SetGlobalFunc(mem, 'reversed', reversed)

  #
  # List/array methods
  #

  # TODO: Universal function call syntax can change this?
  SetGlobalFunc(mem, 'append', _Append)
  SetGlobalFunc(mem, 'extend', _Extend)
  SetGlobalFunc(mem, 'pop', _Pop)
  # count, index, insert, remove

  #
  # String Methods
  #

  # TODO: strip(), lstrip(), rstrip().  What about upper() and lower() etc.?
  # Shell has versions of those
  # startswith, endswith
  # find, index, cout
  # partition, rpartition: I never seem to use these?

  # Notes on overloaded functions
  #
  #  L.pop()
  #  D.pop('key')
  #
  # Should we mave multiple dispatch?
  #
  # var vals = %(a b)
  # = concat('--flag=', vals)  # => ['--flag=a', '--flag=b']
  # = concat(vals, '=')        # => ['a=', 'b=']
  #
  # Or should we have broadcast like Julia?
  # This can also be accomplished with builtin sub?
  #
  # write --qsn -- @vals | prefix 'a' | read --lines --qsn :out
  # write --qsn -- @vals | suffix 'b' | read --lines --qsn :out
  # 'prefix' and 'suffix' can be like 'awk'?


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

  # There's also float.hex() and float.fromhex()

  # Types:
  #   type()     -- similar to = operator
  #   callable() -- test if it's callable
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
  # json and qtt are styled as BUILTINS
  #   python: json.load, json.dump
  #   js: JSON.parse, JSON.stringify
  #   Oil:
  #     json read :x < foo.json
  #     qtt read :x < foo.qtt

  # This loads a STRING into mytable?  Or maybe it's tagged with a type so you
  # can slice differently?
  #
  # qtt prettify :mytable < '''
  # name age:Int
  # bob  40
  # '''

  #
  # Awk
  #

  # https://www.gnu.org/software/gawk/manual/gawk.html#Library-Functions

  # Already covered: strtonum(), round()
  # need strftime
