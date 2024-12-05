#!/usr/bin/env python3
from __future__ import print_function
"""
translate.py - Hook up all the stages
"""

import os
import sys
import tempfile
import time

# Our code
#from _devbuild.gen.mycpp_asdl import mtype

from mycpp import ir_pass
from mycpp import const_pass
from mycpp import cppgen_pass
from mycpp import control_flow_pass
from mycpp import virtual_pass
from mycpp import pass_state
from mycpp.util import log
from mycpp import visitor

from typing import (Dict, List, Tuple, Any, TextIO, TYPE_CHECKING)

if TYPE_CHECKING:
    from mypy.nodes import FuncDef, MypyFile, Expression
    from mypy.types import Type


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


def Run(timer: Timer,
        f: TextIO,
        header_f: TextIO,
        types: Dict['Expression', 'Type'],
        to_header: List[str],
        to_compile: List[Tuple[str, 'MypyFile']],
        stack_roots_warn: bool = False,
        minimize_stack_roots: bool = False) -> int:

    #_ = mtype
    #if 0:
    #    log('m %r' % mtype)
    #    log('m %r' % mtype.Callable)

    f.write("""\
// BEGIN mycpp output

#include "mycpp/runtime.h"

""")

    # [PASS] IR pass could be merged with virtual pass
    timer.Section('mycpp pass: IR')

    dot_exprs: Dict[str, ir_pass.DotExprs] = {}
    for _, module in to_compile:
        module_dot_exprs: ir_pass.DotExprs = {}
        p1 = ir_pass.Build(types, module_dot_exprs)
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
        forward_decls: List[str] = []  # unused
        p2 = virtual_pass.Pass(
            types,
            virtual,  # output
            forward_decls,  # TODO: write output of forward_decls
            all_member_vars,  # output
            all_local_vars,  # output
            yield_out_params,  # output
        )
        # forward declarations may go to header
        p2.SetOutputFile(header_f if name in to_header else f)
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
        p4 = cppgen_pass.Decl(
            types,
            global_strings,  # input
            yield_out_params,
            virtual=virtual,  # input
            all_member_vars=all_member_vars,  # input
        )
        # prototypes may go to a header
        p4.SetOutputFile(header_f if name in to_header else f)
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
        p5 = control_flow_pass.Build(types, virtual, all_local_vars,
                                     dot_exprs[module.path])
        p5.visit_mypy_file(module)
        cfgs.update(p5.cfgs)
        MaybeExitWithErrors(p5)

    # [PASS] Conditionally run Souffle
    stack_roots = None
    if minimize_stack_roots:
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
        timer.Section('mycpp: dumping control flow graph to _tmp/mycpp-facts')

        pass_state.DumpControlFlowGraphs(cfgs)

    timer.Section('mycpp pass: IMPL')

    # [PASS] the definitions / implementations:
    # void Foo:method() { ... }
    # void Bar:method() { ... }
    for name, module in to_compile:
        p6 = cppgen_pass.Impl(
            types,
            global_strings,
            yield_out_params,
            local_vars=all_local_vars,
            all_member_vars=all_member_vars,
            dot_exprs=dot_exprs[module.path],
            stack_roots=stack_roots,
            stack_roots_warn=stack_roots_warn,
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
