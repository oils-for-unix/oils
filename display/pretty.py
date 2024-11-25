#!/usr/bin/env python2
"""
Pretty printing library.

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

from _devbuild.gen.pretty_asdl import doc, doc_e, DocFragment, Measure, MeasuredDoc
from mycpp.mylib import log, tagswitch, BufWriter
from typing import cast, List

_ = log

#
# Measurements
#


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
    """Compute the measure of 2 concatenated docs.

    If m1 and m2 are the measures of doc1 and doc2, then _ConcatMeasure(m1, m2)
    is the measure of doc.Concat([doc1, doc2]).  This concatenation is
    associative but not commutative.
    """
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


#
# Doc Construction
#


def AsciiText(string):
    # type: (str) -> MeasuredDoc
    """Print string (which must not contain a newline)."""
    return MeasuredDoc(doc.Text(string), Measure(len(string), -1))


def _Break(string):
    # type: (str) -> MeasuredDoc
    """If in flat mode, print string, otherwise print `\n`.

    Note: Doesn't try to compute Unicode width, since we control these strings.
    """
    return MeasuredDoc(doc.Break(string), Measure(len(string), 0))


def _Indent(indent, mdoc):
    # type: (int, MeasuredDoc) -> MeasuredDoc
    """Add 'indent' spaces after every newline in mdoc."""
    return MeasuredDoc(doc.Indent(indent, mdoc), mdoc.measure)


def _Splice(out, mdocs):
    # type: (List[MeasuredDoc], List[MeasuredDoc]) -> Measure
    """Optimization for _Concat.

    This reduces the total size of the doc_t tree, and thus the memory usage
    (as long as we mylib.MaybeCollect() in _HNode!)

    Example of optimizing _Concat nodes together: _Field() concatenates
    AsciiText("name:") and _HNode(), and the latter is often a doc.Concat node.
    """
    measure = _EmptyMeasure()
    for mdoc in mdocs:
        with tagswitch(mdoc.doc) as case:
            if case(doc_e.Concat):
                child = cast(doc.Concat, mdoc.doc)
                # ignore return value, because the parent has the measure already
                _Splice(out, child.mdocs)
            else:
                out.append(mdoc)
        measure = _ConcatMeasure(measure, mdoc.measure)
    return measure


def _Concat(mdocs):
    # type: (List[MeasuredDoc]) -> MeasuredDoc
    """Print the mdocs in order (with no space in between)."""
    flattened = []  # type: List[MeasuredDoc]
    measure = _Splice(flattened, mdocs)
    return MeasuredDoc(doc.Concat(flattened), measure)


def _Group(mdoc):
    # type: (MeasuredDoc) -> MeasuredDoc
    """Print mdoc. Use flat mode if mdoc will fit on the current line."""
    return MeasuredDoc(mdoc, mdoc.measure)


def _IfFlat(flat_mdoc, nonflat_mdoc):
    # type: (MeasuredDoc, MeasuredDoc) -> MeasuredDoc
    """If in flat mode, print flat_mdoc; otherwise print nonflat_mdoc."""
    return MeasuredDoc(
        doc.IfFlat(flat_mdoc, nonflat_mdoc),
        Measure(flat_mdoc.measure.flat, nonflat_mdoc.measure.nonflat))


def _Flat(mdoc):
    # type: (MeasuredDoc) -> MeasuredDoc
    """Prints mdoc in flat mode."""
    return MeasuredDoc(doc.Flat(mdoc), _FlattenMeasure(mdoc.measure))


class PrettyPrinter(object):

    def __init__(self, max_width):
        # type: (int) -> None
        self.max_width = max_width

    def _Fits(self, prefix_len, group, suffix_measure):
        # type: (int, MeasuredDoc, Measure) -> bool
        """Will group fit flat on the current line?"""
        measure = _ConcatMeasure(_FlattenMeasure(group.measure),
                                 suffix_measure)
        return prefix_len + _SuffixLen(measure) <= self.max_width

    def PrintDoc(self, document, buf):
        # type: (MeasuredDoc, BufWriter) -> None
        """Pretty print a doc_t to a BufWriter."""

        # The width of the text we've printed so far on the current line
        prefix_len = 0
        # A _stack_ of document fragments to print. Each fragment contains:
        # - A MeasuredDoc (doc node and its measure, saying how "big" it is)
        # - The indentation level to print this doc node at.
        # - Is this doc node being printed in flat mode?
        # - The measure _from just after the doc node, to the end of the entire document_.
        #   (Call this the suffix_measure)
        fragments = [DocFragment(_Group(document), 0, False, _EmptyMeasure())]

        max_stack = len(fragments)

        while len(fragments) > 0:
            max_stack = max(max_stack, len(fragments))

            frag = fragments.pop()
            UP_doc = frag.mdoc.doc
            with tagswitch(UP_doc) as case:

                if case(doc_e.Text):
                    text = cast(doc.Text, UP_doc)
                    buf.write(text.string)
                    prefix_len += frag.mdoc.measure.flat

                elif case(doc_e.Break):
                    break_ = cast(doc.Break, UP_doc)
                    if frag.is_flat:
                        buf.write(break_.string)
                        prefix_len += frag.mdoc.measure.flat
                    else:
                        buf.write('\n')
                        buf.write_spaces(frag.indent)
                        prefix_len = frag.indent

                elif case(doc_e.Indent):
                    indented = cast(doc.Indent, UP_doc)
                    fragments.append(
                        DocFragment(indented.mdoc,
                                    frag.indent + indented.indent,
                                    frag.is_flat, frag.measure))

                elif case(doc_e.Concat):
                    concat = cast(doc.Concat, UP_doc)

                    # If we encounter Concat([A, B, C]) with a suffix measure M,
                    # we need to push A,B,C onto the stack in reverse order:
                    # - C, with suffix_measure = B.measure + A.measure + M
                    # - B, with suffix_measure = A.measure + M
                    # - A, with suffix_measure = M
                    measure = frag.measure
                    for mdoc in reversed(concat.mdocs):
                        fragments.append(
                            DocFragment(mdoc, frag.indent, frag.is_flat,
                                        measure))
                        # TODO: this algorithm allocates too much!
                        measure = _ConcatMeasure(mdoc.measure, measure)

                elif case(doc_e.Group):
                    # If the group would fit on the current line when printed
                    # flat, do so. Otherwise, print it non-flat.
                    group = cast(MeasuredDoc, UP_doc)
                    is_flat = self._Fits(prefix_len, group, frag.measure)
                    fragments.append(
                        DocFragment(group, frag.indent, is_flat, frag.measure))

                elif case(doc_e.IfFlat):
                    if_flat = cast(doc.IfFlat, UP_doc)
                    if frag.is_flat:
                        subdoc = if_flat.flat_mdoc
                    else:
                        subdoc = if_flat.nonflat_mdoc
                    fragments.append(
                        DocFragment(subdoc, frag.indent, frag.is_flat,
                                    frag.measure))

                elif case(doc_e.Flat):
                    flat_doc = cast(doc.Flat, UP_doc)
                    fragments.append(
                        DocFragment(flat_doc.mdoc, frag.indent, True,
                                    frag.measure))

        if 0:
            log('')
            log('___ MAX DocFragment stack: %d', max_stack)
            log('')


# vim: sw=4
