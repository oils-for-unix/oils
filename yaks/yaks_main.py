#!/usr/bin/env python2
"""
yaks.py - Generate C++ from Yaks IR.

Uses yaks.asdl.

Will this be rewritten as yaks.yaks?
"""
from __future__ import print_function

#import optparse
#import os
import sys

from typing import List

from _devbuild.gen import yaks_asdl
#from _devbuild.gen import nil8_asdl
from asdl import format as fmt
from data_lang import j8
from mycpp import mylib
#from yaks import lex
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

    stdout_ = mylib.Stdout()
    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    if action == 'cpp':

        path = argv[2]
        #with open(path) as f:
        #    contents = f.read()

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
        node = p.ParseNil8()

        #print(obj)

        # Dump ASDL representation
        # We could also have a NIL8 printer
        pretty_f = fmt.DetectConsoleOutput(stdout_)
        fmt.PrintTree(node.PrettyTree(), pretty_f)
        stdout_.write('\n')

        # TODO:
        #
        # - Use nvalue representation I think
        #   - nvalue can be converted to value for manipulating in Oils
        #     - nvalue.Record becomes a Dict
        #     - since field names must be identifier names, you're guaranteed
        #       to have 0 1 2 3 available, so node.0 is fine
        # - Then convert nvalue to a static representation in yaks.asdl
        # - Then a few mycpp passes over this representation
        #   - not sure if we'll need any more IRs

    elif action == 'test':
        if mylib.PYTHON:
            path = argv[2]

            m = yaks_asdl.Module('hi', [])
            #print(m)

            #tokens = lex.Lex('hello there')
            #print(tokens)

            #with open(path) as f:
            #    print(f.read())

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
