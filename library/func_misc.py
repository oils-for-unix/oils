#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_str, value_t, value_e, scope_e
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import ui
from core import vm
from frontend import match
from frontend import typed_args
from mycpp.mylib import NewDict, iteritems, log, tagswitch
from ysh import expr_eval, val_ops

from typing import TYPE_CHECKING, Dict, List, cast
if TYPE_CHECKING:
    from core import state
    from osh import glob_
    from osh import split

_ = log


class Append(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        items = args.PosList()
        to_append = args.PosValue()
        args.Done()

        items.append(to_append)

        # Equivalent to no return value?
        return value.Null


class Extend(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        a = args.PosList()
        b = args.PosList()
        args.Done()

        a.extend(b)
        return value.Null


class Pop(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        items = args.PosList()
        args.Done()

        return items.pop()


class StartsWith(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        string = args.PosStr()
        match = args.PosStr()
        args.Done()

        res = string.startswith(match)
        return value.Bool(res)


class Strip(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        string = args.PosStr()
        args.Done()

        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        string = args.PosStr()
        args.Done()

        res = string.upper()
        return value.Str(res)


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        dictionary = args.PosDict()
        args.Done()

        keys = [value.Str(k) for k in dictionary.keys()]  # type: List[value_t]
        return value.List(keys)


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        x = args.PosValue()
        args.Done()

        UP_x = x
        with tagswitch(x) as case:
            if case(value_e.List):
                x = cast(value.List, UP_x)
                return value.Int(len(x.items))

            elif case(value_e.Dict):
                x = cast(value.Dict, UP_x)
                return value.Int(len(x.d))

            elif case(value_e.Str):
                x = cast(value.Str, UP_x)
                return value.Int(len(x.s))

        raise error.TypeErr(x, 'len() expected Str, List, or Dict',
                            loc.Missing)


class Reverse(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        li = args.PosList()
        args.Done()

        li.reverse()

        return value.Null


class Join(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        li = args.PosList()

        # TODO: see if we can incorporate positional defaults into typed_args.Reader
        delim = ''
        if args.NumPos():
            delim = args.PosStr()

        args.Done()

        strs = []  # type: List[str]
        for i, el in enumerate(li):
            strs.append(val_ops.Stringify(el, loc.Missing))

        return value.Str(delim.join(strs))


class Maybe(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        if val == value.Null:
            return value.List([])

        s = val_ops.ToStr(
            val, 'maybe() expected Str, but got %s' % value_str(val.tag()),
            loc.Missing)
        if len(s):
            return value.List([val])  # use val to avoid needlessly copy

        return value.List([])


class Type(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        tname = ui.ValType(val)
        return value.Str(tname[6:])  # strip "value." prefix


class Bool(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        return value.Bool(val_ops.ToBool(val))


class Int(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                return val

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                return value.Int(int(val.b))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Int(int(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeInteger(val.s):
                    raise error.Expr('Cannot convert %s to Int' % val.s,
                                     loc.Missing)

                return value.Int(int(val.s))

        raise error.TypeErr(val, 'Int() expected Bool, Int, Float, or Str',
                            loc.Missing)


class Float(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Float(float(val.i))

            elif case(value_e.Float):
                return val

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeFloat(val.s):
                    raise error.Expr('Cannot convert %s to Float' % val.s,
                                     loc.Missing)

                return value.Float(float(val.s))

        raise error.TypeErr(val, 'Float() expected Int, Float, or Str',
                            loc.Missing)


class Str_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Str(str(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Str(str(val.f))

            elif case(value_e.Str):
                return val

        raise error.TypeErr(val, 'Str() expected Str, Int, or Float',
                            loc.Missing)


class List_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        l = []  # type: List[value_t]
        it = None  # type: val_ops._ContainerIter
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.List):
                val = cast(value.List, UP_val)
                it = val_ops.ListIterator(val)

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)
                it = val_ops.DictIterator(val)

            elif case(value_e.Range):
                val = cast(value.Range, UP_val)
                it = val_ops.RangeIterator(val)

            else:
                raise error.TypeErr(val,
                                    'List() expected Dict, List, or Range',
                                    loc.Missing)

        assert it is not None
        while not it.Done():
            l.append(it.FirstValue())
            it.Next()

        return value.List(l)


class Dict_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()
        args.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Dict):
                d = NewDict()  # type: Dict[str, value_t]
                val = cast(value.Dict, UP_val)
                for k, v in iteritems(val.d):
                    d[k] = v

                return value.Dict(d)

        raise error.TypeErr(val, 'Dict() expected List or Dict', loc.Missing)


class Split(vm._Callable):

    def __init__(self, splitter):
        # type: (split.SplitContext) -> None
        vm._Callable.__init__(self)
        self.splitter = splitter

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        s = args.PosStr()

        ifs = None  # type: str
        if args.NumPos():
            ifs = args.PosStr()

        args.Done()

        l = [
            value.Str(elem)
            for elem in self.splitter.SplitForWordEval(s, ifs=ifs)
        ]  # type: List[value_t]
        return value.List(l)


class Glob(vm._Callable):

    def __init__(self, globber):
        # type: (glob_.Globber) -> None
        vm._Callable.__init__(self)
        self.globber = globber

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        s = args.PosStr()
        args.Done()

        out = []  # type: List[str]
        self.globber._Glob(s, out)

        l = [value.Str(elem) for elem in out]  # type: List[value_t]
        return value.List(l)


class Shvar_get(vm._Callable):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        name = args.PosStr()
        args.Done()
        return expr_eval.LookupVar(self.mem, name, scope_e.Dynamic,
                                   loc.Missing)


class Assert(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t

        val = args.PosValue()

        msg = ''
        if args.NumPos():
            msg = args.PosStr()

        args.Done()

        if not val_ops.ToBool(val):
            raise error.AssertionErr(msg, loc.Missing)

        return value.Null
