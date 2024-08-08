#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (scope_e)
from _devbuild.gen.value_asdl import (value, value_e, value_t, value_str,
                                      Dict_)

from core import error
from core import num
from core import state
from display import pp_value
from display import ui
from core import vm
from data_lang import j8
from frontend import match
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import NewDict, iteritems, log, tagswitch
from ysh import expr_eval
from ysh import val_ops

from typing import TYPE_CHECKING, Dict, List, cast
if TYPE_CHECKING:
    from osh import glob_
    from osh import split

_ = log


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
                x = cast(Dict_, UP_x)
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
            strs.append(val_ops.Stringify(el, rd.LeftParenToken()))

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
                if not match.LooksLikeInteger(val.s):
                    raise error.Expr("Can't convert %s to Int" % val.s,
                                     rd.BlamePos())

                return value.Int(mops.FromStr(val.s))

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
                if not match.LooksLikeFloat(val.s):
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

        # TODO: Should we call Stringify here?  That would handle Eggex.

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Str(mops.ToStr(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Str(str(val.f))

            elif case(value_e.Str):
                return val

        raise error.TypeErr(val, 'str() expected Str, Int, or Float',
                            rd.BlamePos())


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
                val = cast(Dict_, UP_val)
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
                d = NewDict()  # type: Dict[str, value_t]
                val = cast(Dict_, UP_val)
                for k, v in iteritems(val.d):
                    d[k] = v

                return Dict_(d, None)

            elif case(value_e.BashAssoc):
                d = NewDict()
                val = cast(value.BashAssoc, UP_val)
                for k, s in iteritems(val.d):
                    d[k] = value.Str(s)

                return Dict_(d, None)

        raise error.TypeErr(val, 'dict() expected Dict or BashAssoc',
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


class Shvar_get(vm._Callable):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return state.DynamicGetVar(self.mem, name, scope_e.Dynamic)


class GetVar(vm._Callable):
    """Look up normal scoping rules."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return state.DynamicGetVar(self.mem, name, scope_e.LocalOrGlobal)


class EvalExpr(vm._Callable):

    def __init__(self, expr_ev):
        # type: (expr_eval.ExprEvaluator) -> None
        self.expr_ev = expr_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        lazy = rd.PosExpr()
        rd.Done()

        result = self.expr_ev.EvalExpr(lazy, rd.LeftParenToken())

        return result


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


class BashArrayToSparse(vm._Callable):
    """
    value.BashArray -> value.SparseArray, for testing
    """

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        strs = rd.PosBashArray()
        rd.Done()

        d = {}  # type: Dict[mops.BigInt, str]
        max_index = mops.MINUS_ONE  # max index for empty array
        for i, s in enumerate(strs):
            if s is not None:
                big_i = mops.IntWiden(i)
                d[big_i] = s
                if mops.Greater(big_i, max_index):
                    max_index = big_i

        return value.SparseArray(d, max_index)


class SparseOp(vm._Callable):
    """
    All ops on value.SparseArray, for testing performance
    """

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        sp = rd.PosSparseArray()
        d = sp.d
        #i = mops.BigTruncate(rd.PosInt())
        op_name = rd.PosStr()

        no_str = None  # type: str

        if op_name == 'len':  # ${#a[@]}
            rd.Done()
            return num.ToBig(len(d))

        elif op_name == 'get':  # ${a[42]}
            index = rd.PosInt()
            rd.Done()

            s = d.get(index)
            if s is None:
                return value.Null
            else:
                return value.Str(s)

        elif op_name == 'set':  # a[42]=foo
            index = rd.PosInt()
            s = rd.PosStr()
            rd.Done()

            d[index] = s

            if mops.Greater(index, sp.max_index):
                sp.max_index = index

            return value.Int(mops.ZERO)

        elif op_name == 'unset':  # unset 'a[1]'
            index = rd.PosInt()
            rd.Done()

            mylib.dict_erase(d, index)

            max_index = mops.MINUS_ONE  # Note: this works if d is not empty
            for i1 in d:
                if mops.Greater(i1, max_index):  # i1 > max_index
                    max_index = i1
            sp.max_index = max_index

            return value.Int(mops.ZERO)

        elif op_name == 'subst':  # "${a[@]}"
            # Algorithm to expand a Dict[BigInt, Str]
            #
            # 1. Copy the integer keys into a new List
            # 2. Sort them in numeric order
            # 3. Create a List[str] that's the same size as the keys
            # 4. Loop through sorted keys, look up value, and populate list
            #
            # There is another possible algorithm:
            #
            # 1. Copy the VALUES into a new list
            # 2. Somehow sort them by the CORRESPONDING key, which depends on
            #    Slab<> POSITION.  I think this does not fit within the
            #    std::sort() model.  I think we would have to write a little custom
            #    sort algorithm.

            keys = d.keys()
            mylib.BigIntSort(keys)
            # Pre-allocate
            items = [no_str] * len(d)  # type: List[str]
            j = 0
            for i in keys:
                s = d.get(i)
                assert s is not None
                items[j] = s
                j += 1
            return value.BashArray(items)

        elif op_name == 'keys':  # "${!a[@]}"
            keys = d.keys()
            mylib.BigIntSort(keys)
            items = [mops.ToStr(k) for k in keys]

            # TODO: return SparseArray
            return value.BashArray(items)

        elif op_name == 'slice':  # "${a[@]:0:5}"
            start = rd.PosInt()
            end = rd.PosInt()
            rd.Done()

            n = mops.BigTruncate(mops.Sub(end, start))
            #log('start %d - end %d', start.i, end.i)

            # Pre-allocate
            items2 = [no_str] * n  # type: List[str]

            # Iterate from start to end.  Note that this algorithm is
            # theoretically slower than bash in the case where the array is
            # sparse (in the part selected by the slice)
            #
            # e.g. if you do ${a[@]:1:1000} e.g. to SHIFT, and there are only 3
            # elements, OSH will iterate through 999 integers and do 999 dict
            # lookups, while bash will follow 3 pointers.
            #
            # However, in practice, I think iterating through integers is
            # cheap.

            j = 0
            i = start
            while mops.Greater(end, i):  # i < end
                s = d.get(i)
                #log('s %s', s)
                if s is not None:
                    items2[j] = s
                    j += 1

                i = mops.Add(i, mops.ONE)  # i += 1

            # TODO: return SparseArray
            return value.BashArray(items2)

        elif op_name == 'append':  # a+=(x y)
            strs = rd.PosBashArray()

            # TODO: We can maintain the max index in the value.SparseArray(),
            # so that it's O(1) to append rather than O(n)
            # - Update on 'set' is O(1)
            # - Update on 'unset' is potentially O(n)

            if 0:
                max_index = mops.MINUS_ONE  # Note: this works for empty arrays
                for i1 in d:
                    if mops.Greater(i1, max_index):  # i1 > max_index
                        max_index = i1
            else:
                max_index = sp.max_index

            i2 = mops.Add(max_index, mops.ONE)  # i2 = max_index + 1
            for s in strs:
                d[i2] = s
                i2 = mops.Add(i2, mops.ONE)  # i2 += 1

            # sp.max_index += len(strs)
            sp.max_index = mops.Add(sp.max_index, mops.IntWiden(len(strs)))
            return value.Int(mops.ZERO)

        else:
            print('Invalid SparseArray operation %r' % op_name)
            return value.Int(mops.ZERO)
