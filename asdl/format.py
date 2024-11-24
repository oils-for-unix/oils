"""
format.py -- Pretty print an ASDL data structure.
"""
from _devbuild.gen.hnode_asdl import hnode_t
from display import pp_hnode
from display import pretty
from mycpp import mylib

from typing import Any, Optional

if mylib.PYTHON:

    def PrettyPrint(obj, f=None):
        # type: (Any, Optional[mylib.Writer]) -> None
        """Print abbreviated tree in color.  For unit tests."""
        f = f if f else mylib.Stdout()
        tree = obj.PrettyTree(True)
        HNodePrettyPrint(tree, f)


def HNodePrettyPrint(node, f, max_width=80):
    # type: (hnode_t, mylib.Writer, int) -> None
    """
    Make sure dependencies aren't a problem
    """
    enc = pp_hnode.HNodeEncoder()
    enc.SetUseStyles(f.isatty())
    enc.SetIndent(2)  # save space, compared to 4 spaces

    doc = enc.HNode(node)

    printer = pretty.PrettyPrinter(max_width)  # max columns

    buf = mylib.BufWriter()
    printer.PrintDoc(doc, buf)
    f.write(buf.getvalue())
    f.write('\n')
