#!/usr/bin/env python2
"""
Render Oils value_t -> doc_t, so it can be pretty printed
"""

from __future__ import print_function

import math

from _devbuild.gen.pretty_asdl import (doc, Measure, MeasuredDoc)
from _devbuild.gen.value_asdl import value, value_e, value_t, value_str
from data_lang import j8
from data_lang import j8_lite
from display.pretty import (_Break, _Concat, _Flat, _Group, _IfFlat, _Indent,
                            _EmptyMeasure)
from display import ansi
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


def _FloatString(fl):
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


class ValueEncoder:
    """Converts Oils values into `doc`s, which can then be pretty printed."""

    def __init__(self):
        # type: () -> None

        # Default values
        self.indent = 4
        self.use_styles = True
        # Tuned for 'data_lang/pretty-benchmark.sh float-demo'
        # TODO: might want options for float width
        self.max_tabular_width = 22

        self.ysh_style = True

        self.visiting = {}  # type: Dict[int, bool]

        # These can be configurable later
        self.int_style = ansi.YELLOW
        self.float_style = ansi.BLUE
        self.null_style = ansi.RED
        self.bool_style = ansi.CYAN
        self.string_style = ansi.GREEN
        self.cycle_style = ansi.BOLD + ansi.BLUE
        self.type_style = ansi.MAGENTA

    def SetIndent(self, indent):
        # type: (int) -> None
        """Set the number of spaces per indent."""
        self.indent = indent

    def SetUseStyles(self, use_styles):
        # type: (bool) -> None
        """Print with ansi colors and styles, rather than plain text."""
        self.use_styles = use_styles

    def SetMaxTabularWidth(self, max_tabular_width):
        # type: (int) -> None
        """Set the maximum width that list elements can be, for them to be
        vertically aligned."""
        self.max_tabular_width = max_tabular_width

    def TypePrefix(self, type_str):
        # type: (str) -> List[MeasuredDoc]
        """Return docs for type string "(List)", which may break afterward."""
        type_name = self._Styled(self.type_style, UText(type_str))

        n = len(type_str)
        # Our maximum string is "Float"
        assert n <= 5, type_str

        # Start printing in column 8.   Adjust to 6 because () takes 2 spaces.
        spaces = ' ' * (6 - n)

        mdocs = [UText("("), type_name, UText(")"), _Break(spaces)]
        return mdocs

    def Value(self, val):
        # type: (value_t) -> MeasuredDoc
        """Convert an Oils value into a `doc`, which can then be pretty printed."""
        self.visiting.clear()
        return self._Value(val)

    def _Styled(self, style, mdoc):
        # type: (str, MeasuredDoc) -> MeasuredDoc
        """Apply the ANSI style string to the given node, if use_styles is set."""
        if self.use_styles:
            return _Concat([
                MeasuredDoc(doc.Text(style), _EmptyMeasure()), mdoc,
                MeasuredDoc(doc.Text(ansi.RESET), _EmptyMeasure())
            ])
        else:
            return mdoc

    def _Surrounded(self, open, mdoc, close):
        # type: (str, MeasuredDoc, str) -> MeasuredDoc
        """Print one of two options (using '[', ']' for open, close):
    
        ```
        [mdoc]
        ------
        [
            mdoc
        ]
        ```
        """
        return _Group(
            _Concat([
                UText(open),
                _Indent(self.indent, _Concat([_Break(""), mdoc])),
                _Break(""),
                UText(close)
            ]))

    def _SurroundedAndPrefixed(self, open, prefix, sep, mdoc, close):
        # type: (str, MeasuredDoc, str, MeasuredDoc, str) -> MeasuredDoc
        """Print one of two options
        (using '[', 'prefix', ':', 'mdoc', ']' for open, prefix, sep, mdoc, close):

        ```
        [prefix:mdoc]
        ------
        [prefix
            mdoc
        ]
        ```
        """
        return _Group(
            _Concat([
                UText(open), prefix,
                _Indent(self.indent, _Concat([_Break(sep), mdoc])),
                _Break(""),
                UText(close)
            ]))

    def _Join(self, items, sep, space):
        # type: (List[MeasuredDoc], str, str) -> MeasuredDoc
        """Join `items`, using either 'sep+space' or 'sep+newline' between them.

        E.g., if sep and space are ',' and '_', print one of these two cases:
        ```
        first,_second,_third
        ------
        first,
        second,
        third
        ```
        """
        seq = []  # type: List[MeasuredDoc]
        for i, item in enumerate(items):
            if i != 0:
                seq.append(UText(sep))
                seq.append(_Break(space))
            seq.append(item)
        return _Concat(seq)

    def _Tabular(self, items, sep):
        # type: (List[MeasuredDoc], str) -> MeasuredDoc
        """Join `items` together, using one of three styles:

        (showing spaces as underscores for clarity)
        ```
        first,_second,_third,_fourth,_fifth,_sixth,_seventh,_eighth
        ------
        first,___second,__third,
        fourth,__fifth,___sixth,
        seventh,_eighth
        ------
        first,
        second,
        third,
        fourth,
        fifth,
        sixth,
        seventh,
        eighth
        ```

        The first "single line" style is used if the items fit on one line.  The
        second "tabular' style is used if the flat width of all items is no
        greater than `self.max_tabular_width`. The third "multi line" style is
        used otherwise.
        """

        # Why not "just" use tabular alignment so long as two items fit on every
        # line?  Because it isn't possible to check for that in the pretty
        # printing language. There are two sorts of conditionals we can do:
        #
        # A. Inside the pretty printing language, which supports exactly one
        #    conditional: "does it fit on one line?".
        # B. Outside the pretty printing language we can run arbitrary Python
        #    code, but we don't know how much space is available on the line
        #    because it depends on the context in which we're printed, which may
        #    vary.
        #
        # We're picking between the three styles, by using (A) to check if the
        # first style fits on one line, then using (B) with "are all the items
        # smaller than `self.max_tabular_width`?" to pick between style 2 and
        # style 3.

        if len(items) == 0:
            return UText("")

        max_flat_len = 0
        seq = []  # type: List[MeasuredDoc]
        for i, item in enumerate(items):
            if i != 0:
                seq.append(UText(sep))
                seq.append(_Break(" "))
            seq.append(item)
            max_flat_len = max(max_flat_len, item.measure.flat)
        non_tabular = _Concat(seq)

        sep_width = TryUnicodeWidth(sep)
        if max_flat_len + sep_width + 1 <= self.max_tabular_width:
            tabular_seq = []  # type: List[MeasuredDoc]
            for i, item in enumerate(items):
                tabular_seq.append(_Flat(item))
                if i != len(items) - 1:
                    padding = max_flat_len - item.measure.flat + 1
                    tabular_seq.append(UText(sep))
                    tabular_seq.append(_Group(_Break(" " * padding)))
            tabular = _Concat(tabular_seq)
            return _Group(_IfFlat(non_tabular, tabular))
        else:
            return non_tabular

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
            return UText("[]")
        mdocs = [self._Value(item) for item in vlist.items]
        return self._Surrounded("[", self._Tabular(mdocs, ","), "]")

    def _YshDict(self, vdict):
        # type: (value.Dict) -> MeasuredDoc
        if len(vdict.d) == 0:
            return UText("{}")
        mdocs = []  # type: List[MeasuredDoc]
        for k, v in iteritems(vdict.d):
            mdocs.append(
                _Concat([self._DictKey(k),
                         UText(": "),
                         self._Value(v)]))
        return self._Surrounded("{", self._Join(mdocs, ",", " "), "}")

    def _BashArray(self, varray):
        # type: (value.BashArray) -> MeasuredDoc
        type_name = self._Styled(self.type_style, UText("BashArray"))
        if len(varray.strs) == 0:
            return _Concat([UText("("), type_name, UText(")")])
        mdocs = []  # type: List[MeasuredDoc]
        for s in varray.strs:
            if s is None:
                mdocs.append(UText("null"))
            else:
                mdocs.append(self._BashStringLiteral(s))
        return self._SurroundedAndPrefixed("(", type_name, " ",
                                           self._Tabular(mdocs, ""), ")")

    def _BashAssoc(self, vassoc):
        # type: (value.BashAssoc) -> MeasuredDoc
        type_name = self._Styled(self.type_style, UText("BashAssoc"))
        if len(vassoc.d) == 0:
            return _Concat([UText("("), type_name, UText(")")])
        mdocs = []  # type: List[MeasuredDoc]
        for k2, v2 in iteritems(vassoc.d):
            mdocs.append(
                _Concat([
                    UText("["),
                    self._BashStringLiteral(k2),
                    UText("]="),
                    self._BashStringLiteral(v2)
                ]))
        return self._SurroundedAndPrefixed("(", type_name, " ",
                                           self._Join(mdocs, "", " "), ")")

    def _SparseArray(self, val):
        # type: (value.SparseArray) -> MeasuredDoc
        type_name = self._Styled(self.type_style, UText("SparseArray"))
        if len(val.d) == 0:
            return _Concat([UText("("), type_name, UText(")")])
        mdocs = []  # type: List[MeasuredDoc]
        for k2, v2 in iteritems(val.d):
            mdocs.append(
                _Concat([
                    UText("["),
                    self._Styled(self.int_style, UText(mops.ToStr(k2))),
                    UText("]="),
                    self._BashStringLiteral(v2)
                ]))
        return self._SurroundedAndPrefixed("(", type_name, " ",
                                           self._Join(mdocs, "", " "), ")")

    def _Value(self, val):
        # type: (value_t) -> MeasuredDoc

        with tagswitch(val) as case:
            if case(value_e.Null):
                return self._Styled(self.null_style, UText("null"))

            elif case(value_e.Bool):
                b = cast(value.Bool, val).b
                return self._Styled(self.bool_style,
                                    UText("true" if b else "false"))

            elif case(value_e.Int):
                i = cast(value.Int, val).i
                return self._Styled(self.int_style, UText(mops.ToStr(i)))

            elif case(value_e.Float):
                f = cast(value.Float, val).f
                return self._Styled(self.float_style, UText(_FloatString(f)))

            elif case(value_e.Str):
                s = cast(value.Str, val).s
                return self._StringLiteral(s)

            elif case(value_e.Range):
                r = cast(value.Range, val)
                type_name = self._Styled(self.type_style, UText(ValType(r)))
                mdocs = [UText(str(r.lower)), UText(".."), UText(str(r.upper))]
                return self._SurroundedAndPrefixed("(", type_name, " ",
                                                   self._Join(mdocs, "", " "),
                                                   ")")

            elif case(value_e.List):
                vlist = cast(value.List, val)
                heap_id = j8.HeapValueId(vlist)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        UText("["),
                        self._Styled(self.cycle_style, UText("...")),
                        UText("]")
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
                        UText("{"),
                        self._Styled(self.cycle_style, UText("...")),
                        UText("}")
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

            else:
                type_name = self._Styled(self.type_style, UText(ValType(val)))
                id_str = j8.ValueIdString(val)
                return _Concat([UText("<"), type_name, UText(id_str + ">")])


# vim: sw=4
