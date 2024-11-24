#!/usr/bin/env python2
from __future__ import print_function
"""
Base class for pretty printing, and HNodeEncoder
"""

from _devbuild.gen.hnode_asdl import hnode, hnode_e, hnode_t, Field, color_e
from _devbuild.gen.pretty_asdl import (doc, MeasuredDoc)
from data_lang import j8_lite
from display import ansi
from display import pretty
from display.pretty import (_Break, _Concat, _Flat, _Group, _IfFlat, _Indent,
                            _EmptyMeasure, AsciiText)
from mycpp import mylib
from mycpp.mylib import log, tagswitch, switch
from typing import cast, List, Dict, Optional

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
            # TODO: the begin and end mdocs are CONSTANT.  We should fold those
            # in.
            return _Concat([
                MeasuredDoc(doc.Text(style), _EmptyMeasure()), mdoc,
                MeasuredDoc(doc.Text(ansi.RESET), _EmptyMeasure())
            ])
        else:
            return mdoc

    def _Surrounded(self, left, mdoc, right):
        # type: (str, MeasuredDoc, str) -> MeasuredDoc
        """Print one of two options (using '[', ']' for left, right):
    
        [mdoc]
        ------
        [
            mdoc
        ]
        """
        # TODO:
        # - left and right AsciiText often CONSTANT mdocs
        # - _Break too
        return _Group(
            _Concat([
                AsciiText(left),
                _Indent(self.indent, _Concat([_Break(''), mdoc])),
                _Break(''),
                AsciiText(right)
            ]))

    def _SurroundedAndPrefixed(self, left, prefix, sep, mdoc, right):
        # type: (str, MeasuredDoc, str, MeasuredDoc, str) -> MeasuredDoc
        """Print one of two options
        (using '[', 'prefix', ':', 'mdoc', ']' for left, prefix, sep, mdoc, right):

        [prefix:mdoc]
        ------
        [prefix
            mdoc
        ]
        """
        return _Group(
            _Concat([
                AsciiText(left), prefix,
                _Indent(self.indent, _Concat([_Break(sep), mdoc])),
                _Break(''),
                AsciiText(right)
            ]))

    def _Join(self, items, sep, space):
        # type: (List[MeasuredDoc], str, str) -> MeasuredDoc
        """Join `items`, using either 'sep+space' or 'sep+newline' between them.

        e.g., if sep and space are ',' and '_', print one of these two cases:

        first,_second,_third
        ------
        first,
        second,
        third
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

        The first "single line" style is used if the items fit on one line.  The
        second "tabular" style is used if the flat width of all items is no
        greater than self.max_tabular_width. The third "multi line" style is
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
        # smaller than self.max_tabular_width?" to pick between style 2 and
        # style 3.

        if len(items) == 0:
            return AsciiText('')

        max_flat_len = 0
        seq = []  # type: List[MeasuredDoc]
        for i, item in enumerate(items):
            if i != 0:
                seq.append(AsciiText(sep))
                seq.append(_Break(' '))
            seq.append(item)
            max_flat_len = max(max_flat_len, item.measure.flat)
        non_tabular = _Concat(seq)

        #log('MAX FLAT %d', max_flat_len)

        sep_width = len(sep)
        if max_flat_len + sep_width + 1 <= self.max_tabular_width:
            tabular_seq = []  # type: List[MeasuredDoc]
            for i, item in enumerate(items):
                tabular_seq.append(_Flat(item))
                if i != len(items) - 1:
                    padding = max_flat_len - item.measure.flat + 1
                    tabular_seq.append(AsciiText(sep))
                    tabular_seq.append(_Group(_Break(' ' * padding)))
            tabular = _Concat(tabular_seq)
            return _Group(_IfFlat(non_tabular, tabular))
        else:
            return non_tabular


class HNodeEncoder(BaseEncoder):

    def __init__(self):
        # type: () -> None
        BaseEncoder.__init__(self)

        self.type_color = ansi.YELLOW
        self.field_color = ansi.MAGENTA

    def HNode(self, h):
        # type: (hnode_t) -> MeasuredDoc
        self.visiting.clear()
        return self._HNode(h)

    def _Field(self, field):
        # type: (Field) -> MeasuredDoc
        #name = self._Styled(self.field_color, AsciiText(field.name))
        name = AsciiText(field.name)
        return _Concat([name, AsciiText(':'), self._HNode(field.val)])

    def _HNode(self, h):
        # type: (hnode_t) -> MeasuredDoc

        UP_h = h
        with tagswitch(h) as case:
            if case(hnode_e.AlreadySeen):
                h = cast(hnode.AlreadySeen, UP_h)
                return pretty.AsciiText('...0x%s' % mylib.hex_lower(h.heap_id))

            elif case(hnode_e.Leaf):
                h = cast(hnode.Leaf, UP_h)

                with switch(h.color) as case2:
                    if case2(color_e.TypeName):
                        color = ansi.YELLOW
                    elif case2(color_e.StringConst):
                        color = ansi.BOLD
                    elif case2(color_e.OtherConst):
                        color = ansi.GREEN
                    elif case2(color_e.External):
                        color = ansi.BOLD + ansi.BLUE
                    elif case2(color_e.UserType):
                        color = ansi.GREEN  # Same color as other literals for now
                    else:
                        raise AssertionError()

                # TODO: what do we do with node.color
                s = j8_lite.EncodeString(h.s, unquoted_ok=True)

                # Could be Unicode, but we don't want that dependency right now
                return self._Styled(color, AsciiText(s))

            elif case(hnode_e.Array):
                h = cast(hnode.Array, UP_h)
                if len(h.children) == 0:
                    return AsciiText('[]')
                children = [self._HNode(item) for item in h.children]
                return self._Surrounded('[', self._Tabular(children, ''), ']')

            elif case(hnode_e.Record):
                h = cast(hnode.Record, UP_h)

                type_name = None  # type: Optional[MeasuredDoc]
                if len(h.node_type):
                    type_name = self._Styled(self.type_color,
                                             AsciiText(h.node_type))

                mdocs = None  # type: Optional[List[MeasuredDoc]]
                if h.unnamed_fields is not None and len(h.unnamed_fields):
                    mdocs = [self._HNode(item) for item in h.unnamed_fields]
                elif len(h.fields) != 0:
                    mdocs = [self._Field(field) for field in h.fields]

                if mdocs is None:
                    assert type_name is not None, h

                    # e.g. (value.Stdin) with no fields
                    return _Concat(
                        [AsciiText(h.left), type_name,
                         AsciiText(h.right)])

                # Named or unnamed
                child = self._Join(mdocs, '', ' ')

                if type_name is not None:
                    # e.g. (Token id:LitChars col:5)
                    return self._SurroundedAndPrefixed(h.left, type_name, ' ',
                                                       child, h.right)
                else:
                    # e.g. <Id.Lit_Chars foo>
                    return self._Surrounded(h.left, child, h.right)

            else:
                raise AssertionError()


# vim: sw=4
