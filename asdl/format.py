"""
format.py -- Pretty print an ASDL data structure.
"""
from _devbuild.gen.hnode_asdl import hnode_t
from display import pp_hnode
from display import pretty
from mycpp import mylib
from mycpp.mylib import log

from typing import Any, Optional

_ = log

if mylib.PYTHON:

    def PrettyPrint(obj, f=None):
        # type: (Any, Optional[mylib.Writer]) -> None
        """Print abbreviated tree in color.  For unit tests."""
        f = f if f else mylib.Stdout()
        tree = obj.PrettyTree(True)
        HNodePrettyPrint(tree, f)


def _HNodePrettyPrint(perf_stats, node, f, max_width=80):
    # type: (bool, hnode_t, mylib.Writer, int) -> None
    if perf_stats:
        log('')
        log('___ GC: after hnode_t conversion')
        mylib.PrintGcStats()

    enc = pp_hnode.HNodeEncoder()
    enc.SetUseStyles(f.isatty())
    enc.SetIndent(2)  # save space, compared to 4 spaces

    doc = enc.HNode(node)
    # TODO: print gc stats here

    if perf_stats:
        log('')
        log('___ GC: after doc_t conversion')
        mylib.PrintGcStats()

    printer = pretty.PrettyPrinter(max_width)  # max columns

    buf = mylib.BufWriter()
    printer.PrintDoc(doc, buf)

    f.write(buf.getvalue())
    f.write('\n')

    if perf_stats:
        log('')
        log('___ GC: after printing')
        mylib.PrintGcStats()


def HNodePrettyPrint(node, f, max_width=80):
    # type: (hnode_t, mylib.Writer, int) -> None
    """
    Make sure dependencies aren't a problem
    """
    _HNodePrettyPrint(False, node, f, max_width=max_width)
