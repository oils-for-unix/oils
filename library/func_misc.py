#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_str, value_t, value_e
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import vm
from core.ui import ValType
from frontend import typed_args
from mycpp.mylib import NewDict, iteritems, log, tagswitch
from ysh import expr_eval, val_ops

from typing import TYPE_CHECKING, Dict, List, cast

_ = log


class Append(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        items = r.PosList()
        to_append = r.PosValue()
        r.Done()

        items.append(to_append)

        # Equivalent to no return value?
        return value.Null


class Pop(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        items = r.PosList()
        r.Done()

        items.pop()

        return value.Null


class StartsWith(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        string = r.PosStr()
        match = r.PosStr()
        r.Done()

        res = string.startswith(match)
        return value.Bool(res)


class Strip(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        string = r.PosStr()
        r.Done()

        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        string = r.PosStr()
        r.Done()

        res = string.upper()
        return value.Str(res)


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        dictionary = r.PosDict()
        r.Done()

        keys = [value.Str(k) for k in dictionary.keys()]  # type: List[value_t]
        return value.List(keys)


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        x = r.PosValue()
        r.Done()

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

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        li = r.PosList()
        r.Done()

        li.reverse()

        return value.Null


class Join(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        li = r.PosList()

        delim = ''
        if len(pos_args):  # reader has a reference
            delim = r.PosStr()

        r.Done()

        strs = []  # type: List[str]
        for i, el in enumerate(li):
            strs.append(val_ops.Stringify(el, loc.Missing))

        return value.Str(delim.join(strs))


class Maybe(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        if val == value.Null:
            return value.List([])

        s = val_ops.ToStr(
            val, 'maybe() expected Str, but got %s' % value_str(val.tag()),
            loc.Missing)
        if len(s):
            return value.List([val])  # use val to avoid needlessly copy

        return value.List([])


class _Type(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        tname = ValType(val)
        return value.Str(tname[6:])  # strip "value." prefix


class _Bool(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        return value.Bool(val_ops.ToBool(val))


class _Int(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Int(val.i)

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Int(int(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                return value.Int(int(val.s))

        raise error.TypeErr(
            val, 'Int() expected Int, Float, or Str, but got %s' %
            value_str(val.tag()), loc.Missing)


class _Float(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Float(float(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Float(val.f)

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                return value.Float(float(val.s))

        raise error.TypeErr(
            val, 'Float() expected Int, Float, or Str, but got %s' %
            value_str(val.tag()), loc.Missing)


class _Str(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        if len(pos_args) == 0:
            return value.Str('')

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Str(str(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Str(str(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                return value.Str(val.s)

        raise error.TypeErr(
            val, 'Str() expected Str, Int, or Float, but got %s' %
            value_str(val.tag()), loc.Missing)


class _List(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        if len(pos_args) == 0:
            return value.List([])

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.List):
                val = cast(value.List, UP_val)
                return value.List(list(val.items))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                # MYCPP: rewrite list comprehension over sum type
                l = [] # type: List[value_t]
                for c in val.s:
                    l.append(value.Str(c))

                return value.List(l)

        raise error.TypeErr(
            val,
            'List() expected List or Str, but got %s' % value_str(val.tag()),
            loc.Missing)


class _Dict(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        d = NewDict() # type: Dict[str, value_t]
        if len(pos_args) == 0:
            return value.Dict(d)

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.List):
                val = cast(value.List, UP_val)
                for i, item in enumerate(val.items):
                    kv = val_ops.ToList(item,
                                        'expected item %d to be a List' % i,
                                        loc.Missing)
                    if len(kv) != 2:
                        raise error.TypeErr(
                            item,
                            'expected item %d to have length 2, but has length %d'
                            % (i, len(kv)), loc.Missing)

                    k = val_ops.ToStr(
                        kv[0],
                        'expected first element of item %d to be Str' % i,
                        loc.Missing)
                    d[k] = kv[1]

                return value.Dict(d)

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)
                for k, v in iteritems(val.d):
                    d[k] = v

                return value.Dict(d)

        raise error.TypeErr(
            val,
            'Dict() expected List or Dict, but got %s' % value_str(val.tag()),
            loc.Missing)
