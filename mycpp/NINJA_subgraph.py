"""
mycpp/NINJA_subgraph.py
"""

from __future__ import print_function

import os
import sys

from build.ninja_lib import (log, mycpp_binary, COMPILERS_VARIANTS,
                             OTHER_VARIANTS, SHWRAP)

_ = log


def DefineTargets(ru):

    # Creates _bin/shwrap/mycpp_main
    ru.py_binary('mycpp/mycpp_main.py',
                 deps_base_dir='prebuilt/ninja',
                 template='mycpp')

    # mycpp wrapper that depends on _bin/datalog/dataflow, a binary created
    # from Souffle datalog!
    ru.n.build(
        '_bin/shwrap/mycpp_main_souffle',
        'cp',
        ['bin/mycpp_main_souffle.sh'],
        implicit=['_bin/shwrap/mycpp_main', '_bin/datalog/dataflow'],
    )

    ru.cc_library(
        '//mycpp/runtime',
        # Could separate into //mycpp/runtime_{marksweep,bumpleak}
        srcs=[
            'mycpp/bump_leak_heap.cc',
            'mycpp/gc_builtins.cc',
            'mycpp/gc_iolib.cc',
            'mycpp/gc_mops.cc',
            'mycpp/gc_mylib.cc',
            'mycpp/gc_str.cc',
            'mycpp/hash.cc',
            'mycpp/mark_sweep_heap.cc',
        ])

    # Special test with -D
    ru.cc_binary('mycpp/bump_leak_heap_test.cc',
                 deps=['//mycpp/runtime'],
                 matrix=[
                     ('cxx', 'asan+bumpleak'),
                     ('cxx', 'ubsan+bumpleak'),
                     ('clang', 'ubsan+bumpleak'),
                     ('clang', 'coverage+bumpleak'),
                 ],
                 phony_prefix='mycpp-unit')

    for test_main in [
            'mycpp/mark_sweep_heap_test.cc',
            'mycpp/gc_heap_test.cc',
            'mycpp/gc_stress_test.cc',
            'mycpp/gc_builtins_test.cc',
            'mycpp/gc_iolib_test.cc',
            'mycpp/gc_mops_test.cc',
            'mycpp/gc_mylib_test.cc',
            'mycpp/gc_dict_test.cc',
            'mycpp/gc_list_test.cc',
            'mycpp/gc_str_test.cc',
            'mycpp/gc_tuple_test.cc',
            'mycpp/small_str_test.cc',
    ]:
        ru.cc_binary(test_main,
                     deps=['//mycpp/runtime'],
                     matrix=(COMPILERS_VARIANTS + OTHER_VARIANTS),
                     phony_prefix='mycpp-unit')

    ru.cc_binary(
        'mycpp/float_test.cc',
        deps=['//mycpp/runtime'],
        # Just test two compilers, in fast mode
        matrix=[('cxx', 'opt'), ('clang', 'opt')],
        phony_prefix='mycpp-unit')

    for test_main in [
            'mycpp/demo/gc_header.cc',
            'mycpp/demo/hash_table.cc',
            'mycpp/demo/target_lang.cc',
    ]:
        ru.cc_binary(test_main,
                     deps=['//mycpp/runtime'],
                     matrix=COMPILERS_VARIANTS,
                     phony_prefix='mycpp-unit')

    # ASDL schema that examples/parse.py depends on
    ru.asdl_library('mycpp/examples/expr.asdl')


#
# mycpp/examples build config
#

# TODO:
# - Fold this dependency into a proper shwrap wrapper
# - Make a n.build() wrapper that takes it into account automatically
RULES_PY = 'build/ninja-rules-py.sh'

# special ones in examples.sh:
# - parse
# - lexer_main -- these use Oil code
# - pgen2_demo -- uses pgen2


def ShouldSkipBuild(name):
    if name.startswith('invalid_'):
        return True

    if name in [
            # these use Oil code, and don't type check or compile.  Maybe give up on
            # them?  pgen2_demo might be useful later.
            'lexer_main',
            'pgen2_demo',
    ]:
        return True

    return False


def ExamplesToBuild():
    filenames = os.listdir('mycpp/examples')
    py = [
        name[:-3] for name in filenames
        if name.endswith('.py') and name != '__init__.py'
    ]

    to_test = [name for name in py if not ShouldSkipBuild(name)]

    result = []
    for ex in to_test:
        py_main = 'mycpp/examples/%s.py' % ex
        result.append((ex, py_main))

    return result


def ShouldSkipTest(name):
    return False


def ShouldSkipBenchmark(name):
    return name.startswith('test_')


TRANSLATE_FILES = {
    # TODO: We could also use app_deps.py here
    # BUG: modules.py must be listed last.  Order matters with inheritance
    # across modules!
    'modules': [
        'mycpp/testpkg/module1.py',
        'mycpp/testpkg/module2.py',
        'mycpp/examples/modules.py',
    ],
    'parse': [],  # added dynamically from mycpp/examples/parse.translate.txt
}

# Unused.  Could use mycpp/examples/parse.typecheck.txt
EXAMPLES_PY = {
    'parse': [],
}

EXAMPLES_DEPS = {
    'parse': [
        '//mycpp/runtime',
        '//mycpp/examples/expr.asdl',
        '//cpp/data_lang',
    ],
}

# mycpp-souffle only has three variants for now
SOUFFLE_MATRIX = [
    ('cxx', 'opt'),  # for benchmarks
    #('cxx', 'opt-sh'),  # for benchmarks
    ('cxx', 'asan'),  # need this for running the examples in CI
    ('cxx', 'asan+gcalways'),
]
MYPY_PATH = '$NINJA_REPO_ROOT/mycpp:$NINJA_REPO_ROOT/pyext'

# TODO Next:
# - separate parse.main.cc files, instead of _gen/_tmp


def TranslatorSubgraph(
        ru,
        translator,
        py_main,
        mypy_path,
        py_inputs=None,  # list of source files, including main
        phony_prefix=None,
        matrix=None,
        deps=None):
    """Create rules for a single example."""
    py_inputs = py_inputs or [py_main]  # if not specified, it's a single file
    matrix = matrix or COMPILERS_VARIANTS
    deps = deps or ['//mycpp/runtime']

    n = ru.n

    # e.g. mycpp/examples/parse
    py_rel_path, _ = os.path.splitext(py_main)

    # e.g. mycpp.examples.parse
    py_module = py_rel_path.replace('/', '.')

    ex = os.path.basename(py_rel_path)

    # Two steps
    raw = '_gen/_tmp/%s.%s-raw.cc' % (py_rel_path, translator)
    main_cc_src = '_gen/%s.%s.cc' % (py_rel_path, translator)

    translator_shwrap = SHWRAP[translator]

    n.build(
        raw,
        'translate-%s' % translator,
        py_inputs,  # files to translate
        # Implicit dependency: if the translator changes, regenerate source
        # code.  But don't pass it on the command line.
        implicit=[translator_shwrap],
        # examples/parse uses pyext/fastfunc.pyi
        variables=[('mypypath', mypy_path)])

    p = '%s_preamble.h' % py_rel_path
    preamble = p if os.path.exists(p) else "''"  # Ninja empty string!

    # Make a translation unit
    n.build(main_cc_src,
            'wrap-cc',
            raw,
            implicit=[RULES_PY],
            variables=[
                ('main_namespace', ex),
                ('main_func', 'example-main-wrapper'),
                ('preamble', preamble),
            ])

    n.newline()

    ru.cc_binary(
        main_cc_src,
        deps=deps,
        matrix=matrix,
        phony_prefix=phony_prefix,
    )


def NinjaGraph(ru):
    n = ru.n

    ru.comment('Generated by %s' % __name__)

    # Running build/ninja_main.py
    this_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

    n.variable('NINJA_REPO_ROOT', os.path.dirname(this_dir))
    n.newline()

    # mycpp and pea have the same interface
    n.rule('translate-mycpp',
           command='_bin/shwrap/mycpp_main $mypypath $out $in',
           description='mycpp $mypypath $out $in')
    n.newline()

    n.rule('translate-mycpp-souffle',
           command='_bin/shwrap/mycpp_main_souffle $mypypath $out $in',
           description='mycpp-souffle $mypypath $out $in')
    n.newline()

    n.rule('translate-pea',
           command='_bin/shwrap/pea_main $mypypath $out $in',
           description='pea $mypypath $out $in')
    n.newline()

    n.rule(
        'wrap-cc',
        command=
        'build/ninja-rules-py.sh wrap-cc $out $main_func $main_namespace $in $preamble',
        description='wrap-cc $out $main_func $main_namespace $in $preamble')
    n.newline()
    n.rule(
        'example-task',
        # note: $out can be MULTIPLE FILES, shell-quoted
        command='build/ninja-rules-py.sh example-task $name $impl $bin $out',
        description='example-task $name $impl $bin $out')
    n.newline()
    n.rule(
        'typecheck',
        command='build/ninja-rules-py.sh typecheck $main_py $out $skip_imports',
        description='typecheck $main_py $out $skip_imports')
    n.newline()
    n.rule('logs-equal',
           command='build/ninja-rules-py.sh logs-equal $out $in',
           description='logs-equal $out $in')
    n.newline()
    n.rule('benchmark-table',
           command='build/ninja-rules-py.sh benchmark-table $out $in',
           description='benchmark-table $out $in')
    n.newline()

    # For simplicity, this is committed to the repo.  We could also have
    # build/dev.sh minimal generate it?
    with open('_build/NINJA/mycpp.examples.parse/translate.txt') as f:
        for line in f:
            path = line.strip()
            TRANSLATE_FILES['parse'].append(path)

    examples = ExamplesToBuild()
    #examples = ['cgi', 'containers', 'fib_iter']

    # Groups of targets.  Not all of these are run by default.
    ph = {
        'mycpp-typecheck':
        [],  # optional: for debugging only.  translation does it.
        'mycpp-strip':
        [],  # optional: strip binaries.  To see how big they are.

        # Compare logs for tests AND benchmarks.
        # It's a separate task because we have multiple variants to compare, and
        # the timing of test/benchmark tasks should NOT include comparison.
        'mycpp-logs-equal': [],

        # NOTE: _test/benchmark-table.tsv isn't included in any phony target

        # Targets dynamically added:
        #
        # mycpp-unit-$compiler-$variant
        # mycpp-examples-$compiler-$variant
        'pea-translate': [],
        'pea-compile': [],
        # TODO: eventually we will have pea-logs-equal, and pea-benchmark-table
    }
    ru.AddPhony(ph)

    DefineTargets(ru)

    #
    # Build and run examples/
    #

    ## Pea Examples
    for ex, py_main in examples:
        # Special case: mycpp/examples/pea_* are only translated with pea.
        # TODO: pea examples don't have the same main()

        if ex.startswith('pea_'):
            mycpp_binary(ru,
                         'mycpp.examples.%s' % ex,
                         translator='pea',
                         matrix=[
                             ('cxx', 'asan'),
                             ('cxx', 'opt'),
                         ],
                         deps=['//mycpp/runtime'])

    to_compare = []
    benchmark_tasks = []

    for ex, py_main in examples:
        if ex.startswith('pea_'):  # Only non-pea examples
            continue

        ru.comment('- mycpp/examples/%s' % ex)

        # TODO: make a phony target for these, since they're not strictly necessary.
        # Translation does everything that type checking does.  Type checking only
        # is useful for debugging.
        t = '_test/tasks/typecheck/%s.log.txt' % ex
        main_py = 'mycpp/examples/%s.py' % ex

        # expr.asdl needs to import pylib.collections_, which doesn't type check
        skip_imports = 'T' if (ex == 'parse') else "''"

        ## Type check the example

        n.build(
            [t],
            'typecheck',
            # TODO: Use mycpp/examples/parse.typecheck.txt
            EXAMPLES_PY.get(ex, []) + [main_py],
            variables=[('main_py', main_py), ('skip_imports', skip_imports)])
        n.newline()
        ru.phony['mycpp-typecheck'].append(t)

        ## Run example as Python

        for mode in ['test', 'benchmark']:
            prefix = '_test/tasks/%s/%s.py' % (mode, ex)
            task_out = '%s.task.txt' % prefix

            if mode == 'benchmark':
                if ShouldSkipBenchmark(ex):
                    #log('Skipping benchmark of %s', ex)
                    continue
                benchmark_tasks.append(task_out)

            elif mode == 'test':
                if ShouldSkipTest(ex):
                    #log('Skipping test of %s', ex)
                    continue

            # TODO: This should be a Python stub!
            log_out = '%s.log' % prefix
            n.build([task_out, log_out],
                    'example-task',
                    EXAMPLES_PY.get(ex, []) + ['mycpp/examples/%s.py' % ex],
                    variables=[('bin', main_py), ('name', ex),
                               ('impl', 'Python')])

            n.newline()

        ## Translate the example 2 ways, and benchmark and test it

        for translator in ['mycpp', 'mycpp-souffle']:

            matrix = SOUFFLE_MATRIX if translator == 'mycpp-souffle' else None
            phony_prefix = 'mycpp-examples' if translator == 'mycpp' else None
            py_inputs = TRANSLATE_FILES.get(ex)

            TranslatorSubgraph(ru,
                               translator,
                               py_main,
                               MYPY_PATH,
                               py_inputs=py_inputs,
                               phony_prefix=phony_prefix,
                               matrix=matrix,
                               deps=EXAMPLES_DEPS.get(ex))

            # minimal
            TEST_MATRIX = [
                ('test', 'asan'),  # TODO: asan+gcalways is better!
                ('benchmark', 'opt'),
            ]

            # Run the binary in two ways
            for mode, variant in TEST_MATRIX:
                task_out = '_test/tasks/%s/%s.%s.%s.task.txt' % (
                    mode, ex, translator, variant)

                if mode == 'benchmark':
                    if ShouldSkipBenchmark(ex):
                        #log('Skipping benchmark of %s', ex)
                        continue
                    benchmark_tasks.append(task_out)

                elif mode == 'test':
                    if ShouldSkipTest(ex):
                        #log('Skipping test of %s', ex)
                        continue

                cc_log_out = '_test/tasks/%s/%s.%s.%s.log' % (
                    mode, ex, translator, variant)
                py_log_out = '_test/tasks/%s/%s.py.log' % (mode, ex)

                to_compare.append(cc_log_out)
                to_compare.append(py_log_out)

                # Only test cxx- variant
                b_example = '_bin/cxx-%s/mycpp/examples/%s.%s' % (variant, ex,
                                                                  translator)
                impl = 'C++'
                if translator == 'mycpp-souffle':
                    impl = 'C++-Souffle'

                n.build([task_out, cc_log_out],
                        'example-task', [b_example],
                        variables=[('bin', b_example), ('name', ex),
                                   ('impl', impl)])
                n.newline()

    # Compare the log of all examples
    out = '_test/mycpp-compare-passing.txt'
    n.build([out], 'logs-equal', to_compare)
    n.newline()

    # NOTE: Don't really need this
    ru.phony['mycpp-logs-equal'].append(out)

    # Timing of benchmarks
    out = '_test/benchmark-table.tsv'
    n.build([out], 'benchmark-table', benchmark_tasks)
    n.newline()

    ru.souffle_binary('prebuilt/datalog/call-graph.cc')
    ru.souffle_binary('prebuilt/datalog/dataflow.cc')
    ru.souffle_binary('prebuilt/datalog/smoke-test.cc')
