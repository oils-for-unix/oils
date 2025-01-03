#!/usr/bin/env python2
from __future__ import print_function
"""
Render Oils value_t -> doc_t, so it can be pretty printed
"""

import math

from _devbuild.gen.pretty_asdl import (doc, Measure, MeasuredDoc)
from _devbuild.gen.runtime_asdl import error_code_e
from _devbuild.gen.value_asdl import Obj, value, value_e, value_t, value_str
from core import bash_impl
from data_lang import j8
from data_lang import j8_lite
from display import ansi
from display import pp_hnode
from display.pretty import _Break, _Concat, AsciiText
from frontend import match
from mycpp import mops
from mycpp.mylib import log, tagswitch, iteritems
from typing import cast, List, Dict

import libc

_ = log


def ValType(val):
    # type: (value_t) -> str
    """Returns a user-facing string like Int, Eggex, BashArray, etc."""
    return value_str(val.tag(), dot=False)


def FloatString(fl):
    # type: (float) -> str

    # Print in YSH syntax, similar to data_lang/j8.py
    if math.isinf(fl):
        s = 'INFINITY'
        if fl < 0:
            s = '-' + s
    elif math.isnan(fl):
        s = 'NAN'
    else:
        s = str(fl)
    return s


#
# Unicode Helpers
#


def TryUnicodeWidth(s):
    # type: (str) -> int
    try:
        width = libc.wcswidth(s)
    except UnicodeError:
        # e.g. en_US.UTF-8 locale missing, just return the number of bytes
        width = len(s)

    if width == -1:  # non-printable wide char
        return len(s)

    return width


def UText(string):
    # type: (str) -> MeasuredDoc
    """Print `string` (which must not contain a newline)."""
    return MeasuredDoc(doc.Text(string), Measure(TryUnicodeWidth(string), -1))


class ValueEncoder(pp_hnode.BaseEncoder):
    """Converts Oils values into `doc`s, which can then be pretty printed."""

    def __init__(self):
        # type: () -> None
        pp_hnode.BaseEncoder.__init__(self)
        self.ysh_style = True

        # These can be configurable later
        self.int_style = ansi.YELLOW
        self.float_style = ansi.BLUE
        self.null_style = ansi.RED
        self.bool_style = ansi.CYAN
        self.string_style = ansi.GREEN
        self.cycle_style = ansi.BOLD + ansi.BLUE
        self.type_style = ansi.MAGENTA

    def TypePrefix(self, type_str):
        # type: (str) -> List[MeasuredDoc]
        """Return docs for type string '(List)', which may break afterward."""
        type_name = self._Styled(self.type_style, AsciiText(type_str))

        n = len(type_str)
        # Our maximum string is 'Float'
        assert n <= 5, type_str

        # Start printing in column 8.   Adjust to 6 because () takes 2 spaces.
        spaces = ' ' * (6 - n)

        mdocs = [AsciiText('('), type_name, AsciiText(')'), _Break(spaces)]
        return mdocs

    def Value(self, val):
        # type: (value_t) -> MeasuredDoc
        """Convert an Oils value into a `doc`, which can then be pretty printed."""
        self.visiting.clear()
        return self._Value(val)

    def _DictKey(self, s):
        # type: (str) -> MeasuredDoc
        if match.IsValidVarName(s):
            encoded = s
        else:
            if self.ysh_style:
                encoded = j8_lite.YshEncodeString(s)
            else:
                # TODO: remove this dead branch after fixing tests
                encoded = j8_lite.EncodeString(s)
        return UText(encoded)

    def _StringLiteral(self, s):
        # type: (str) -> MeasuredDoc
        if self.ysh_style:
            # YSH r'' or b'' style
            encoded = j8_lite.YshEncodeString(s)
        else:
            # TODO: remove this dead branch after fixing tests
            encoded = j8_lite.EncodeString(s)
        return self._Styled(self.string_style, UText(encoded))

    def _BashStringLiteral(self, s):
        # type: (str) -> MeasuredDoc

        # '' or $'' style
        #
        # We mimic bash syntax by using $'\\' instead of b'\\'
        #
        # $ declare -a array=($'\\')
        # $ = array
        # (BashArray)   (BashArray $'\\')
        #
        # $ declare -A assoc=([k]=$'\\')
        # $ = assoc
        # (BashAssoc)   (BashAssoc ['k']=$'\\')

        encoded = j8_lite.ShellEncode(s)
        return self._Styled(self.string_style, UText(encoded))

    def _YshList(self, vlist):
        # type: (value.List) -> MeasuredDoc
        """Print a string literal."""
        if len(vlist.items) == 0:
            return AsciiText('[]')
        mdocs = [self._Value(item) for item in vlist.items]
        return self._Surrounded('[', self._Tabular(mdocs, ','), ']')

    def _DictMdocs(self, d):
        # type: (Dict[str, value_t]) -> List[MeasuredDoc]
        mdocs = []  # type: List[MeasuredDoc]
        for k, v in iteritems(d):
            mdocs.append(
                _Concat([self._DictKey(k),
                         AsciiText(': '),
                         self._Value(v)]))
        return mdocs

    def _YshDict(self, vdict):
        # type: (value.Dict) -> MeasuredDoc
        if len(vdict.d) == 0:
            return AsciiText('{}')
        mdocs = self._DictMdocs(vdict.d)
        return self._Surrounded('{', self._Join(mdocs, ',', ' '), '}')

    def _BashArray(self, varray):
        # type: (value.BashArray) -> MeasuredDoc
        type_name = self._Styled(self.type_style, AsciiText('BashArray'))
        if bash_impl.BashArray_Count(varray) == 0:
            return _Concat([AsciiText('('), type_name, AsciiText(')')])
        mdocs = []  # type: List[MeasuredDoc]
        for s in bash_impl.BashArray_GetValues(varray):
            if s is None:
                mdocs.append(AsciiText('null'))
            else:
                mdocs.append(self._BashStringLiteral(s))
        return self._SurroundedAndPrefixed('(', type_name, ' ',
                                           self._Tabular(mdocs, ''), ')')

    def _BashAssoc(self, vassoc):
        # type: (value.BashAssoc) -> MeasuredDoc
        type_name = self._Styled(self.type_style, AsciiText('BashAssoc'))
        if bash_impl.BashAssoc_Count(vassoc) == 0:
            return _Concat([AsciiText('('), type_name, AsciiText(')')])
        mdocs = []  # type: List[MeasuredDoc]
        for k2, v2 in iteritems(bash_impl.BashAssoc_GetDict(vassoc)):
            mdocs.append(
                _Concat([
                    AsciiText('['),
                    self._BashStringLiteral(k2),
                    AsciiText(']='),
                    self._BashStringLiteral(v2)
                ]))
        return self._SurroundedAndPrefixed('(', type_name, ' ',
                                           self._Join(mdocs, '', ' '), ')')

    def _SparseArray(self, val):
        # type: (value.SparseArray) -> MeasuredDoc
        type_name = self._Styled(self.type_style, AsciiText('SparseArray'))
        if bash_impl.SparseArray_Count(val) == 0:
            return _Concat([AsciiText('('), type_name, AsciiText(')')])
        mdocs = []  # type: List[MeasuredDoc]
        for k2 in bash_impl.SparseArray_GetKeys(val):
            v2, error_code = bash_impl.SparseArray_GetElement(val, k2)
            assert error_code == error_code_e.OK, error_code
            mdocs.append(
                _Concat([
                    AsciiText('['),
                    self._Styled(self.int_style, AsciiText(mops.ToStr(k2))),
                    AsciiText(']='),
                    self._BashStringLiteral(v2)
                ]))
        return self._SurroundedAndPrefixed('(', type_name, ' ',
                                           self._Join(mdocs, '', ' '), ')')

    def _Obj(self, obj):
        # type: (Obj) -> MeasuredDoc
        chain = []  # type: List[MeasuredDoc]
        cur = obj
        while cur is not None:
            mdocs = self._DictMdocs(cur.d)
            chain.append(
                self._Surrounded('(', self._Join(mdocs, ',', ' '), ')'))
            cur = cur.prototype
            if cur is not None:
                chain.append(AsciiText(' --> '))

        return _Concat(chain)

    def _Value(self, val):
        # type: (value_t) -> MeasuredDoc

        with tagswitch(val) as case:
            if case(value_e.Null):
                return self._Styled(self.null_style, AsciiText('null'))

            elif case(value_e.Bool):
                b = cast(value.Bool, val).b
                return self._Styled(self.bool_style,
                                    AsciiText('true' if b else 'false'))

            elif case(value_e.Int):
                i = cast(value.Int, val).i
                return self._Styled(self.int_style, AsciiText(mops.ToStr(i)))

            elif case(value_e.Float):
                f = cast(value.Float, val).f
                return self._Styled(self.float_style,
                                    AsciiText(FloatString(f)))

            elif case(value_e.Str):
                s = cast(value.Str, val).s
                return self._StringLiteral(s)

            elif case(value_e.Range):
                r = cast(value.Range, val)
                type_name = self._Styled(self.type_style,
                                         AsciiText(ValType(r)))
                mdocs = [
                    AsciiText(str(r.lower)),
                    AsciiText('..<'),
                    AsciiText(str(r.upper))
                ]
                return self._SurroundedAndPrefixed('(', type_name, ' ',
                                                   self._Join(mdocs, '', ' '),
                                                   ')')

            elif case(value_e.List):
                vlist = cast(value.List, val)
                heap_id = j8.HeapValueId(vlist)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        AsciiText('['),
                        self._Styled(self.cycle_style, AsciiText('...')),
                        AsciiText(']')
                    ])
                else:
                    self.visiting[heap_id] = True
                    result = self._YshList(vlist)
                    self.visiting[heap_id] = False
                    return result

            elif case(value_e.Dict):
                vdict = cast(value.Dict, val)
                heap_id = j8.HeapValueId(vdict)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        AsciiText('{'),
                        self._Styled(self.cycle_style, AsciiText('...')),
                        AsciiText('}')
                    ])
                else:
                    self.visiting[heap_id] = True
                    result = self._YshDict(vdict)
                    self.visiting[heap_id] = False
                    return result

            elif case(value_e.SparseArray):
                sparse = cast(value.SparseArray, val)
                return self._SparseArray(sparse)

            elif case(value_e.BashArray):
                varray = cast(value.BashArray, val)
                return self._BashArray(varray)

            elif case(value_e.BashAssoc):
                vassoc = cast(value.BashAssoc, val)
                return self._BashAssoc(vassoc)

            elif case(value_e.Obj):
                vaobj = cast(Obj, val)
                heap_id = j8.HeapValueId(vaobj)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        AsciiText('('),
                        self._Styled(self.cycle_style, AsciiText('...')),
                        AsciiText(')')
                    ])
                else:
                    self.visiting[heap_id] = True
                    result = self._Obj(vaobj)
                    self.visiting[heap_id] = False
                    return result

            # Bug fix: these types are GLOBAL singletons in C++.  This means
            # they have no object ID, so j8.ValueIdString() will CRASH on them.

            elif case(value_e.Stdin, value_e.Interrupted):
                type_name = self._Styled(self.type_style,
                                         AsciiText(ValType(val)))
                return _Concat([AsciiText('<'), type_name, AsciiText('>')])

            else:
                type_name = self._Styled(self.type_style,
                                         AsciiText(ValType(val)))
                id_str = j8.ValueIdString(val)
                return _Concat(
                    [AsciiText('<'), type_name,
                     AsciiText(id_str + '>')])


# vim: sw=4
