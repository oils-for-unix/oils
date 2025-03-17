#!/usr/bin/env python3
from __future__ import print_function
"""
mycpp_main.py - Translate a subset of Python to C++, using MyPy's typed AST.
"""

import optparse
import os
import sys
import time

START_TIME = time.time()  # measure before imports

# MyPy deps
from mypy.build import build as mypy_build
from mypy.main import process_options

from mycpp.util import log
from mycpp import translate

from typing import (List, Optional, Tuple, Any, Iterator, TYPE_CHECKING)

if TYPE_CHECKING:
    from mypy.nodes import MypyFile
    from mypy.modulefinder import BuildSource
    from mypy.build import BuildResult


def Options() -> optparse.OptionParser:
    """Returns an option parser instance."""

    p = optparse.OptionParser()
    p.add_option('-v',
                 '--verbose',
                 dest='verbose',
                 action='store_true',
                 default=False,
                 help='Show details about translation')

    p.add_option('--cc-out',
                 dest='cc_out',
                 default=None,
                 help='.cc file to write to')

    p.add_option('--to-header',
                 dest='to_header',
                 action='append',
                 default=[],
                 help='Export this module to a header, e.g. frontend.args')

    p.add_option('--header-out',
                 dest='header_out',
                 default=None,
                 help='Write this header')

    p.add_option(
        '--stack-roots-warn',
        dest='stack_roots_warn',
        default=None,
        type='int',
        help='Emit warnings about functions with too many stack roots')

    p.add_option('--minimize-stack-roots',
                 dest='minimize_stack_roots',
                 action='store_true',
                 default=False,
                 help='Try to minimize the number of GC stack roots.')

    return p


# Copied from mypyc/build.py
def get_mypy_config(
        paths: List[str],
        mypy_options: Optional[List[str]]) -> Tuple[List['BuildSource'], Any]:
    """Construct mypy BuildSources and Options from file and options lists"""
    # It is kind of silly to do this but oh well
    mypy_options = mypy_options or []
    mypy_options.append('--')
    mypy_options.extend(paths)

    sources, options = process_options(mypy_options)

    options.show_traceback = True
    # Needed to get types for all AST nodes
    options.export_types = True
    # TODO: Support incremental checking
    options.incremental = False
    # 10/2019: FIX for MyPy 0.730.  Not sure why I need this but I do.
    options.preserve_asts = True

    # 1/2023: Workaround for conditional import in osh/builtin_comp.py
    # Same as devtools/types.sh
    options.warn_unused_ignores = False

    for source in sources:
        options.per_module_options.setdefault(source.module,
                                              {})['mypyc'] = True

    return sources, options


_FIRST = ('asdl.runtime', 'core.vm')

# should be LAST because they use base classes
_LAST = ('builtin.bracket_osh', 'builtin.completion_osh', 'core.shell')


def ModulesToCompile(result: 'BuildResult',
                     mod_names: List[str]) -> Iterator[Tuple[str, 'MypyFile']]:
    # HACK TO PUT asdl/runtime FIRST.
    #
    # Another fix is to hoist those to the declaration phase?  Not sure if that
    # makes sense.

    # FIRST files.  Somehow the MyPy builder reorders the modules.
    for name, module in result.files.items():
        if name in _FIRST:
            yield name, module

    for name, module in result.files.items():
        # Only translate files that were mentioned on the command line
        suffix = name.split('.')[-1]
        if suffix not in mod_names:
            continue

        if name in _FIRST:  # We already did these
            continue

        if name in _LAST:  # We'll do these later
            continue

        yield name, module

    # LAST files
    for name, module in result.files.items():
        if name in _LAST:
            yield name, module


def _DedupeHack(
        to_compile: List[Tuple[str,
                               'MypyFile']]) -> List[Tuple[str, 'MypyFile']]:
    # Filtering step
    filtered = []
    seen = set()
    for name, module in to_compile:
        # HACK: Why do I get oil.asdl.tdop in addition to asdl.tdop?
        if name.startswith('oil.'):
            name = name[4:]

        # ditto with testpkg.module1
        if name.startswith('mycpp.'):
            name = name[6:]

        if name not in seen:  # remove dupe
            filtered.append((name, module))
            seen.add(name)
    return filtered


def main(argv: List[str]) -> int:
    timer = translate.Timer(START_TIME)

    # Hack:
    mypy_options = [
        '--py2',
        '--strict',
        '--no-implicit-optional',
        '--no-strict-optional',
        # for consistency?
        '--follow-imports=silent',
        #'--verbose',
    ]

    o = Options()
    opts, argv = o.parse_args(argv)
    paths = argv[1:]  # e.g. asdl/typed_arith_parse.py

    timer.Section('mycpp: LOADING %s', ' '.join(paths))

    #log('\tmycpp: MYPYPATH = %r', os.getenv('MYPYPATH'))

    if 0:
        print(opts)
        print(paths)
        return

    # e.g. asdl/typed_arith_parse.py -> 'typed_arith_parse'
    mod_names = [os.path.basename(p) for p in paths]
    mod_names = [os.path.splitext(name)[0] for name in mod_names]

    # Ditto
    to_header = opts.to_header

    #log('to_header %s', to_header)

    sources, options = get_mypy_config(paths, mypy_options)
    if 0:
        for source in sources:
            log('source %s', source)
        log('')
    #log('options %s', options)

    #
    # Type checking, which builds a Dict[Expression, Type] (12+ seconds)
    #
    result = mypy_build(sources=sources, options=options)

    if result.errors:
        log('')
        log('-' * 80)
        for e in result.errors:
            log(e)
        log('-' * 80)
        log('')
        return 1

    # no-op
    if 0:
        for name in result.graph:
            log('result %s %s', name, result.graph[name])
        log('')

    to_compile = list(ModulesToCompile(result, mod_names))
    to_compile = _DedupeHack(to_compile)

    if 0:
        for name, module in to_compile:
            log('to_compile %s', name)
        log('')
        #import pickle
        # can't pickle but now I see deserialize() nodes and stuff
        #s = pickle.dumps(module)
        #log('%d pickle', len(s))

    if opts.cc_out:
        f = open(opts.cc_out, 'w')
    else:
        f = sys.stdout

    header_f = None
    if opts.header_out:
        header_f = open(opts.header_out, 'w')  # Not closed

    return translate.Run(timer,
                         f,
                         header_f,
                         result.types,
                         to_header,
                         to_compile,
                         stack_roots_warn=opts.stack_roots_warn,
                         minimize_stack_roots=opts.minimize_stack_roots)


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
