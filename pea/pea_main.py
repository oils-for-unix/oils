#!/usr/bin/env python3
"""
pea_main.py

A potential rewrite of mycpp.
"""
import io
import optparse
import pickle
import sys
import time

START_TIME = time.time()

if 0:
    for p in sys.path:
        print('*** syspath: %s' % p)

from typing import Any, Dict, List, Tuple

from mycpp import translate

from pea import gen_cpp
from pea import mypy_shim
from pea import parse
from pea.header import (TypeSyntaxError, Program, log)


def Options() -> optparse.OptionParser:
    """Returns an option parser instance."""

    p = optparse.OptionParser()
    p.add_option('-v',
                 '--verbose',
                 dest='verbose',
                 action='store_true',
                 default=False,
                 help='Show details about translation')

    # Control which modules are exported to the header.  Used by
    # build/translate.sh.
    p.add_option('--to-header',
                 dest='to_header',
                 action='append',
                 default=[],
                 help='Export this module to a header, e.g. frontend.args')

    p.add_option('--header-out',
                 dest='header_out',
                 default=None,
                 help='Write this header')

    return p


def main(argv: list[str]) -> int:

    o = Options()
    opts, argv = o.parse_args(argv)

    action = argv[1]

    # TODO: get rid of 'parse'
    if action in ('parse', 'cpp'):
        files = argv[2:]

        # TODO:
        # pass_state.Virtual
        #   this loops over functions and methods.  But it has to be done BEFORE
        #   the PrototypesPass, or we need two passes.  Gah!
        #   Could it be done in ConstVisitor?  ConstVirtualVisitor?

        # local_vars

        prog = Program()
        log('Pea begin')

        if not parse.ParseFiles(files, prog):
            return 1
        log('Parsed %d files and their type comments', len(files))
        prog.PrintStats()

        # This is the first pass

        const_lookup: dict[str, int] = {}

        v = gen_cpp.ConstVisitor(const_lookup)
        for py_file in prog.py_files:
            v.visit(py_file.module)

        log('Collected %d constants', len(const_lookup))

        # TODO: respect header_out for these two passes
        #out_f = sys.stdout
        out_f = io.StringIO()

        # ForwardDeclPass: module -> class
        # TODO: Move trivial ForwardDeclPass into ParsePass, BEFORE constants,
        # after comparing output with mycpp.
        pass2 = gen_cpp.ForwardDeclPass(out_f)
        for py_file in prog.py_files:
            namespace = py_file.namespace
            pass2.DoPyFile(py_file)

        log('Wrote forward declarations')
        prog.PrintStats()

        try:
            # PrototypesPass: module -> class/method, func

            pass3 = gen_cpp.PrototypesPass(opts, prog, out_f)
            for py_file in prog.py_files:
                pass3.DoPyFile(py_file)  # parses type comments in signatures

            log('Wrote prototypes')
            prog.PrintStats()

            # ImplPass: module -> class/method, func; then probably a fully recursive thing

            pass4 = gen_cpp.ImplPass(prog, out_f)
            for py_file in prog.py_files:
                pass4.DoPyFile(py_file)  # parses type comments in assignments

            log('Wrote implementation')
            prog.PrintStats()

        except TypeSyntaxError as e:
            log('Type comment syntax error on line %d of %s: %r', e.lineno,
                py_file.filename, e.code_str)
            return 1

        log('Done')

    elif action == 'mycpp':
        paths = argv[2:]
        _ = paths

        #log('pea mycpp %s', sys.argv)

        timer = translate.Timer(START_TIME)
        timer.Section('PEA loading %s', ' '.join(paths))

        f = sys.stdout
        header_f = sys.stdout

        # TODO: Dict[Expression, Type]
        types: Dict[Any, Any] = {}

        to_header: List[str] = []
        to_compile: List[Tuple[str, Any]] = []

        for path in paths:
            # defs, imports
            # Ah this is an empty file!
            m = mypy_shim.CreateMyPyFile(path)

            to_compile.append((path, m))

        return translate.Run(timer, f, header_f, types, to_header, to_compile)

    elif action == 'dump-pickles':
        files = argv[2:]

        prog = Program()
        log('Pea begin')

        if not parse.ParseFiles(files, prog):
            return 1
        log('Parsed %d files and their type comments', len(files))
        prog.PrintStats()

        # Note: can't use marshal here, because it only accepts simple types
        pickle.dump(prog.py_files, sys.stdout.buffer)
        log('Dumped pickle')

    elif action == 'load-pickles':
        while True:
            try:
                py_files = pickle.load(sys.stdin.buffer)
            except EOFError:
                break
            log('Loaded pickle with %d files', len(py_files))

    else:
        raise RuntimeError('Invalid action %r' % action)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
