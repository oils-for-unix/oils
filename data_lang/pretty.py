#!/usr/bin/env python2

"""
Pretty print Oils values (and later other data/languages as well).

(Pretty printing means intelligently choosing whitespace including indentation
and newline placement, to attempt to display data nicely while staying within a
maximum line width.)
"""

# ~~~ Architecture ~~~
#
# Based on a string version of the algorithm from Wadler's "A Prettier Printer".
#
# Pretty printing proceeds in two phases:
#
# 1. Convert the thing you want to print into a `doc`.
# 2. Print the `doc` using a standard algorithm.
#
# This separation keeps the details of the data you want to print separate from
# the printing algorithm.
#
# Some relevant links:
#
# - https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf
# - https://lindig.github.io/papers/strictly-pretty-2000.pdf
# - https://justinpombrio.net/2024/02/23/a-twist-on-Wadlers-printer.html
# - https://lobste.rs/s/1r0aak/twist_on_wadler_s_printer
# - https://lobste.rs/s/aevptj/why_is_prettier_rock_solid

# ~~~ Algorithm Description ~~~
#
# [FILL]


from __future__ import print_function

from _devbuild.gen.pretty_asdl import doc, doc_e, doc_t, DocFragment, Measure, MeasuredDoc
from _devbuild.gen.value_asdl import value, value_e, value_t, value_str

from data_lang.j8 import ValueIdString, HeapValueId
from typing import cast, List, Dict, Callable #, Tuple Optional
from core import ansi
from libc import wcswidth

import fastfunc
import re

from mycpp import mops
from mycpp.mylib import log, tagswitch, BufWriter, iteritems

_ = log

# TODO:
# Later:
# - [ ] clean up imports (is there a lint that checks for unused imports?)
# - [ ] run the linter
# - [ ] what's with `_ = log`?
# - [ ] contributing page: PRs are squash-merged with a descriptive tag like [json]
# Between:
# - [ ] fill in ~Algorithm Description~
# - [ ] hook up the printer in core/ui.py::PrettyPrintValue
# - [ ] test cyclic values
# - [x] test styles (how?)
# - [ ] tabular alignment for list elements
# - [x] float prints with '.'
# - [ ] print type at top level, newline after type if multiline
# Now:
# - [x] string width
# - [x] Unquote identifier-y dict keys
# - [x] Add some style
# - [ ] Test BashArray and BashAssoc
# - [x] Show cycles as [...]/{...}
# - [ ] DetectConsoleOutput to only print styles to terminal

# QUESTIONS:
# - Is there a better way to do Option[int] than -1 as a sentinel? NO
# - Is there a way to have methods on an ASDL product type? NO
# - Indentation level: hard-coded? Option? How to set?
# - How to construct BashArray and BashAssoc values for testing?
#   (I'm using ParseValue)
# - How to construct cyclic values for testing?
# - max_depth vs. cycle detection. Turn cycle detection off if there's a max_depth?
#   NO MAX DEPTH

UNQUOTED_KEY_REGEX = re.compile("^[_a-zA-Z][a-zA-Z0-9]*$")
KEY_STYLE = ansi.GREEN
NUMBER_STYLE = ansi.YELLOW
NULL_STYLE = ansi.BOLD + ansi.RED
BOOL_STYLE = ansi.BOLD + ansi.BLUE
CYCLE_STYLE = ansi.BOLD + ansi.YELLOW

################
# Measurements #
################

def _StrWidth(string):
    # type: (str) -> int
    return wcswidth(string)

def _EmptyMeasure():
    # type: () -> Measure
    return Measure(0, -1)

def _TextMeasure(string):
    # type: (str) -> Measure
    return Measure(_StrWidth(string), -1)

def _BreakMeasure(string):
    # type: (str) -> Measure
    return Measure(_StrWidth(string), 0)

def _FlattenMeasure(measure):
    # type: (Measure) -> Measure
    return Measure(measure.flat, -1)

def _AddMeasure(m1, m2):
    # type: (Measure, Measure) -> Measure
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
    """Print `string` (which must contain newlines)."""
    return MeasuredDoc(doc.Text(string), _TextMeasure(string))

def _Break(string):
    # type: (str) -> MeasuredDoc
    """If in `flat` mode, print `string`, otherwise print `\n`."""
    return MeasuredDoc(doc.Break(string), _BreakMeasure(string))

def _Indent(indent, mdoc):
    # type: (int, MeasuredDoc) -> MeasuredDoc
    """Add `indent` spaces after every newline in `mdoc`."""
    return MeasuredDoc(doc.Indent(indent, mdoc), mdoc.measure)

def _Concat(mdocs):
    # type: (List[MeasuredDoc]) -> MeasuredDoc
    """Print the docs in order (with no spacing in between)."""
    measure = _EmptyMeasure()
    for mdoc in mdocs:
        measure = _AddMeasure(measure, mdoc.measure)
    return MeasuredDoc(doc.Concat(mdocs), measure)

def _Group(mdoc):
    # type: (MeasuredDoc) -> MeasuredDoc
    """Print `mdoc`. Do so in flat mode if it will fit on the current line."""
    return MeasuredDoc(doc.Group(mdoc), mdoc.measure)


###################
# Pretty Printing #
###################

class PrettyPrinter(object):
    """Pretty print an Oils value.

    Uses a strict version of the algorithm from Wadler's "A Prettier Printer".
    (https://homepages.inf.ed.ac.uk/wadler/papers/prettier/prettier.pdf)
    (https://lindig.github.io/papers/strictly-pretty-2000.pdf)
    """

    DEFAULT_MAX_WIDTH = 80
    DEFAULT_INDENTATION = 4
    DEFAULT_USE_STYLES = True

    def __init__(self):
        # type: () -> None
        """Construct a PrettyPrinter with default configuration options.

        Use the Set*() methods for configuration before printing."""
        self.max_width = PrettyPrinter.DEFAULT_MAX_WIDTH
        self.indent = PrettyPrinter.DEFAULT_INDENTATION
        self.use_styles = PrettyPrinter.DEFAULT_USE_STYLES

    def SetMaxWidth(self, max_width):
        # type: (int) -> None
        """Set the maximum line width.

        Pretty printing will attempt to (but does not guarantee) fitting within this width.
        """
        self.max_width = max_width

    def SetIndent(self, indent):
        # type: (int) -> None
        """Set the number of spaces per indentation level."""
        self.indent = indent

    def SetUseStyles(self, use_styles):
        # type: (bool) -> None
        """If true, print with ansi colors and styles. Otherwise print plainly."""
        self.use_styles = use_styles

    def PrintValue(self, val, buf):
        # type: (value_t, BufWriter) -> None
        """Pretty print an Oils value to a BufWriter."""
        constructor = _DocConstructor(self.indent, self.use_styles)
        document = constructor.Value(val)
        self._PrintDoc(document, buf)

    def _Fits(self, prefix_len, group, suffix_measure):
        # type: (int, doc.Group, Measure) -> bool
        """Will `group` fit flat on the current line?"""
        measure = _AddMeasure(_FlattenMeasure(group.mdoc.measure), suffix_measure)
        return prefix_len + _SuffixLen(measure) <= self.max_width

    def _PrintDoc(self, document, buf):
        # type: (MeasuredDoc, BufWriter) -> None
        """Pretty print a `pretty.doc` to a BufWriter."""

        # The width of the text we've printed so far on the current line
        prefix_len = 0
        # A _stack_ of document fragments to print. Each fragment contains:
        # - A MeasuredDoc (doc node and its measure, saying how "big" it is)
        # - The indentation level to print this doc node at.
        # - Is this doc node being printed in flat mode?
        # - The measure _from just after the doc node, to the end of the entire document_.
        #   (Call this the _suffix measure)
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
                    fragments.append(DocFragment(
                        indented.mdoc,
                        frag.indent + indented.indent,
                        frag.is_flat,
                        frag.measure))

                elif case(doc_e.Concat):
                    # If we encounter Concat([A, B, C]) with a suffix measure M,
                    # we need to push A,B,C onto the stack in reverse order:
                    # - C, with suffix measure = B.measure + A.measure + M
                    # - B, with suffix measure = A.measure + M
                    # - A, with suffix measure = M
                    concat = cast(doc.Concat, frag.mdoc.doc)
                    measure = frag.measure
                    for mdoc in reversed(concat.mdocs):
                        fragments.append(DocFragment(
                            mdoc,
                            frag.indent,
                            frag.is_flat,
                            measure))
                        measure = _AddMeasure(mdoc.measure, measure)

                elif case(doc_e.Group):
                    # If the group would fit on the current line when printed
                    # flat, do so. Otherwise, print it non-flat.
                    group = cast(doc.Group, frag.mdoc.doc)
                    flat = self._Fits(prefix_len, group, frag.measure)
                    fragments.append(DocFragment(
                        group.mdoc,
                        frag.indent,
                        flat,
                        frag.measure))


################
# Value -> Doc #
################

class _DocConstructor:
    """Converts Oil values into `doc`s, which can then be pretty printed."""

    def __init__(self, indent, use_styles):
        # type: (int, bool) -> None
        self.indent = indent
        self.use_styles = use_styles

    def Value(self, val):
        # type: (value_t) -> MeasuredDoc
        """Convert an Oils value into a `doc`, which can then be pretty printed."""
        self.visiting = {} # type: Dict[int, bool]
        return self._Value(val)

    def _Styled(self, style, mdoc):
        # type: (str, MeasuredDoc) -> MeasuredDoc
        """Apply the ANSI style string to the given node, if use_styles is set."""
        if self.use_styles:
            return _Concat([
                MeasuredDoc(doc.Text(style), _EmptyMeasure()),
                mdoc,
                MeasuredDoc(doc.Text(ansi.RESET), _EmptyMeasure())])
        else:
            return mdoc

    def _Surrounded(self, open, mdoc, close):
        # type: (str, MeasuredDoc, str) -> MeasuredDoc
        """Print one of two options (using '[' and ']' for open and close):
    
        ```
        [mdoc]
        ------
        [
            mdoc
        ]
        ```
        """
        return _Group(_Concat([
            _Text(open),
            _Indent(self.indent, _Concat([_Break(""), mdoc])),
            _Break(""),
            _Text(close)]))
    
    def _Join(self, items, sep, space):
        # type: (List[MeasuredDoc], str, str) -> MeasuredDoc
        """Join `items`, using either 'sep+space' or 'sep+newline' between them."""
        seq = [items[0]]
        for item in items[1:]:
            seq.append(_Text(sep))
            seq.append(_Break(space))
            seq.append(item)
        return _Concat(seq)

    def _Key(self, s):
        # type: (str) -> MeasuredDoc
        if UNQUOTED_KEY_REGEX.match(s):
            return self._Styled(KEY_STYLE, _Text(s))
        else:
            return self._Styled(KEY_STYLE, _Text(fastfunc.J8EncodeString(s, True))) # lossy_json=True

    def _String(self, s):
        # type: (str) -> MeasuredDoc
        return _Text(fastfunc.J8EncodeString(s, True)) # lossy_json=True

    def _ValueList(self, vlist):
        # type: (value.List) -> MeasuredDoc
        if len(vlist.items) == 0:
            return _Text("[]")
        mdocs = [self._Value(item) for item in vlist.items]
        return self._Surrounded("[", self._Join(mdocs, ",", " "), "]")

    def _ValueDict(self, vdict):
        # type: (value.Dict) -> MeasuredDoc
        if len(vdict.d) == 0:
            return _Text("{}")
        mdocs = []
        for k, v in iteritems(vdict.d):
            mdocs.append(_Concat([self._Key(k), _Text(": "), self._Value(v)]))
        return self._Surrounded("{", self._Join(mdocs, ",", " "), "}")

    def _BashArray(self, varray):
        # type: (value.BashArray) -> MeasuredDoc
        if len(varray.strs) == 0:
            return _Text("[]")
        mdocs = []
        for s in varray.strs:
            if s is None:
                mdocs.append(self._String(s))
            else:
                mdocs.append(_Text("null"))
        return self._Surrounded("[", self._Join(mdocs, ",", " "), "]")

    def _BashAssoc(self, vassoc):
        # type: (value.BashAssoc) -> MeasuredDoc
        if len(vassoc.d) == 0:
            return _Text("{}")
        mdocs = []
        for k2, v2 in iteritems(vassoc.d):
            mdocs.append(_Concat([self._Key(k2), _Text(": "), self._String(v2)]))
        return self._Surrounded("{", self._Join(mdocs, ",", " "), "}")

    def _Value(self, val):
        # type: (value_t) -> MeasuredDoc

        with tagswitch(val) as case:
            if case(value_e.Null):
                return self._Styled(NULL_STYLE, _Text("null"))

            elif case(value_e.Bool):
                b = cast(value.Bool, val).b
                return self._Styled(BOOL_STYLE, _Text("true" if b else "false"))

            elif case(value_e.Int):
                i = cast(value.Int, val).i
                return self._Styled(NUMBER_STYLE, _Text(mops.ToStr(i)))

            elif case(value_e.Float):
                f = cast(value.Float, val).f
                return self._Styled(NUMBER_STYLE, _Text(str(f)))

            elif case(value_e.Str):
                s = cast(value.Str, val).s
                return self._String(s)

            elif case(value_e.List):
                vlist = cast(value.List, val)
                heap_id = HeapValueId(vlist)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        _Text("["),
                        self._Styled(CYCLE_STYLE, _Text("...")),
                        _Text("]")])
                else:
                    self.visiting[heap_id] = True
                    result = self._ValueList(vlist)
                    self.visiting[heap_id] = False
                    return result

            elif case(value_e.Dict):
                vdict = cast(value.Dict, val)
                heap_id = HeapValueId(vdict)
                if self.visiting.get(heap_id, False):
                    return _Concat([
                        _Text("{"),
                        self._Styled(CYCLE_STYLE, _Text("...")),
                        _Text("}")])
                else:
                    self.visiting[heap_id] = True
                    result = self._ValueDict(vdict)
                    self.visiting[heap_id] = False
                    return result

            elif case(value_e.BashArray):
                varray = cast(value.BashArray, val)
                return self._BashArray(varray)

            elif case(value_e.BashAssoc):
                vassoc = cast(value.BashAssoc, val)
                return self._BashAssoc(vassoc)

            else:
                ysh_type = value_str(val.tag(), dot=False)
                id_str = ValueIdString(val)
                return _Text("<" + ysh_type + id_str + ">")

# vim: sw=4
