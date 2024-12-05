#!/usr/bin/env python3
"""
mycpp_main.py - Translate a subset of Python to C++, using MyPy's typed AST.
"""
from __future__ import print_function

import optparse
import os
import sys
import tempfile
import time

START_TIME = time.time()  # measure before imports

# MyPy deps
from mypy.build import build as mypy_build
from mypy.main import process_options

# Our code
from _devbuild.gen.mycpp_asdl import mtype

from mycpp import ir_pass
from mycpp import const_pass
from mycpp import cppgen_pass
from mycpp import control_flow_pass
from mycpp import virtual_pass
from mycpp import pass_state
from mycpp.util import log
from mycpp import visitor

from typing import Dict, List, Optional, Tuple, Any, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from mypy.nodes import MemberExpr, FuncDef
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
                     mod_names: List[str]) -> Iterator[Tuple[str, Any]]:
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


class Timer:
    """
    Example timings:

    So loading it takes 13.4 seconds, and the rest only takes 2 seconds.  If we
    combine const pass and forward decl pass, that's only a couple hundred
    milliseconds.  So might as well keep them separate.

        [0.1] mycpp: LOADING asdl/format.py ...
        [13.5] mycpp pass: IR
        [13.7] mycpp pass: FORWARD DECL
        [13.8] mycpp pass: CONST
        [14.0] mycpp pass: PROTOTYPES
        [14.4] mycpp pass: CONTROL FLOW
        [15.0] mycpp pass: DATAFLOW
        [15.0] mycpp pass: IMPL
        [15.5] mycpp DONE
    """

    def __init__(self, start_time: float):
        self.start_time = start_time

    def Section(self, msg: str, *args: Any) -> None:
        elapsed = time.time() - self.start_time

        if args:
            msg = msg % args

        #log('\t[%.1f] %s', elapsed, msg)
        log('\t%s', msg)


def main(argv: List[str]) -> int:
    timer = Timer(START_TIME)

    _ = mtype
    if 0:
        log('m %r' % mtype)
        log('m %r' % mtype.Callable)

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
    if 0:
        to_header = [os.path.basename(p) for p in to_header]
        to_header = [os.path.splitext(name)[0] for name in to_header]

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

    # HACK: Why do I get oil.asdl.tdop in addition to asdl.tdop?
    filtered = []
    seen = set()
    for name, module in to_compile:
        if name.startswith('oil.'):
            name = name[4:]

        # ditto with testpkg.module1
        if name.startswith('mycpp.'):
            name = name[6:]

        if name not in seen:  # remove dupe
            filtered.append((name, module))
            seen.add(name)

    to_compile = filtered

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

    f.write("""\
// BEGIN mycpp output

#include "mycpp/runtime.h"

""")

    # [PASS] IR pass could be merged with virtual pass
    timer.Section('mycpp pass: IR')

    dot_exprs: Dict[MemberExpr, ir_pass.DotExprs] = {}
    for _, module in to_compile:
        module_dot_exprs: ir_pass.DotExprs = {}
        p1 = ir_pass.Build(result.types, module_dot_exprs)
        p1.visit_mypy_file(module)
        dot_exprs[module.path] = p1.dot_exprs

        MaybeExitWithErrors(p1)

    # Which functions are C++ 'virtual'?
    virtual = pass_state.Virtual()

    all_member_vars: cppgen_pass.AllMemberVars = {}
    all_local_vars: cppgen_pass.AllLocalVars = {}
    yield_out_params: Dict[FuncDef, Tuple[str, str]] = {}

    # [PASS] namespace foo { class Spam; class Eggs; }
    timer.Section('mycpp pass: FORWARD DECL')

    for name, module in to_compile:
        if name in to_header:
            out_f = header_f
        else:
            out_f = f

        forward_decls: List[str] = []  # unused
        p2 = virtual_pass.Pass(
            result.types,
            virtual,  # output
            forward_decls,  # TODO: write output of forward_decls
            all_member_vars,  # output
            all_local_vars,  # output
            yield_out_params,  # output
        )
        p2.SetOutputFile(out_f)
        p2.visit_mypy_file(module)
        MaybeExitWithErrors(p2)

    # After seeing class and method names in the first pass, figure out which
    # ones are virtual.  We use this info in the second pass.
    virtual.Calculate()
    if 0:
        log('virtuals %s', virtual.virtuals)
        log('has_vtable %s', virtual.has_vtable)

    # [PASS]
    timer.Section('mycpp pass: CONST')

    global_strings = const_pass.GlobalStrings()
    p3 = const_pass.Collect(global_strings)

    for name, module in to_compile:
        p3.visit_mypy_file(module)
        MaybeExitWithErrors(p3)

    global_strings.ComputeStableVarNames()
    # Emit GLOBAL_STR(), never to header
    global_strings.WriteConstants(f)

    # [PASS] C++ declarations like:
    # class Foo { void method(); }; class Bar { void method(); };
    timer.Section('mycpp pass: PROTOTYPES')

    for name, module in to_compile:
        if name in to_header:
            out_f = header_f
        else:
            out_f = f
        p4 = cppgen_pass.Decl(
            result.types,
            global_strings,  # input
            yield_out_params,
            virtual=virtual,  # input
            all_member_vars=all_member_vars,  # input
        )
        p4.SetOutputFile(out_f)
        p4.visit_mypy_file(module)
        MaybeExitWithErrors(p4)

    if 0:
        log('\tall_member_vars')
        from pprint import pformat
        print(pformat(all_member_vars), file=sys.stderr)

    # [PASS]
    timer.Section('mycpp pass: CONTROL FLOW')

    cfgs = {}  # fully qualified function name -> control flow graph
    for name, module in to_compile:
        p5 = control_flow_pass.Build(result.types, virtual, all_local_vars,
                                     dot_exprs[module.path])
        p5.visit_mypy_file(module)
        cfgs.update(p5.cfgs)
        MaybeExitWithErrors(p5)

    stack_roots = None
    if opts.minimize_stack_roots:
        # [PASS]
        timer.Section('mycpp pass: SOUFFLE data flow')

        # souffle_dir contains two subdirectories.
        #   facts: TSV files for the souffle inputs generated by mycpp
        #   outputs: TSV files for the solver's output relations
        souffle_dir = os.getenv('MYCPP_SOUFFLE_DIR', None)
        if souffle_dir is None:
            tmp_dir = tempfile.TemporaryDirectory()
            souffle_dir = tmp_dir.name
        stack_roots = pass_state.ComputeMinimalStackRoots(
            cfgs, souffle_dir=souffle_dir)
    else:  
        # [PASS]
        timer.Section('mycpp: dumping control flow graph to _tmp/mycpp-facts')

        pass_state.DumpControlFlowGraphs(cfgs)

    timer.Section('mycpp pass: IMPL')

    # [PASS] the definitions / implementations:
    # void Foo:method() { ... }
    # void Bar:method() { ... }
    for name, module in to_compile:
        p6 = cppgen_pass.Impl(
            result.types,
            global_strings,
            yield_out_params,
            local_vars=all_local_vars,
            all_member_vars=all_member_vars,
            dot_exprs=dot_exprs[module.path],
            stack_roots=stack_roots,
            stack_roots_warn=opts.stack_roots_warn,
        )
        p6.SetOutputFile(f)  # doesn't go to header
        p6.visit_mypy_file(module)
        MaybeExitWithErrors(p6)

    timer.Section('mycpp DONE')
    return 0  # success


def MaybeExitWithErrors(p: visitor.SimpleVisitor) -> None:
    # Check for errors we collected
    num_errors = len(p.errors_keep_going)
    if num_errors != 0:
        log('')
        log('%s: %d translation errors (after type checking)', sys.argv[0],
            num_errors)

        # A little hack to tell the test-invalid-examples harness how many errors we had
        sys.exit(min(num_errors, 255))


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
