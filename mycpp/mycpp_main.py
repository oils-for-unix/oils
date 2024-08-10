#!/usr/bin/env python3
"""
mycpp_main.py - Translate a subset of Python to C++, using MyPy's typed AST.
"""
from __future__ import print_function

import optparse
import os
import sys

from typing import List, Optional, Tuple

from mypy.build import build as mypy_build
from mypy.build import BuildSource
from mypy.main import process_options

from mycpp import ir_pass
from mycpp import const_pass
from mycpp import cppgen_pass
from mycpp import debug_pass
from mycpp import control_flow_pass
from mycpp import pass_state
from mycpp.util import log


def Options():
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

    p.add_option(
        '--minimize-stack-roots',
        dest='minimize_stack_roots',
        default=False,
        help='Try to minimize the number of GC stack roots.')

    return p


# Copied from mypyc/build.py
def get_mypy_config(
        paths: List[str], mypy_options: Optional[List[str]]
) -> Tuple[List[BuildSource], Options]:
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


def ModulesToCompile(result, mod_names):
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


def main(argv):
    # TODO: Put these in the shell script
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

    log('\tmycpp: LOADING %s', ' '.join(paths))
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
    #if to_header:
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

    #result = emitmodule.parse_and_typecheck(sources, options)
    import time
    start_time = time.time()
    result = mypy_build(sources=sources, options=options)
    #log('elapsed 1: %f', time.time() - start_time)

    if result.errors:
        log('')
        log('-' * 80)
        for e in result.errors:
            log(e)
        log('-' * 80)
        log('')
        return 1

    # Important functions in mypyc/build.py:
    #
    # generate_c (251 lines)
    #   parse_and_typecheck
    #   compile_modules_to_c

    # mypyc/emitmodule.py (487 lines)
    # def compile_modules_to_c(result: BuildResult, module_names: List[str],
    # class ModuleGenerator:
    #   # This generates a whole bunch of textual code!

    # literals, modules, errors = genops.build_ir(file_nodes, result.graph,
    # result.types)

    # TODO: Debug what comes out of here.
    #build.dump_graph(result.graph)
    #return

    # no-op
    if 0:
        for name in result.graph:
            log('result %s %s', name, result.graph[name])
        log('')

    # GLOBAL Constant pass over all modules.  We want to collect duplicate
    # strings together.  And have globally unique IDs str0, str1, ... strN.
    const_lookup = {}  # Dict {StrExpr node => string name}
    const_code = []
    pass1 = const_pass.Collect(result.types, const_lookup, const_code)

    to_compile = list(ModulesToCompile(result, mod_names))

    # HACK: Why do I get oil.asdl.tdop in addition to asdl.tdop?
    #names = set(name for name, _ in to_compile)

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

    #import pickle
    if 0:
        for name, module in to_compile:
            log('to_compile %s', name)
        log('')

        # can't pickle but now I see deserialize() nodes and stuff
        #s = pickle.dumps(module)
        #log('%d pickle', len(s))

    # Print the tree for debugging
    if 0:
        for name, module in to_compile:
            builder = debug_pass.Print(result.types)
            builder.visit_mypy_file(module)
        return

    if opts.cc_out:
        f = open(opts.cc_out, 'w')
    else:
        f = sys.stdout

    f.write("""\
// BEGIN mycpp output

#include "mycpp/runtime.h"

""")

    # Convert the mypy AST into our own IR.
    dot_exprs = {} # module name -> {expr node -> access type}
    log('\tmycpp pass: IR')
    for _, module in to_compile:
        p = ir_pass.Build(result.types)
        p.visit_mypy_file(module)
        dot_exprs[module.path] = p.dot_exprs

    # Collect constants and then emit code.
    log('\tmycpp pass: CONST')
    for name, module in to_compile:
        pass1.visit_mypy_file(module)

    # Instead of top-level code, should we generate a function and call it from
    # main?
    for line in const_code:
        f.write('%s\n' % line)
    f.write('\n')

    # Note: doesn't take into account module names!
    virtual = pass_state.Virtual()

    if opts.header_out:
        header_f = open(opts.header_out, 'w')  # Not closed

    log('\tmycpp pass: FORWARD DECL')

    # Forward declarations first.
    # class Foo; class Bar;
    for name, module in to_compile:
        #log('forward decl name %s', name)
        if name in to_header:
            out_f = header_f
        else:
            out_f = f
        p2 = cppgen_pass.Generate(result.types,
                                  const_lookup,
                                  out_f,
                                  virtual=virtual,
                                  forward_decl=True,
                                  dot_exprs=dot_exprs[module.path])

        p2.visit_mypy_file(module)
        MaybeExitWithErrors(p2)

    # After seeing class and method names in the first pass, figure out which
    # ones are virtual.  We use this info in the second pass.
    virtual.Calculate()
    if 0:
        log('virtuals %s', virtual.virtuals)
        log('has_vtable %s', virtual.has_vtable)

    local_vars = {}  # FuncDef node -> (name, c_type) list
    ctx_member_vars = {
    }  # Dict[ClassDef node for ctx_Foo, Dict[member_name: str, Type]]

    log('\tmycpp pass: PROTOTYPES')

    # First generate ALL C++ declarations / "headers".
    # class Foo { void method(); }; class Bar { void method(); };
    for name, module in to_compile:
        #log('decl name %s', name)
        if name in to_header:
            out_f = header_f
        else:
            out_f = f
        p3 = cppgen_pass.Generate(result.types,
                                  const_lookup,
                                  out_f,
                                  local_vars=local_vars,
                                  ctx_member_vars=ctx_member_vars,
                                  virtual=virtual,
                                  decl=True,
                                  dot_exprs=dot_exprs[module.path])

        p3.visit_mypy_file(module)
        MaybeExitWithErrors(p3)

    if 0:
        log('\tctx_member_vars')
        from pprint import pformat
        print(pformat(ctx_member_vars), file=sys.stderr)

    log('\tmycpp pass: CONTROL FLOW')

    cfgs = {}  # fully qualified function name -> control flow graph
    for name, module in to_compile:
        cfg_pass = control_flow_pass.Build(result.types, virtual, local_vars,
                                           dot_exprs[module.path])
        cfg_pass.visit_mypy_file(module)
        cfgs.update(cfg_pass.cfgs)

    log('\tmycpp pass: DATAFLOW')
    stack_roots = None
    if opts.minimize_stack_roots:
        stack_roots = pass_state.ComputeMinimalStackRoots(cfgs)
    else:
        pass_state.DumpControlFlowGraphs(cfgs)

    log('\tmycpp pass: IMPL')

    # Now the definitions / implementations.
    # void Foo:method() { ... }
    # void Bar:method() { ... }
    for name, module in to_compile:
        p4 = cppgen_pass.Generate(result.types,
                                  const_lookup,
                                  f,
                                  local_vars=local_vars,
                                  ctx_member_vars=ctx_member_vars,
                                  stack_roots_warn=opts.stack_roots_warn,
                                  dot_exprs=dot_exprs[module.path],
                                  stack_roots=stack_roots)
        p4.visit_mypy_file(module)
        MaybeExitWithErrors(p4)

    return 0  # success


def MaybeExitWithErrors(p):
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
