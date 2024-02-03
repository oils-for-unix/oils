#!/usr/bin/env python2
"""
yaks.py - Generate C++ from Yaks IR.

Uses yaks.asdl.

Will this be rewritten as yaks.yaks?
"""
from __future__ import print_function

import optparse
import os
import sys

from typing import List

from _devbuild.gen import yaks_asdl
from yaks import lex



def Options():
    # type: () -> optparse.OptionParser
    """Returns an option parser instance."""

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


def main(argv):
    # type: (List[str]) -> None
    o = Options()
    opts, argv = o.parse_args(argv)

    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    if action == 'cpp':
        path = argv[2]

        m = yaks_asdl.Module('hi', [])
        print(m)

        tokens = lex.Lex('hello there')
        print(tokens)

        with open(path) as f:
            print(f.read())

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('%s: FATAL: %s' % (sys.argv[0], e), file=sys.stderr)
        sys.exit(1)
