#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_e, value_t, value_str, Obj)

from core import error
from core import num
from display import pp_value
from display import ui
from core import vm
from data_lang import j8
from frontend import match
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import NewDict, iteritems, log, tagswitch
from ysh import val_ops

from typing import TYPE_CHECKING, Dict, List, Optional, cast
if TYPE_CHECKING:
    from osh import glob_
    from osh import split

_ = log


class Object(vm._Callable):
    """OLD API to a value.Obj

    The order of params follows JavaScript's Object.create():
        var obj = Object(prototype, props)
    """

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        prototype = rd.PosValue()
        proto_loc = rd.BlamePos()

        props = rd.PosDict()
        rd.Done()

        chain = None  # type: Optional[Obj]
        UP_prototype = prototype
        with tagswitch(prototype) as case:
            if case(value_e.Null):
                pass
            elif case(value_e.Obj):
                prototype = cast(Obj, UP_prototype)
                chain = prototype
            else:
                raise error.TypeErr(prototype, 'Object() expected Obj or Null',
                                    proto_loc)

        return Obj(chain, props)


class Obj_call(vm._Callable):
    """New API to create a value.Obj

    It has a more natural order
        var obj = Obj(props, prototype)

    Until we have __call__, it's Obj:
        var obj = Obj.new(props, prototype)
    """

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        props = rd.PosDict()

        prototype = rd.OptionalValue()
        proto_loc = rd.BlamePos()

        rd.Done()

        chain = None  # type: Optional[Obj]

        if prototype is not None:
            UP_prototype = prototype
            with tagswitch(prototype) as case:
                if case(value_e.Null):  # Obj({}, null)
                    pass
                elif case(value_e.Obj):
                    prototype = cast(Obj, UP_prototype)
                    chain = prototype
                else:
                    raise error.TypeErr(prototype,
                                        'Object() expected Obj or Null',
                                        proto_loc)

        return Obj(chain, props)


class Prototype(vm._Callable):
    """Get an object's prototype."""

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        obj = rd.PosObj()
        rd.Done()

        if obj.prototype is None:
            return value.Null

        return obj.prototype


class PropView(vm._Callable):
    """Get a Dict view of an object's properties."""

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        obj = rd.PosObj()
        rd.Done()

        return value.Dict(obj.d)


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        x = rd.PosValue()
        rd.Done()

        UP_x = x
        with tagswitch(x) as case:
            if case(value_e.List):
                x = cast(value.List, UP_x)
                return num.ToBig(len(x.items))

            elif case(value_e.Dict):
                x = cast(value.Dict, UP_x)
                return num.ToBig(len(x.d))

            elif case(value_e.Str):
                x = cast(value.Str, UP_x)
                return num.ToBig(len(x.s))

        raise error.TypeErr(x, 'len() expected Str, List, or Dict',
                            rd.BlamePos())


class Type(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        # TODO: assert it's not Undef, Interrupted, Slice
        # Then return an Obj type
        #
        # It would be nice if they were immutable, if we didn't have to create
        # 23-24 dicts and 23-24 Obj on startup?
        return value.Str(ui.ValType(val))


class Join(vm._Callable):
    """Both free function join() and List->join() method."""

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        delim = rd.OptionalStr(default_='')
        rd.Done()

        strs = []  # type: List[str]
        for i, el in enumerate(li):
            strs.append(val_ops.Stringify(el, rd.LeftParenToken(), 'join() '))

        return value.Str(delim.join(strs))


class Maybe(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        if val == value.Null:
            return value.List([])

        s = val_ops.ToStr(
            val, 'maybe() expected Str, but got %s' % value_str(val.tag()),
            rd.LeftParenToken())
        if len(s):
            return value.List([val])  # use val to avoid needlessly copy

        return value.List([])


class Bool(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        return value.Bool(val_ops.ToBool(val))


class Int(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                return val

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                return value.Int(mops.FromBool(val.b))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                ok, big_int = mops.FromFloat(val.f)
                if ok:
                    return value.Int(big_int)
                else:
                    raise error.Expr(
                        "Can't convert float %s to Int" %
                        pp_value.FloatString(val.f), rd.BlamePos())

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeYshInt(val.s):
                    raise error.Expr("Can't convert %s to Int" % val.s,
                                     rd.BlamePos())

                s = val.s.replace('_', '')
                ok, big_int = mops.FromStr2(s)
                if not ok:
                    raise error.Expr("Integer too big: %s" % val.s,
                                     rd.BlamePos())

                return value.Int(big_int)

        raise error.TypeErr(val, 'int() expected Bool, Int, Float, or Str',
                            rd.BlamePos())


class Float(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Float(mops.ToFloat(val.i))

            elif case(value_e.Float):
                return val

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeYshFloat(val.s):
                    raise error.Expr('Cannot convert %s to Float' % val.s,
                                     rd.BlamePos())

                return value.Float(float(val.s))

        raise error.TypeErr(val, 'float() expected Int, Float, or Str',
                            rd.BlamePos())


class Str_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        with tagswitch(val) as case:
            # Avoid extra allocation
            if case(value_e.Str):
                return val
            else:
                s = val_ops.Stringify(val, rd.LeftParenToken(), 'str() ')
                return value.Str(s)


class List_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        l = []  # type: List[value_t]
        it = None  # type: val_ops.Iterator
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
                                    'list() expected Dict, List, or Range',
                                    rd.BlamePos())

        assert it is not None
        while True:
            first = it.FirstValue()
            if first is None:
                break
            l.append(first)
            it.Next()

        return value.List(l)


class DictFunc(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Dict):
                val = cast(value.Dict, UP_val)
                d = NewDict()  # type: Dict[str, value_t]
                for k, v in iteritems(val.d):
                    d[k] = v

                return value.Dict(d)

            elif case(value_e.Obj):
                val = cast(Obj, UP_val)
                d = NewDict()
                for k, v in iteritems(val.d):
                    d[k] = v

                return value.Dict(d)

            elif case(value_e.BashAssoc):
                val = cast(value.BashAssoc, UP_val)
                d = NewDict()
                for k, s in iteritems(val.d):
                    d[k] = value.Str(s)

                return value.Dict(d)

            elif case(value_e.Frame):
                val = cast(value.Frame, UP_val)
                d = NewDict()
                for k, cell in iteritems(val.frame):
                    d[k] = cell.val

                return value.Dict(d)

        raise error.TypeErr(val, 'dict() expected Dict, Obj, or BashAssoc',
                            rd.BlamePos())


class Runes(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null


class EncodeRunes(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null


class Bytes(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null


class EncodeBytes(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null


class Split(vm._Callable):

    def __init__(self, splitter):
        # type: (split.SplitContext) -> None
        vm._Callable.__init__(self)
        self.splitter = splitter

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        s = rd.PosStr()

        ifs = rd.OptionalStr()

        rd.Done()

        l = [
            value.Str(elem)
            for elem in self.splitter.SplitForWordEval(s, ifs=ifs)
        ]  # type: List[value_t]
        return value.List(l)


class FloatsEqual(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        left = rd.PosFloat()
        right = rd.PosFloat()
        rd.Done()

        return value.Bool(left == right)


class Glob(vm._Callable):

    def __init__(self, globber):
        # type: (glob_.Globber) -> None
        vm._Callable.__init__(self)
        self.globber = globber

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        s = rd.PosStr()
        rd.Done()

        out = []  # type: List[str]
        self.globber._Glob(s, out)

        l = [value.Str(elem) for elem in out]  # type: List[value_t]
        return value.List(l)


class ToJson8(vm._Callable):

    def __init__(self, is_j8):
        # type: (bool) -> None
        self.is_j8 = is_j8

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        space = mops.BigTruncate(rd.NamedInt('space', 0))
        rd.Done()

        # Convert from external JS-like API to internal API.
        if space <= 0:
            indent = -1
        else:
            indent = space

        buf = mylib.BufWriter()
        try:
            if self.is_j8:
                j8.PrintMessage(val, buf, indent)
            else:
                j8.PrintJsonMessage(val, buf, indent)
        except error.Encode as e:
            # status code 4 is special, for encode/decode errors.
            raise error.Structured(4, e.Message(), rd.LeftParenToken())

        return value.Str(buf.getvalue())


class FromJson8(vm._Callable):

    def __init__(self, is_j8):
        # type: (bool) -> None
        self.is_j8 = is_j8

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        s = rd.PosStr()
        rd.Done()

        p = j8.Parser(s, self.is_j8)
        try:
            val = p.ParseValue()
        except error.Decode as e:
            # Right now I'm not exposing the original string, because that
            # could lead to a memory leak in the _error Dict.
            # The message quotes part of the string, and we could improve
            # that.  We could have a substring with context.
            props = {
                'start_pos': num.ToBig(e.start_pos),
                'end_pos': num.ToBig(e.end_pos),
            }  # type: Dict[str, value_t]
            # status code 4 is special, for encode/decode errors.
            raise error.Structured(4, e.Message(), rd.LeftParenToken(), props)

        return val
