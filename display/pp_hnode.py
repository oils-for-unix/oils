#!/usr/bin/env python2
from __future__ import print_function
"""
Base class for pretty printing, and HNodeEncoder
"""

from _devbuild.gen.hnode_asdl import hnode, hnode_e, hnode_t
from _devbuild.gen.pretty_asdl import (doc, MeasuredDoc)
from display import ansi
from display import pretty
from display.pretty import (_Break, _Concat, _Flat, _Group, _IfFlat, _Indent,
                            _EmptyMeasure, AsciiText)
from mycpp import mylib
from mycpp.mylib import log, tagswitch
from typing import cast, List, Dict

_ = log


class BaseEncoder(object):

    def __init__(self):
        # type: () -> None

        # Default values
        self.indent = 4
        self.use_styles = True
        # Tuned for 'data_lang/pretty-benchmark.sh float-demo'
        # TODO: might want options for float width
        self.max_tabular_width = 22

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
                AsciiText(open),
                _Indent(self.indent, _Concat([_Break(""), mdoc])),
                _Break(""),
                AsciiText(close)
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
                AsciiText(open), prefix,
                _Indent(self.indent, _Concat([_Break(sep), mdoc])),
                _Break(""),
                AsciiText(close)
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
                seq.append(AsciiText(sep))
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
            return AsciiText("")

        max_flat_len = 0
        seq = []  # type: List[MeasuredDoc]
        for i, item in enumerate(items):
            if i != 0:
                seq.append(AsciiText(sep))
                seq.append(_Break(" "))
            seq.append(item)
            max_flat_len = max(max_flat_len, item.measure.flat)
        non_tabular = _Concat(seq)

        sep_width = len(sep)
        if max_flat_len + sep_width + 1 <= self.max_tabular_width:
            tabular_seq = []  # type: List[MeasuredDoc]
            for i, item in enumerate(items):
                tabular_seq.append(_Flat(item))
                if i != len(items) - 1:
                    padding = max_flat_len - item.measure.flat + 1
                    tabular_seq.append(AsciiText(sep))
                    tabular_seq.append(_Group(_Break(" " * padding)))
            tabular = _Concat(tabular_seq)
            return _Group(_IfFlat(non_tabular, tabular))
        else:
            return non_tabular


class HNodeEncoder(BaseEncoder):

    def __init__(self):
        # type: () -> None
        BaseEncoder.__init__(self)

    def HNode(self, h):
        # type: (hnode_t) -> MeasuredDoc
        self.visiting.clear()
        return self._HNode(h)

    def _HNode(self, h):
        # type: (hnode_t) -> MeasuredDoc

        doc = pretty.AsciiText('foo')

        UP_h = h
        with tagswitch(h) as case:
            if case(hnode_e.AlreadySeen):
                h = cast(hnode.AlreadySeen, UP_h)
                return pretty.AsciiText('...0x%s' % mylib.hex_lower(h.heap_id))

            elif case(hnode_e.Leaf):
                h = cast(hnode.Leaf, UP_h)
                # TODO: what do we do with node.color
                return doc

            elif case(hnode_e.External):
                h = cast(hnode.External, UP_h)
                # TODO: color_e.External
                return doc

            elif case(hnode_e.Array):
                h = cast(hnode.Array, UP_h)
                # TODO: _Join I think
                return doc

            elif case(hnode_e.Record):
                h = cast(hnode.Record, UP_h)
                # TODO: _SurroundedAndPrefixed
                return doc

            else:
                raise AssertionError()


# vim: sw=4
