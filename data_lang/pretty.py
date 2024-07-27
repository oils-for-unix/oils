#!/usr/bin/env python2
"""
Pretty print Oils values (and later other data/languages as well).

Pretty printing means intelligently choosing whitespace including indentation
and newline placement, to attempt to display data nicely while staying within a
maximum line width.
"""

# ~~~ Architecture ~~~
#
# Based on a version of the algorithm from Wadler's "A Prettier Printer".
#
# Pretty printing proceeds in two phases:
#
# 1. Convert the thing you want to print into a `doc`.
# 2. Print the `doc` using a standard algorithm.
#
# This separation keeps the details of the data you want to print separate from
# the printing algorithm.

# ~~~ Pretty Printing Overview ~~~
#
# If you're just using this file, you don't need to know how pretty printing
# works. Just call `PrettyPrinter().PrintValue()`. However if you want to change
# or extend how values are printed, you'll need to know, so here's an overview.
#
# You may want to first read Walder's "A Prettier Printer", which this is based
# off of:
# https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf
#
# Some additional reading, though only tangentially related:
#
# - https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf
# - https://lindig.github.io/papers/strictly-pretty-2000.pdf
# - https://justinpombrio.net/2024/02/23/a-twist-on-Wadlers-printer.html
# - https://lobste.rs/s/1r0aak/twist_on_wadler_s_printer
# - https://lobste.rs/s/aevptj/why_is_prettier_rock_solid
#
# ~ Constructors ~
#
# There are just a few constructors for `doc`, from which everything else is
# built from.
#
# Text(string) prints like:
# |string
#
# Break(string) prints like:
# |string
# or like a newline:
# |
# |
# (It does the latter if printed in "flat" mode, and the former otherwise. See
# Group for details.)
#
# Concat(a, b) prints like:
# |AAAAA
# |AAABBB
# |BBBBB
#
# Indent(3, a) prints like:
# |AAAAA
# |   AAAAA
# |   AAAAA
#
# Group(a) makes a decision. It either:
# - Prints `a` "flat", meaning that (i) every Break inside of it is printed as a
#   string instead of as a newline, and (ii) every Group nested inside of it is
#   printed flat.
# - Prints `a` normally, meaning that (i) the Breaks inside of it are printed as
#   newlines, and (ii) the Groups inside of it make their own decision about
#   whether to be flat.
# It makes this decision greedily. If the current line would not overflow if the
# group printed flat, then it will print flat. This takes into account not only
# the group itself, but the content before and after it on the same line.
#
# IfFlat(a, b) prints a if in flat mode or b otherwise.
#
# Flat(a) prints a in flat mode. You should generally not need to use it.
#
# ~ Measures ~
#
# The algorithm used here is close to the one originally described by Wadler,
# but it precomputes a "measure" for each node in the `doc`. This "measure"
# allows each Groups to decide whether to print flat or not without needing to
# look ahead per Wadler's algorithm. A measure has two pieces of information:
#
# - Measure.flat is the width of the doc if it's printed flat.
# - Measure.nonflat is the width of the doc until the _earliest possible_
#   newline, or -1 if it doesn't contain a Break.
#
# Measures are used in two steps:
# (1) First, they're computed bottom-up on the `doc`, measuring the size of each
#     node.
# (2) Later, PrintDoc() stores a measure in each DocFragment. These Measures
#     measure something different: the width from the doc _to the end of the
#     entire doc tree_. This second set of Measures (the ones in the
#     DocFragments) are computed top-down, and they're used to decide for each
#     Group whether to use flat mode or not, without needing to scan ahead.

from __future__ import print_function

import math

from _devbuild.gen.pretty_asdl import doc, doc_e, DocFragment, Measure, MeasuredDoc
from _devbuild.gen.value_asdl import value, value_e, value_t, value_str
from data_lang import j8
from data_lang import j8_lite
from core import ansi
from frontend import match
from mycpp import mops
from mycpp.mylib import log, tagswitch, BufWriter, iteritems
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


################
# Measurements #
################


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


def _EmptyMeasure():
    # type: () -> Measure
    """The measure of an empty doc."""
    return Measure(0, -1)


def _FlattenMeasure(measure):
    # type: (Measure) -> Measure
    """The measure if its document is rendered flat."""
    return Measure(measure.flat, -1)


def _ConcatMeasure(m1, m2):
    # type: (Measure, Measure) -> Measure
    """Compute the measure of concatenated docs.

    If m1 and m2 are the measures of doc1 and doc2,
    then _ConcatMeasure(m1, m2) is the measure of doc.Concat([doc1, doc2]).
    This concatenation is associative but not commutative."""
    if m1.nonflat != -1:
        return Measure(m1.flat + m2.flat, m1.nonflat)
    elif m2.nonflat != -1:
        return Measure(m1.flat + m2.flat, m1.flat + m2.nonflat)
    else:
        return Measure(m1.flat + m2.flat, -1)


def _SuffixLen(measure):
    # type: (Measure) -> int
    """The width until the earliest possible newline, or end of document."""
    if measure.nonflat != -1:
        return measure.nonflat
    else:
        return measure.flat


####################
# Doc Construction #
####################


def _Text(string):
    # type: (str) -> MeasuredDoc
    """Print `string` (which must not contain a newline)."""
    return MeasuredDoc(doc.Text(string), Measure(TryUnicodeWidth(string), -1))


def _Break(string):
    # type: (str) -> MeasuredDoc
    """If in `flat` mode, print `string`, otherwise print `\n`."""
    return MeasuredDoc(doc.Break(string), Measure(TryUnicodeWidth(string), 0))


def _Indent(indent, mdoc):
    # type: (int, MeasuredDoc) -> MeasuredDoc
    """Add `indent` spaces after every newline in `mdoc`."""
    return MeasuredDoc(doc.Indent(indent, mdoc), mdoc.measure)


def _Concat(mdocs):
    # type: (List[MeasuredDoc]) -> MeasuredDoc
    """Print the mdocs in order (with no space in between)."""
    measure = _EmptyMeasure()
    for mdoc in mdocs:
        measure = _ConcatMeasure(measure, mdoc.measure)
    return MeasuredDoc(doc.Concat(mdocs), measure)


def _Group(mdoc):
    # type: (MeasuredDoc) -> MeasuredDoc
    """Print `mdoc`. Use flat mode if `mdoc` will fit on the current line."""
    return MeasuredDoc(doc.Group(mdoc), mdoc.measure)


def _IfFlat(flat_mdoc, nonflat_mdoc):
    # type: (MeasuredDoc, MeasuredDoc) -> MeasuredDoc
    """If in flat mode, print `flat_mdoc` otherwise print `nonflat_mdoc`."""
    return MeasuredDoc(
        doc.IfFlat(flat_mdoc, nonflat_mdoc),
        Measure(flat_mdoc.measure.flat, nonflat_mdoc.measure.nonflat))


def _Flat(mdoc):
    # type: (MeasuredDoc) -> MeasuredDoc
    """Prints `mdoc` in flat mode."""
    return MeasuredDoc(doc.Flat(mdoc), _FlattenMeasure(mdoc.measure))


###################
# Pretty Printing #
###################


class PrettyPrinter(object):
    """Pretty print an Oils value."""

    def __init__(self, max_width):
        # type: (int) -> None
        """Construct a PrettyPrinter with default configuration options.

        Use the Set*() methods for configuration before printing."""
        self.max_width = max_width

    def _Fits(self, prefix_len, group, suffix_measure):
        # type: (int, doc.Group, Measure) -> bool
        """Will `group` fit flat on the current line?"""
        measure = _ConcatMeasure(_FlattenMeasure(group.mdoc.measure),
                                 suffix_measure)
        return prefix_len + _SuffixLen(measure) <= self.max_width

    def PrintDoc(self, document, buf):
        # type: (MeasuredDoc, BufWriter) -> None
        """Pretty print a `pretty.doc` to a BufWriter."""

        # The width of the text we've printed so far on the current line
        prefix_len = 0
        # A _stack_ of document fragments to print. Each fragment contains:
        # - A MeasuredDoc (doc node and its measure, saying how "big" it is)
        # - The indentation level to print this doc node at.
        # - Is this doc node being printed in flat mode?
        # - The measure _from just after the doc node, to the end of the entire document_.
        #   (Call this the suffix_measure)
        fragments = [DocFragment(_Group(document), 0, False, _EmptyMeasure())]

        while len(fragments) > 0:
            frag = fragments.pop()
            with tagswitch(frag.mdoc.doc) as case:

                if case(doc_e.Text):
                    text = cast(doc.Text, frag.mdoc.doc)
                    buf.write(text.string)
                    prefix_len += frag.mdoc.measure.flat

                elif case(doc_e.Break):
                    if frag.is_flat:
                        break_str = cast(doc.Break, frag.mdoc.doc).string
                        buf.write(break_str)
                        prefix_len += frag.mdoc.measure.flat
                    else:
                        buf.write('\n')
                        buf.write_spaces(frag.indent)
                        prefix_len = frag.indent

                elif case(doc_e.Indent):
                    indented = cast(doc.Indent, frag.mdoc.doc)
                    fragments.append(
                        DocFragment(indented.mdoc,
                                    frag.indent + indented.indent,
                                    frag.is_flat, frag.measure))

                elif case(doc_e.Concat):
                    # If we encounter Concat([A, B, C]) with a suffix measure M,
                    # we need to push A,B,C onto the stack in reverse order:
                    # - C, with suffix_measure = B.measure + A.measure + M
                    # - B, with suffix_measure = A.measure + M
                    # - A, with suffix_measure = M
                    concat = cast(doc.Concat, frag.mdoc.doc)
                    measure = frag.measure
                    for mdoc in reversed(concat.mdocs):
                        fragments.append(
                            DocFragment(mdoc, frag.indent, frag.is_flat,
                                        measure))
                        measure = _ConcatMeasure(mdoc.measure, measure)

                elif case(doc_e.Group):
                    # If the group would fit on the current line when printed
                    # flat, do so. Otherwise, print it non-flat.
                    group = cast(doc.Group, frag.mdoc.doc)
                    flat = self._Fits(prefix_len, group, frag.measure)
                    fragments.append(
                        DocFragment(group.mdoc, frag.indent, flat,
                                    frag.measure))

                elif case(doc_e.IfFlat):
                    if_flat = cast(doc.IfFlat, frag.mdoc.doc)
                    if frag.is_flat:
                        subdoc = if_flat.flat_mdoc
                    else:
                        subdoc = if_flat.nonflat_mdoc
                    fragments.append(
                        DocFragment(subdoc, frag.indent, frag.is_flat,
                                    frag.measure))

                elif case(doc_e.Flat):
                    flat_doc = cast(doc.Flat, frag.mdoc.doc)
                    fragments.append(
                        DocFragment(flat_doc.mdoc, frag.indent, True,
                                    frag.measure))


################
# Value -> Doc #
################

_DEFAULT_INDENTATION = 4
_DEFAULT_USE_STYLES = True

# Tuned for 'data_lang/pretty-benchmark.sh float-demo'
# TODO: might want options for float width
_DEFAULT_MAX_TABULAR_WIDTH = 22


class ValueEncoder:
    """Converts Oils values into `doc`s, which can then be pretty printed."""

    def __init__(self):
        # type: () -> None
        self.indent = _DEFAULT_INDENTATION
        self.use_styles = _DEFAULT_USE_STYLES
        self.max_tabular_width = _DEFAULT_MAX_TABULAR_WIDTH
        self.ysh_style = False

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

    def SetYshStyle(self):
        # type: () -> None
        """Set the string literal style."""
        self.ysh_style = True

    def TypePrefix(self, type_str):
        # type: (str) -> List[MeasuredDoc]
        """Return a fragment for (List), which may break afterward."""
        type_name = self._Styled(self.type_style, _Text(type_str))
        mdocs = [_Text("("), type_name, _Text(")"), _Break("   ")]
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
                _Text(open),
                _Indent(self.indent, _Concat([_Break(""), mdoc])),
                _Break(""),
                _Text(close)
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
                _Text(open), prefix,
                _Indent(self.indent, _Concat([_Break(sep), mdoc])),
                _Break(""),
                _Text(close)
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
                seq.append(_Text(sep))
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
            return _Text("")

        max_flat_len = 0
        seq = []  # type: List[MeasuredDoc]
        for i, item in enumerate(items):
            if i != 0:
                seq.append(_Text(sep))
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
                    tabular_seq.append(_Text(sep))
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
        return _Text(encoded)

    def _StringLiteral(self, s):
        # type: (str) -> MeasuredDoc
        if self.ysh_style:
            # YSH r'' or b'' style
            encoded = j8_lite.YshEncodeString(s)
        else:
            # TODO: remove this dead branch after fixing tests
            encoded = j8_lite.EncodeString(s)
        return self._Styled(self.string_style, _Text(encoded))

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
        return self._Styled(self.string_style, _Text(encoded))

    def _YshList(self, vlist):
        # type: (value.List) -> MeasuredDoc
        """Print a string literal."""
        if len(vlist.items) == 0:
            return _Text("[]")
        mdocs = [self._Value(item) for item in vlist.items]
        return self._Surrounded("[", self._Tabular(mdocs, ","), "]")

    def _YshDict(self, vdict):
        # type: (value.Dict) -> MeasuredDoc
        if len(vdict.d) == 0:
            return _Text("{}")
        mdocs = []  # type: List[MeasuredDoc]
        for k, v in iteritems(vdict.d):
            mdocs.append(
                _Concat([self._DictKey(k),
                         _Text(": "),
                         self._Value(v)]))
        return self._Surrounded("{", self._Join(mdocs, ",", " "), "}")

    def _BashArray(self, varray):
        # type: (value.BashArray) -> MeasuredDoc
        type_name = self._Styled(self.type_style, _Text("BashArray"))
        if len(varray.strs) == 0:
            return _Concat([_Text("("), type_name, _Text(")")])
        mdocs = []  # type: List[MeasuredDoc]
        for s in varray.strs:
            if s is None:
                mdocs.append(_Text("null"))
            else:
                mdocs.append(self._BashStringLiteral(s))
        return self._SurroundedAndPrefixed("(", type_name, " ",
                                           self._Tabular(mdocs, ""), ")")

    def _BashAssoc(self, vassoc):
        # type: (value.BashAssoc) -> MeasuredDoc
        type_name = self._Styled(self.type_style, _Text("BashAssoc"))
        if len(vassoc.d) == 0:
            return _Concat([_Text("("), type_name, _Text(")")])
        mdocs = []  # type: List[MeasuredDoc]
        for k2, v2 in iteritems(vassoc.d):
            mdocs.append(
                _Concat([
                    _Text("["),
                    self._BashStringLiteral(k2),
                    _Text("]="),
                    self._BashStringLiteral(v2)
                ]))
        return self._SurroundedAndPrefixed("(", type_name, " ",
                                           self._Join(mdocs, "", " "), ")")

    def _SparseArray(self, val):
        # type: (value.SparseArray) -> MeasuredDoc
        type_name = self._Styled(self.type_style, _Text("SparseArray"))
        if len(val.d) == 0:
            return _Concat([_Text("("), type_name, _Text(")")])
        mdocs = []  # type: List[MeasuredDoc]
        for k2, v2 in iteritems(val.d):
            mdocs.append(
                _Concat([
                    _Text("["),
                    self._Styled(self.int_style, _Text(mops.ToStr(k2))),
                    _Text("]="),
                    self._BashStringLiteral(v2)
                ]))
        return self._SurroundedAndPrefixed("(", type_name, " ",
                                           self._Join(mdocs, "", " "), ")")

    def _Value(self, val):
        # type: (value_t) -> MeasuredDoc

        with tagswitch(val) as case:
            if case(value_e.Null):
                return self._Styled(self.null_style, _Text("null"))

            elif case(value_e.Bool):
                b = cast(value.Bool, val).b
                return self._Styled(self.bool_style,
                                    _Text("true" if b else "false"))

            elif case(value_e.Int):
                i = cast(value.Int, val).i
                return self._Styled(self.int_style, _Text(mops.ToStr(i)))

            elif case(value_e.Float):
                f = cast(value.Float, val).f
                return self._Styled(self.float_style, _Text(_FloatString(f)))

            elif case(value_e.Str):
                s = cast(value.Str, val).s
                return self._StringLiteral(s)

            elif case(value_e.Range):
                r = cast(value.Range, val)
                type_name = self._Styled(self.type_style, _Text(ValType(r)))
                mdocs = [_Text(str(r.lower)), _Text(".."), _Text(str(r.upper))]
                return self._SurroundedAndPrefixed("(", type_name, " ",
                                                   self._Join(mdocs, "", " "),
                                                   ")")

            elif case(value_e.List):
                vlist = cast(value.List, val)
                heap_id = j8.HeapValueId(vlist)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        _Text("["),
                        self._Styled(self.cycle_style, _Text("...")),
                        _Text("]")
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
                        _Text("{"),
                        self._Styled(self.cycle_style, _Text("...")),
                        _Text("}")
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
                type_name = self._Styled(self.type_style, _Text(ValType(val)))
                id_str = j8.ValueIdString(val)
                return _Concat([_Text("<"), type_name, _Text(id_str + ">")])


# vim: sw=4
