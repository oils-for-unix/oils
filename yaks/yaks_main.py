#!/usr/bin/env python2
"""
yaks_main.py - Generate C++ from Yaks IR.

Uses yaks.asdl.  Will this be rewritten as yaks_main.yaks?
"""
from __future__ import print_function

import sys

from _devbuild.gen import yaks_asdl
from asdl import format as fmt
from core import error
from data_lang import j8
from mycpp import mylib
from yaks import transform
from yaks import gen_cpp

from typing import List
"""
def Options():
    # type: () -> optparse.OptionParser
    "Returns an option parser instance."

    p = optparse.OptionParser()
    p.add_option('--no-pretty-print-methods',
                 dest='pretty_print_methods',
                 action='store_false',
                 default=True,
                 help='Whether to generate pretty printing methods')

    # Control Python constructors

    # for hnode.asdl
    p.add_option('--py-init-N',
                 dest='py_init_n',
                 action='store_true',
                 default=False,
                 help='Generate Python __init__ that requires every field')

    # The default, which matches C++
    p.add_option(
        '--init-zero-N',
        dest='init_zero_n',
        action='store_true',
        default=True,
        help='Generate 0 arg and N arg constructors, in Python and C++')

    return p
"""


def main(argv):
    # type: (List[str]) -> int

    #o = Options()
    #opts, argv = o.parse_args(argv)

    stderr_ = mylib.Stderr()
    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    if action == 'cpp':
        # Usage:
        # - Specify a root file - each file contains a module
        #   - this module may or may not contain main()
        # - then it will walk imports, and create a big list of modules
        # - then does it make a SINGLE translation unit for all modules?
        # - and then maybe generate a unit test that links the translation unit
        #   and calls a function?
        #   - I suppose we could add main() to each module, like core/ and osh/

        path = argv[2]
        #with open(path) as f:
        #    contents = f.read()

        # TODO: could implement mylib.SlurpFile()
        lines = []  # type: List[str]
        f = mylib.open(path)
        while True:
            line = f.readline()
            if len(line) == 0:
                break
            lines.append(line)

        #contents = '(print "hi")'
        contents = ''.join(lines)

        p = j8.Nil8Parser(contents, True)

        try:
            nval = p.ParseNil8()
        except error.Decode as e:
            # print e.SourceLine() ?

            # Do we also want ~~~ ^ ~~~ type of hints?
            # Or just ^ and ^~~~~ ?
            #
            # I think the default is the former
            #
            # Data could perhaps use ~~~^

            # factor this out of core/ui.py
            # print util.LocationAsciiArt(e.begin_col, e.end_col) ?

            # ui._PrintCodeExcerpt()
            # Could also be in error

            if mylib.PYTHON:
                print(e.Message(), file=sys.stderr)
            return 1

        #print(obj)

        # Dump ASDL representation
        # We could also have a NIL8 printer
        fmt.HNodePrettyPrint(nval.PrettyTree(False), stderr_)
        #stderr_.write('\n')

        prog = transform.Transform(nval)

        fmt.HNodePrettyPrint(prog.PrettyTree(False), stderr_)

        # TODO: a few mycpp passes over this representation
        #   - not sure if we'll need any more IRs
        gen_cpp.GenCpp(prog, mylib.Stdout())

    elif action == 'check':
        # Only do type checking?

        path = argv[2]

        m = yaks_asdl.Module('hi', [])

        fmt.HNodePrettyPrint(m.PrettyTree(False), stderr_)
        #stderr_.write('\n')

    else:
        raise RuntimeError('Invalid action %r' % action)

    return 0


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('%s: FATAL: %s' % (sys.argv[0], e), file=sys.stderr)
        sys.exit(1)

# vim: sw=4
