"""
format.py -- Pretty print an ASDL data structure.
"""
from _devbuild.gen.hnode_asdl import hnode, hnode_e, hnode_t
from _devbuild.gen.pretty_asdl import doc, doc_e, doc_t, MeasuredDoc
from display import pp_hnode
from display import pretty
from mycpp import mylib
from mycpp.mylib import log, tagswitch

from typing import Any, Optional, cast

_ = log

if mylib.PYTHON:

    def PrettyPrint(obj, f=None):
        # type: (Any, Optional[mylib.Writer]) -> None
        """Print abbreviated tree in color.  For unit tests."""
        f = f if f else mylib.Stdout()
        tree = obj.PrettyTree(True)
        HNodePrettyPrint(tree, f)


def _HNodeCount(h):
    # type: (hnode_t) -> int
    """
    Return the size of the tree
    """
    UP_h = h
    with tagswitch(h) as case:
        if case(hnode_e.AlreadySeen):
            return 1

        elif case(hnode_e.Leaf):
            return 1

        elif case(hnode_e.Array):
            h = cast(hnode.Array, UP_h)
            n = 0
            for child in h.children:
                n += _HNodeCount(child)
            return n

        elif case(hnode_e.Record):
            h = cast(hnode.Record, UP_h)
            n = 0
            for field in h.fields:
                n += _HNodeCount(field.val)

            if h.unnamed_fields is not None:
                for child in h.unnamed_fields:
                    n += _HNodeCount(child)
            return n

        else:
            raise AssertionError()


def _DocCount(d):
    # type: (doc_t) -> int
    """
    Return the size of the tree
    """
    UP_d = d
    with tagswitch(d) as case:
        if case(doc_e.Break):
            return 1

        elif case(doc_e.Text):
            return 1

        elif case(doc_e.Indent):
            d = cast(doc.Indent, UP_d)
            return _DocCount(d.mdoc.doc)

        elif case(doc_e.Group):
            d = cast(MeasuredDoc, UP_d)
            return _DocCount(d.doc)

        elif case(doc_e.Flat):
            d = cast(doc.Flat, UP_d)
            return _DocCount(d.mdoc.doc)

        elif case(doc_e.IfFlat):
            d = cast(doc.IfFlat, UP_d)
            return _DocCount(d.flat_mdoc.doc) + _DocCount(d.nonflat_mdoc.doc)

        elif case(doc_e.Concat):
            d = cast(doc.Concat, UP_d)
            n = 0
            for mdoc in d.mdocs:
                n += _DocCount(mdoc.doc)
            return n

        else:
            raise AssertionError()


def _HNodePrettyPrint(perf_stats, doc_debug, node, f, max_width=80):
    # type: (bool, bool, hnode_t, mylib.Writer, int) -> None

    mylib.MaybeCollect()
    if perf_stats:
        log('___ HNODE COUNT %d', _HNodeCount(node))
        log('')

        log('___ GC: after hnode_t conversion')
        mylib.PrintGcStats()
        log('')

    enc = pp_hnode.HNodeEncoder()
    enc.SetUseStyles(f.isatty())
    enc.SetIndent(2)  # save space, compared to 4 spaces

    d = enc.HNode(node)

    mylib.MaybeCollect()
    if perf_stats:
        #if doc_debug:
        if 0:
            # Pretty print the doc tree itself!
            p = d.PrettyTree(False)
            _HNodePrettyPrint(perf_stats, False, p, f)

        log('___ DOC COUNT %d', _DocCount(d))
        log('')

        log('___ GC: after doc_t conversion')
        mylib.PrintGcStats()
        log('')

    printer = pretty.PrettyPrinter(max_width)  # max columns

    buf = mylib.BufWriter()
    printer.PrintDoc(d, buf)

    f.write(buf.getvalue())
    f.write('\n')

    mylib.MaybeCollect()
    if perf_stats:
        log('___ GC: after printing')
        mylib.PrintGcStats()
        log('')


def HNodePrettyPrint(node, f, max_width=80):
    # type: (hnode_t, mylib.Writer, int) -> None
    """
    Make sure dependencies aren't a problem
    """
    _HNodePrettyPrint(False, True, node, f, max_width=max_width)
