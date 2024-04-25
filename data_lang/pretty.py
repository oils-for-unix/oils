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

import fastfunc

from mycpp import mops
from mycpp.mylib import log, tagswitch, BufWriter, iteritems

_ = log

# TODO:
# - options: max_depth, max_lines, stuff about cycles, LOSSY_JSON
# - clean up imports (is there a lint that checks for unused imports?)
# - hook up the printer in core/ui.py::PrettyPrintValue
# - run the linter
# - what's with `_ = log`?
# - string width
# - contributing page: PRs are squash-merged with a descriptive tag like [json]
# - fill in ~Algorithm Description~

# QUESTIONS:
# - Is there a better way to do Option[int] than -1 as a sentinel? NO
# - Is there a way to have methods on an ASDL product type? NO
# - Indentation level: hard-coded? Option? How to set?
# - How to construct BashArray and BashAssoc values for testing?
#   (I'm using ParseValue)
# - How to construct cyclic values for testing?
# - max_depth vs. cycle detection. Turn cycle detection off if there's a max_depth?


################
# Measurements #
################

def _StrWidth(string):
    # type: (str) -> int
    return len(string) #TODO

def _EmptyMeasure():
    # type: () -> Measure
    return Measure(0, -1)

def _TextMeasure(string):
    # type: (str) -> Measure
    return Measure(_StrWidth(string), -1)

def _NewlineMeasure():
    # type: () -> Measure
    return Measure(0, 0)

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
    return MeasuredDoc(
        doc.Break(string),
        _AddMeasure(_TextMeasure(string), _NewlineMeasure()))

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
    DEFAULT_MAX_DEPTH = -1

    def __init__(self):
        # type: () -> None
        """Construct a PrettyPrinter with default configuration options.

        Use the Set*() methods for configuration before printing."""
        self.max_width = PrettyPrinter.DEFAULT_MAX_WIDTH
        self.indent = PrettyPrinter.DEFAULT_INDENTATION
        self.max_depth = PrettyPrinter.DEFAULT_MAX_DEPTH

    def SetMaxWidth(self, max_width):
        # type: (int) -> None
        self.max_width = max_width

    def SetIndent(self, indent):
        # type: (int) -> None
        self.indent = indent

    def SetMaxDepth(self, max_depth):
        # type: (int) -> None
        self.max_depth = max_depth

    def PrintValue(self, val, buf):
        # type: (value_t, BufWriter) -> None
        """Pretty print an Oils value to a BufWriter."""
        constructor = _DocConstructor(self.indent, self.max_depth)
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

class _CycleDetector:
    def __init__(self, max_depth):
        # type: (int) -> None
        self.visited = {} # type: Dict[int, str]
        self.label = 'a'
        self.max_depth = max_depth
        self.depth = 0

    def _NextLabel(self):
        # type: () -> str
        label = self.label
        # There _really_ shouldn't be more than 26 independent cycles in one
        # value...
        self.label = chr(ord(self.label) + 1)
        return label

    def Visit(self, heap_id, callback):
        # type: (int, Callable[[], MeasuredDoc]) -> MeasuredDoc

        if self.max_depth != -1 and self.depth >= self.max_depth:
            return _Text("...")
        elif heap_id in self.visited:
            label = self.visited[heap_id]
            if label is None:
                label = self._NextLabel()
                self.visited[heap_id] = label
            return _Text("*" + label)
        else:
            self.visited[heap_id] = None
            self.depth += 1
            document = callback()
            self.depth -= 1
            label = self.visited[heap_id]
            if label is None:
                del self.visited[heap_id]
                return document
            else:
                return _Concat([_Text("&" + label + " "), document])

class _DocConstructor:
    """Converts Oil values into `doc`s, which can then be pretty printed."""

    def __init__(self, indent, max_depth):
        # type: (int, int) -> None
        self.indent = indent
        self.max_depth = max_depth

    def Value(self, val):
        # type: (value_t) -> MeasuredDoc
        """Convert an Oils value into a `doc`, which can then be pretty printed."""
        self.cycle_detector = _CycleDetector(self.max_depth)
        return self._Value(val)

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
    
    def _JoinPair(self, left, sep, space, right):
        # type: (MeasuredDoc, str, str, MeasuredDoc) -> MeasuredDoc
        """Print one of two options (using ':' and '_' for sep and space):
        ```
        left:_right
        ------
        left:
            right
        ```
        """
        return _Concat([
            left,
            _Text(sep),
            _Indent(self.indent, _Group(_Concat([_Break(space), right])))])

    def _String(self, s):
        # type: (str) -> MeasuredDoc
        return _Text(fastfunc.J8EncodeString(s, True)) # lossy_json=True

    def _List(self, vlist):
        # type: (value.List) -> MeasuredDoc
        if len(vlist.items) == 0:
            return _Text("[]")
        mdocs = [self._Value(item) for item in vlist.items]
        return self._Surrounded("[", self._Join(mdocs, ",", " "), "]")

    def _Dict(self, vdict):
        # type: (value.Dict) -> MeasuredDoc
        if len(vdict.d) == 0:
            return _Text("{}")
        mdocs = []
        for k, v in iteritems(vdict.d):
            mdocs.append(
                self._JoinPair(self._String(k), ":", " ", self._Value(v)))
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
            mdocs.append(
                self._JoinPair(self._String(k2), ":", " ", self._String(v2)))
        return self._Surrounded("{", self._Join(mdocs, ",", " "), "}")

    def _Value(self, val):
        # type: (value_t) -> MeasuredDoc

        with tagswitch(val) as case:
            if case(value_e.Null):
                return _Text("null")

            elif case(value_e.Bool):
                b = cast(value.Bool, val).b
                return _Text("true" if b else "false")

            elif case(value_e.Int):
                i = cast(value.Int, val).i
                return _Text(mops.ToStr(i))

            elif case(value_e.Float):
                f = cast(value.Float, val).f
                return _Text(str(f))

            elif case(value_e.Str):
                s = cast(value.Str, val).s
                return self._String(s)

            elif case(value_e.List):
                vlist = cast(value.List, val)
                return self.cycle_detector.Visit(
                    HeapValueId(vlist),
                    lambda: self._List(vlist))

            elif case(value_e.Dict):
                vdict = cast(value.Dict, val)
                return self.cycle_detector.Visit(
                    HeapValueId(vdict),
                    lambda: self._Dict(vdict))

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
