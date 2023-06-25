#!/usr/bin/env python2
"""funcs_builtin.py."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (value, value_e, value_str, value_t,
                                        scope_e, IntBox)
from _devbuild.gen.syntax_asdl import loc, sh_lhs_expr
from core import error
from core import vm
from core.util import MustBeInt, MustBeStr, MustBeList
from mycpp.mylib import log, tagswitch
from frontend import lexer
from ysh import expr_eval

from typing import cast, Callable, Dict, List, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from core import state
    from osh import glob_
    from osh import split
    from ysh import funcs

_ = log


def SetGlobalFunc(mem, name, func):
    # type: (state.Mem, str, Union[Callable, type, vm._Func]) -> None
    """Used by bin/oil.py to set split(), etc."""
    # TODO: Fix this location info
    left = lexer.DummyToken(Id.Undefined_Tok, '')
    if isinstance(func, vm._Func):
        mem.SetValue(sh_lhs_expr.Name(left, name), value.Func(func),
                     scope_e.GlobalOnly)
    else:
        assert callable(func), func
        mem.SetValue(sh_lhs_expr.Name(left, name), value.Obj(func),
                     scope_e.GlobalOnly)


class _Join(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 2

        # XXX: python's join() accepts dict keys, strings, and other iterables.
        # should we do the same?
        array = MustBeList(pos_args[0])
        delim = MustBeStr(pos_args[1])

        strs = []  # type: List[str]
        for elem in array.items:
            strs.append(MustBeStr(elem).s)

        return value.Str(delim.s.join(strs))


class _Maybe(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1

        obj = pos_args[0]
        if obj.tag() == value_e.Undef:
            return value.List([])

        ## TODO: Need proper span IDs
        s = MustBeStr(obj)
        if len(s.s):
            return value.List([s])
        else:
            return value.List([])


class _Append(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 2
        L = MustBeList(pos_args[0])
        arg = pos_args[1]
        L.items.append(arg)
        return value.Undef


class _Extend(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 2
        L = MustBeList(pos_args[0])
        args = MustBeList(pos_args[1])
        L.items.extend(args.items)
        return value.Undef


class _Pop(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        L = MustBeList(pos_args[0])
        L.pop()  # NOT returned
        return value.Undef


class _Match(vm._Func):
    """_match(0) or _match():   get the whole match _match(1) ..

    _match(N):  submatch
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Func.__init__(self)
        self.mem = mem

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        return value.Undef
        if len(pos_args) == 0:
            return self.mem.GetMatch(0)

        if len(pos_args) > 1:
            raise TypeError('Too many arguments')

        # TODO: Support strings
        arg = MustBeInt(pos_args[0])
        s = self.mem.GetMatch(arg.i)
        # Oil code doesn't deal well with exceptions!
        #if s is None:
        #  raise IndexError('No such group')
        return value.Str(s)


class _Start(vm._Func):
    """Same signature as _match(), but for start positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Func.__init__(self)
        self.mem = mem

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        raise NotImplementedError('_start')


class _End(vm._Func):
    """Same signature as _match(), but for start positions."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Func.__init__(self)
        self.mem = mem

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        raise NotImplementedError('_end')


class _Shvar_get(vm._Func):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Func.__init__(self)
        self.mem = mem

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        return value.Undef
        assert len(pos_args) == 1
        name = MustBeStr(pos_args[0])
        return expr_eval.LookupVar(self.mem, name.s, scope_e.Dynamic,
                                   loc.Missing)


class _VmEval(vm._Func):
    """_vm_eval()"""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Func.__init__(self)
        self.mem = mem

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        return value.Undef

        # XXX source_path = args[0]
        # XXX first_words = args[1]
        # XXX log('source %s', source_path)
        # XXX log('words %s', first_words)

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

        return value.Dict({'key': 'value'})
        raise NotImplementedError()


class _Split(vm._Func):

    def __init__(self, splitter):
        # type: (split.SplitContext) -> None
        vm._Func.__init__(self)
        self.splitter = splitter

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        s = MustBeStr(pos_args[0])
        # XXX: just update splitter.SplitFuncBuiltin to return value_t
        return value.List(
            [value.Str(elem) for elem in self.splitter.SplitFuncBuiltin(s.s)])


class _Glob(vm._Func):

    def __init__(self, globber):
        # type: (glob_.Globber) -> None
        vm._Func.__init__(self)
        self.globber = globber

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        s = MustBeStr(pos_args[0])
        # XXX: just update globber.OilFuncCall to return value_t
        return value.List(
            [value.Str(elem) for elem in self.globber.OilFuncCall(s.s)])


def Init2(mem, splitter, globber):
    # type: (state.Mem, split.SplitContext, glob_.Globber) -> None

    # split() builtin
    # TODO: Accept IFS as a named arg?  split('a b', IFS=' ')
    SetGlobalFunc(mem, 'split', _Split(splitter))

    # glob() builtin
    SetGlobalFunc(mem, 'glob', _Glob(globber))


def Init3(mem, config_parser, eval_to_dict, block_as_str, hay_result):
    # type: (state.Mem, funcs.ParseHay, funcs.EvalHay, funcs.BlockAsStr, funcs.HayResult) -> None
    SetGlobalFunc(mem, 'parse_hay', config_parser)
    SetGlobalFunc(mem, 'eval_hay', eval_to_dict)

    # For interactive debugging.  'eval_hay()' and 'hay eval' are the main APIs.
    SetGlobalFunc(mem, '_hay', hay_result)

    # for upper case TASK blocks: command_t -> Str
    SetGlobalFunc(mem, 'block_as_str', block_as_str)


class _Bool(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        assert len(named_args) == 0
        return value.Bool(expr_eval.ToBool(pos_args[0]))


class _Int(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Float(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Str(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _List(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Dict(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Identity(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        return pos_args[0]


class _Tup(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Len(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        arg = pos_args[0]
        UP_arg = arg
        with tagswitch(arg) as case:
            if case(value_e.List):
                arg = cast(value.List, UP_arg)
                return len(arg.items)
            elif case(value_e.Tuple):
                arg = cast(value.Tuple, UP_arg)
                return len(arg.items)
            elif case(value_e.Dict):
                arg = cast(value.Dict, UP_arg)
                return len(arg.d)
            elif case(value_e.Str):
                arg = cast(value.Str, UP_arg)
                return len(arg.s)
            else:
                raise error.InvalidType(
                    'expected List, Tuple, Dict, or Str, but got %s' %
                    value_str(arg.tag()), loc.Missing)


class _Max(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Min(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Abs(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Range(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        if len(pos_args) == 1:
            lower = MustBeInt(pos_args[0])
            return value.Range(IntBox(lower.i), None, None)
        elif len(pos_args) == 2:
            lower = MustBeInt(pos_args[0])
            upper = MustBeInt(pos_args[1])
            return value.Range(IntBox(lower.i), IntBox(upper.i), None)
        elif len(pos_args) == 3:
            lower = MustBeInt(pos_args[0])
            upper = MustBeInt(pos_args[1])
            step = MustBeInt(pos_args[2])
            return value.Range(IntBox(lower.i), IntBox(upper.i),
                               IntBox(step.i))
        else:
            raise error.Expr('expected 1-3 arguments', loc.Missing)


class _Slice(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        if len(pos_args) == 1:
            lower = MustBeInt(pos_args[0])
            return value.Range(IntBox(lower.i), None, None)
        elif len(pos_args) == 2:
            lower = MustBeInt(pos_args[0])
            upper = MustBeInt(pos_args[1])
            return value.Range(IntBox(lower.i), IntBox(upper.i), None)
        elif len(pos_args) == 3:
            lower = MustBeInt(pos_args[0])
            upper = MustBeInt(pos_args[1])
            step = MustBeInt(pos_args[2])
            return value.Range(IntBox(lower.i), IntBox(upper.i),
                               IntBox(step.i))
        else:
            raise error.Expr('expected 1-3 arguments', loc.Missing)


class _Any(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        L = MustBeList(pos_args[0])
        for item in L.items:
            if expr_eval.ToBool(item):
                return value.Bool(True)

        assert value.Bool(False)


class _All(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 1
        L = MustBeList(pos_args[0])
        for item in L.items:
            if not expr_eval.ToBool(item):
                return value.Bool(False)

        assert value.Bool(True)


class _Sum(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Sorted(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _Reversed(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert value.Undef


class _StrStartsWith(vm._Func):

    def __init__(self):
        # type: () -> None
        vm._Func.__init__(self)

    def Run(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
        assert len(pos_args) == 2
        assert len(named_args) == 0

        UP_s = pos_args[0]
        UP_prefix = pos_args[1]
        assert UP_s.tag() == value_e.Str
        assert UP_prefix.tag() == value_e.Str
        s = cast(value.Str, UP_s)
        prefix = cast(value.Str, UP_prefix)
        return value.Bool(s.s.startswith(prefix.s))


def Init(mem):
    # type: (state.Mem) -> None
    """Populate the top level namespace with some builtin functions."""

    #
    # Oil
    #

    SetGlobalFunc(mem, 'join', _Join())
    SetGlobalFunc(mem, 'maybe', _Maybe())
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
    SetGlobalFunc(mem, 'Bool', _Bool())
    SetGlobalFunc(mem, 'Int', _Int())

    SetGlobalFunc(mem, 'Float', _Float())

    SetGlobalFunc(mem, 'Str', _Str())
    SetGlobalFunc(mem, 'List', _List())
    SetGlobalFunc(mem, 'Dict', _Dict())

    # For compositionality and testing
    SetGlobalFunc(mem, 'identity', _Identity())

    # Singleton tuple!
    # TODO: remove this and the trailing comma message for 3,
    # A trailing comma can just be a syntax error?
    SetGlobalFunc(mem, 'tup', _Tup())

    SetGlobalFunc(mem, 'len', _Len())
    SetGlobalFunc(mem, 'max', _Max())
    SetGlobalFunc(mem, 'min', _Min())
    # NOTE: cmp() deprecated in Python 3

    # Utilities
    SetGlobalFunc(mem, 'abs', _Abs())
    # round()
    # divmod() - probably useful?  Look at the implementation

    # TODO: Consolidate with explicit 1:2 syntax
    # Return an iterable like Python 3.  Used for 'step' param.
    SetGlobalFunc(mem, 'range', _Range())
    # For the 'step' param.
    SetGlobalFunc(mem, 'slice', _Slice())

    SetGlobalFunc(mem, 'any', _Any())
    SetGlobalFunc(mem, 'all', _All())
    SetGlobalFunc(mem, 'sum', _Sum())

    # We maintain the L.sort() aka sort(L) and sorted(L) distinction.
    # TODO: How do these interact with rows of a data frame?
    SetGlobalFunc(mem, 'sorted', _Sorted())
    SetGlobalFunc(mem, 'reversed', _Reversed())

    #
    # List/array methods
    #

    # TODO: Universal function call syntax can change this?
    SetGlobalFunc(mem, 'append', _Append())
    SetGlobalFunc(mem, 'extend', _Extend())
    SetGlobalFunc(mem, 'pop', _Pop())
    # count, index, insert, remove

    #
    # String Methods
    #

    SetGlobalFunc(mem, 'startswith', _StrStartsWith())
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
