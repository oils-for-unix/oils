#!/usr/bin/env python2
"""func_cpython.py - code to get rid of"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import value, value_e, value_t, scope_e
from _devbuild.gen.syntax_asdl import loc, sh_lhs_expr
from core import error
from core import vm
from mycpp.mylib import log
from frontend import lexer
from library import func_eggex
from library import func_misc
from ysh import cpython
from ysh import expr_eval

from typing import TYPE_CHECKING, Dict, List, Callable, Union, cast
if TYPE_CHECKING:
    from core import state
    from osh import glob_
    from osh import split
    from library import func_hay

_ = log


def SetGlobalFunc(mem, name, func):
    # type: (state.Mem, str, Union[Callable, type]) -> None
    """Used by core/shell.py to set split(), etc."""
    assert isinstance(func, vm._Callable) or callable(func), func

    # TODO: Fix this location info
    left = lexer.DummyToken(Id.Undefined_Tok, '')
    mem.SetValue(sh_lhs_expr.Name(left, name), value.Func(func),
                 scope_e.GlobalOnly)


def _Join(array, delim=''):
    """func join(items List[Str]) Str ..."""
    # default is not ' '?
    return delim.join(array)


def _Maybe(obj):
    """func join(items List[Str]) Str ..."""
    if obj is None:
        return []

    # TODO: Need proper span IDs
    if not isinstance(obj, str):
        raise error.Expr('maybe() passed arg of invalid type %r' %
                         obj.__class__.__name__)

    s = obj
    if len(s):
        return [s]
    else:
        return []


def _Extend(L, arg):
    L.extend(arg)


class _Shvar_get(object):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        self.mem = mem

    def __call__(self, *args):
        name = args[0]
        val = expr_eval.LookupVar(self.mem, name, scope_e.Dynamic,
                                   loc.Missing)
        return cpython._ValueToPyObj(val)


class _VmEval(object):
    """_vm_eval()"""

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


def _Reversed(mylist):
    # Make a copy
    return list(reversed(mylist))


def Init2(mem, splitter, globber):
    # type: (state.Mem, split.SplitContext, glob_.Globber) -> None

    # split() builtin
    # TODO: Accept IFS as a named arg?  split('a b', IFS=' ')
    SetGlobalFunc(mem, 'split', splitter.SplitFuncBuiltin)

    # glob() builtin
    SetGlobalFunc(mem, 'glob', lambda s: globber.OilFuncCall(s))


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

    SetGlobalFunc(mem, '_match', func_eggex.Match(mem))
    SetGlobalFunc(mem, '_start', func_eggex.Start(mem))
    SetGlobalFunc(mem, '_end', func_eggex.End(mem))

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
    SetGlobalFunc(mem, 'List', list)  # obsolete without Python-like iterators?
    SetGlobalFunc(mem, 'Dict', dict)  # ditto

    # NOTE: IN-YSH means we can move it to YSH itself

    # For compositionality and testing
    SetGlobalFunc(mem, 'identity', lambda x: x)  # IN-YSH

    SetGlobalFunc(mem, 'max', max)  # IN-YSH with <
    SetGlobalFunc(mem, 'min', min)  # IN-YSH
    # NOTE: cmp() deprecated in Python 3

    # Utilities
    SetGlobalFunc(mem, 'abs', abs)  # IN-YSH with <
    # round()
    # divmod() - probably useful?  Look at the implementation

    SetGlobalFunc(mem, 'any', any)  # IN-YSH with Bool
    SetGlobalFunc(mem, 'all', all)  # IN-YSH with Bool
    SetGlobalFunc(mem, 'sum', sum)  # IN-YSH with +

    SetGlobalFunc(mem, 'reversed', _Reversed)  # IN-YSH with for

    #
    # List/array methods
    #

    # Do we want to make these methods?
    #
    # _ mylist->append('x')
    # _ mylist->pop()
    #
    # It does help

    SetGlobalFunc(mem, 'append', func_misc.Append())
    SetGlobalFunc(mem, 'pop', func_misc.Pop())

    SetGlobalFunc(mem, 'extend', _Extend)

    # count, index, insert, remove

    #
    # String Methods
    #

    # TODO:
    # - strip(), lStrip(), rStrip()
    #
    # Better API
    #   trim() trimLeft() trimRight() - whitespace
    #   trimLeft(runes='') - like Python lstrip() rstrip()
    #
    #   Like shell versions ${s%} ${s^}
    #
    #   trimLeft(str='prefix')
    #   trimLeft(glob='')   # SLOW, DISCOURAGED

    # - upper() lower()
    # - startsWith(), endsWith
    # - find, index
    #
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
    #   data: Null, Bool, Str, Int, Float, List, Dict
    #   supertype for serialization?  Obj or Data?
    #   code: Eggex, Template, Expr, Command
    #         Func, Proc, BoundFunc (or method?)
    #
    # All Objects:  (Ruby has Kernel?)
    #   id() - unique integer ID
    #   repr() -- I think ours is $[]
    #
    # Introspection:
    #   intern()

    # Not including:
    # - map, filter (use list comp), reduce
    # - open: use redirect
    # - pow() -- do 3^5, and there's no add()
    # - input(), raw_input() -- read builtin instead?
    # - super() -- object system is different
    # - python marks these as deprecated: apply, coerce, buffer, intern

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

    #
    # Awk
    #

    # https://www.gnu.org/software/gawk/manual/gawk.html#Library-Functions

    # Already covered: strtonum(), round()
    # need strftime


# vim: sw=4
