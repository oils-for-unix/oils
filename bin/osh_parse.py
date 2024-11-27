#!/usr/bin/env python2
"""Osh_parse.py."""
from __future__ import print_function

import sys

from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.syntax_asdl import source, source_t, command, command_t
from asdl import format as fmt
from core import alloc
from core import error
from core import optview
#from core import main_loop
from core import pyutil
from core import state
from display import ui
from frontend import parse_lib
from frontend import reader
from mycpp import mylib
from mycpp.mylib import log

_ = log

from typing import List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from osh.cmd_parse import CommandParser
    from pgen2.grammar import Grammar


# TEMP: Copied from core/main_loop.py
def ParseWholeFile(c_parser):
    # type: (CommandParser) -> command_t
    """Parse an entire shell script.

    This uses the same logic as Batch().
    """
    children = []  # type: List[command_t]
    while True:
        node = c_parser.ParseLogicalLine()  # can raise ParseError
        if node is None:  # EOF
            c_parser.CheckForPendingHereDocs()  # can raise ParseError
            break
        children.append(node)

    if len(children) == 1:
        return children[0]
    else:
        return command.CommandList(children)


def main(argv):
    # type: (List[str]) -> int
    arena = alloc.Arena()
    errfmt = ui.ErrorFormatter()

    opt0_array = state.InitOpts()
    no_stack = None  # type: List[bool]  # for mycpp
    opt_stacks = [no_stack] * option_i.ARRAY_SIZE  # type: List[List[bool]]
    parse_opts = optview.Parse(opt0_array, opt_stacks)
    # Dummy value; not respecting aliases!
    aliases = {}  # type: Dict[str, str]
    # parse `` and a[x+1]=bar differently

    ysh_grammar = None  # type: Grammar
    if mylib.PYTHON:
        loader = pyutil.GetResourceLoader()
        ysh_grammar = pyutil.LoadYshGrammar(loader)

    parse_ctx = parse_lib.ParseContext(arena, parse_opts, aliases, ysh_grammar)

    pretty_print = True

    if len(argv) == 1:
        line_reader = reader.FileLineReader(mylib.Stdin(), arena)
        src = source.Stdin('')  # type: source_t

    elif len(argv) == 2:
        path = argv[1]
        f = mylib.open(path)
        line_reader = reader.FileLineReader(f, arena)
        src = source.MainFile(path)

    elif len(argv) == 3:
        if argv[1] == '-c':
            # This path is easier to run through GDB
            line_reader = reader.StringLineReader(argv[2], arena)
            src = source.CFlag

        elif argv[1] == '-n':  # For benchmarking, allow osh_parse -n file.txt
            path = argv[2]
            f = mylib.open(path)
            line_reader = reader.FileLineReader(f, arena)
            src = source.MainFile(path)
            # This is like --ast-format none, which benchmarks/osh-helper.sh passes.
            pretty_print = False

        else:
            raise AssertionError()

    else:
        raise AssertionError()

    arena.PushSource(src)

    c_parser = parse_ctx.MakeOshParser(line_reader)

    try:
        #node = main_loop.ParseWholeFile(c_parser)
        node = ParseWholeFile(c_parser)
    except error.Parse as e:
        errfmt.PrettyPrintError(e)
        return 2
    assert node is not None

    if pretty_print:
        tree = node.PrettyTree(True)
        fmt.HNodePrettyPrint(tree, mylib.Stdout())

    return 0


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
