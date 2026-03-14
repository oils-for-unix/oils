#!/usr/bin/env python2
"""
asdl_main.py - Generate Python and C from ASDL schemas.
"""
from __future__ import print_function

import optparse
import os
import sys

from asdl import front_end
from asdl import gen_cpp
from asdl import gen_python
from asdl import metrics
from asdl.util import log

from typing import Dict
from typing import Any
from typing import List

ARG_0 = os.path.basename(sys.argv[0])


def Options():
    # type: () -> Any
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

    p.add_option('--abbrev-module',
                 dest='abbrev_module',
                 default=None,
                 help='Import this module to find abbreviations')

    return p


class Abbrev(object):
    """A struct for convenience"""

    def __init__(self, module=None, ns=None, mod_entries=None):
        # type: (str, str, List[str]) -> None
        self.module = module
        self.ns = ns
        self.mod_entries = mod_entries


def main(argv):
    # type: (List[str]) -> None
    o = Options()
    opts, argv = o.parse_args(argv)

    try:
        action = argv[1]
    except IndexError:
        raise RuntimeError('Action required')

    try:
        schema_path = argv[2]
    except IndexError:
        raise RuntimeError('Schema path required')

    schema_filename = os.path.basename(schema_path)

    abbrev = Abbrev()
    abbrev.module = opts.abbrev_module
    if opts.abbrev_module:
        # Weird Python rule for importing: fromlist needs to be non-empty.
        abbrev_mod = __import__(opts.abbrev_module, fromlist=['.'])
        abbrev.mod_entries = dir(abbrev_mod)
        abbrev.ns = opts.abbrev_module.split('.')[-1]  # e.g. syntax_abbrev
    else:
        abbrev_mod = None
        abbrev.mod_entries = []
        abbrev.ns = None

    if action == 'metrics':  # Sum type metrics
        with open(schema_path) as f:
            schema_ast, _ = front_end.LoadSchema(f)

        v = metrics.MetricsVisitor(sys.stdout)
        v.VisitModule(schema_ast)

    elif action == 'closure':  # count all types that command_t references
        type_name = argv[3]
        with open(schema_path) as f:
            schema_ast, type_lookup = front_end.LoadSchema(f)

        seen = {}  # type: Dict[str, bool]
        c = metrics.ClosureWalk(type_lookup, seen)
        c.DoModule(schema_ast, type_name)
        for name in sorted(seen):
            print(name)
        log('SHARED (%d): %s', len(c.shared), ' '.join(sorted(c.shared)))

    elif action == 'c':  # Generate C code for the lexer
        with open(schema_path) as f:
            schema_ast, _ = front_end.LoadSchema(f)

        v0 = gen_cpp.CEnumVisitor(sys.stdout)
        v0.VisitModule(schema_ast)

    elif action == 'cpp':  # Generate C++ code for ASDL schemas
        out_prefix = argv[3]
        try:
            debug_info_path = argv[4]
        except IndexError:
            debug_info_path = None

        with open(schema_path) as f:
            schema_ast, _ = front_end.LoadSchema(f)

        # asdl/typed_arith.asdl -> typed_arith_asdl
        ns = os.path.basename(schema_path).replace('.', '_')

        debug_info = gen_cpp.WriteHeaderFile(schema_ast, ARG_0, ns,
                                             opts.pretty_print_methods,
                                             out_prefix)

        if debug_info_path:
            gen_cpp.WriteDebugInfo(debug_info, ns, debug_info_path)

        if not opts.pretty_print_methods:
            # No .cc file at all
            return

        gen_cpp.WriteCppFile(schema_ast, ARG_0, ns, abbrev, out_prefix)

    elif action == 'mypy':  # Generated typed MyPy code
        with open(schema_path) as f:
            schema_ast, _ = front_end.LoadSchema(f)

        v4 = gen_python.GenMyPyVisitor(
            sys.stdout,
            opts.abbrev_module,
            abbrev.mod_entries,
            pretty_print_methods=opts.pretty_print_methods,
            py_init_n=opts.py_init_n)
        v4.VisitModule(schema_ast)

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    try:
        main(sys.argv)
    except RuntimeError as e:
        print('%s: FATAL: %s' % (ARG_0, e), file=sys.stderr)
        sys.exit(1)
