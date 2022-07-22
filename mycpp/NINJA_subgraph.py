#!/usr/bin/env python2
"""
mycpp/NINJA_subgraph.py

This is a library invoked by ./NINJA_config.py

Code Layout:

  mycpp/
    NINJA_subgraph.py  # This file describes dependencies programmatically
    NINJA-steps.sh     # Invoked by Ninja rules

    build.sh           # wrappers invoked by the Toil and devtools/release.sh
    test.sh            # test driver for unit tests and examples

    examples/
      cgi.py
      varargs.py
      varargs_leaky_preamble.h

Output Layout:

  _bin/

    cxx-dbg/
      mycpp-examples/
        cgi
        classes

    cxx-opt/
      mycpp-examples/
        cgi.stripped

    cxx-testgc/
      mycpp-unit/
        gc_heap_test

  _test/
    gen-mycpp/  # rewrite
      varargs_raw.cc
      varargs.cc
    gen-pea/
      varargs_raw.cc
      varargs.cc

    tasks/        # *.txt and *.task.txt for .wwz
      typecheck/  # optionally run
      test/       # py, testgc, asan, opt
      benchmark/
      unit/

      # optionally logged?
      translate/
      compile/

  Phony Targets
    typecheck, strip, benchmark-table, etc. (See phony dict below)

Also:

- .wwz archive of all the logs.
- Turn it into HTML and link to logs.  Basically just like Toil does.

Notes for Oil: 

- escape_path() in ninja_syntax seems wrong?
  - It should really take $ to $$.
  - It doesn't escape newlines

    return word.replace('$ ', '$$ ').replace(' ', '$ ').replace(':', '$:')

  Ninja shouldn't have used $ and ALSO used shell commands (sh -c)!  Better
  solutions:

  - Spawn a process with environment variables.
  - use % for substitution instead

- Another problem: Ninja doesn't escape the # comment character like $#, so
  how can you write a string with a # as the first char on a line?
"""

from __future__ import print_function

import os
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# special ones in examples.sh:
# - parse
# - lexer_main -- these use Oil code
# - pgen2_demo -- uses pgen2

def ShouldSkipBuild(name):
  if name in [
      # these 3 use Oil code, and don't type check or compile
      # Maybe give up on these?  pgen2_demo might be useful later.
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

  return to_test


def ShouldSkipTest(name):
  # '%5d' doesn't work yet.  TODO: fix this.
  if name in (
      'strings',
    ):
    return True

  return False


def ShouldSkipBenchmark(name):
  if name.startswith('test_'):
    return True

  # two crashes

  # BUG: Assertion failure here!
  if name == 'cartesian':
    return True
  # This crashes with an assertion -- probably because ASDL has no GC header!
  if name == 'parse':
    return True

  # two differences

  # BUG: 8191 exceptions problem, I think caused by Alloc<ParseError>
  if name == 'control_flow':
    return True
  # BUG: Different number of iterations!
  if name == 'files':
    return True

  return False


GC_RUNTIME = [
    'mycpp/gc_builtins.cc', 'mycpp/gc_mylib.cc', 'mycpp/gc_heap.cc',
    # files we haven't added StackRoots to
    'mycpp/leaky_types.cc',
    ]

UNIT_TESTS = {
    'mycpp/mylib_old_test': ['mycpp/mylib_old.cc', 'mycpp/leaky_types.cc'],
    'mycpp/gc_heap_test': ['mycpp/gc_heap.cc'],
    'mycpp/gc_stress_test': GC_RUNTIME,
    'mycpp/gc_builtins_test': GC_RUNTIME,
    'mycpp/gc_mylib_test': GC_RUNTIME,

    # leaky bindings run against the GC runtime!
    'mycpp/leaky_types_test': GC_RUNTIME,

    'mycpp/demo/target_lang': ['cpp/leaky_dumb_alloc.cc', 'mycpp/gc_heap.cc'],

    # there is also demo/{gc_heap,square_heap}.cc
}

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

EXAMPLES_PY = {
    'parse': [],  # added dynamically
}

EXAMPLES_CC = {
    'parse': ['_test/asdl/expr_asdl.cc'],
}


def TranslatorSubgraph(n, translator, ex, to_compare, benchmark_tasks, phony):
  raw = '_test/gen-%s/%s_raw.cc' % (translator, ex)

  # Translate to C++
  if ex in TRANSLATE_FILES:
    to_translate = TRANSLATE_FILES[ex]
  else:
    to_translate = ['mycpp/examples/%s.py' % ex]
  n.build(raw, 'translate-%s' % translator, to_translate)

  p = 'mycpp/examples/%s_preamble.h' % ex
  # Ninja empty string!
  preamble_path = p if os.path.exists(p) else "''"

  cc_src = '_test/gen-%s/%s.cc' % (translator, ex)
  # Make a translation unit
  n.build(cc_src, 'wrap-cc', raw,
          variables=[('name', ex), ('preamble_path', preamble_path)])
  n.newline()

  if translator == 'pea':
    phony['pea-translate'].append(cc_src)

  if translator == 'mycpp':
    example_matrix = [
        ('cxx', 'testgc'),
        ('cxx', 'asan'),
        ('cxx', 'ubsan'),
        ('cxx', 'opt'),

        ('clang', 'ubsan'),  # Finds more bugs!
        ('clang', 'coverage'),
    ]
  else:
    example_matrix = [
        ('cxx', 'testgc')
    ]  # pea just has one variant for now

  # Compile C++.
  for compiler, variant in example_matrix:
    b = '_bin/%s-%s/%s-examples/%s' % (compiler, variant, translator, ex)

    example_vars = [
        ('compiler', compiler), ('variant', variant), ('more_cxx_flags', "''")
    ]
    n.build(b, 'compile_and_link',  # defined in cpp/NINJA-steps.sh
            [cc_src] + GC_RUNTIME + EXAMPLES_CC.get(ex, []),
            variables=example_vars)
    n.newline()

    if translator == 'pea':
      phony['pea-compile'].append(b)

    if translator == 'mycpp':
      key = 'mycpp-examples-%s-%s' % (compiler, variant)
      if key not in phony:
        phony[key] = []
      phony[key].append(b)

    if variant == 'opt':
      stripped = '_bin/cxx-%s/%s-examples/%s.stripped' % (variant, translator, ex)
      # no symbols
      n.build([stripped, ''], 'strip', [b],
              variables=[('variant', variant)])
      n.newline()
      phony['mycpp-strip'].append(stripped)


  # Don't run it for now; just compile
  if translator == 'pea':
    return

  # minimal
  MATRIX = [
      ('test', 'asan'),  # TODO: testgc is better!
      ('benchmark', 'opt'),
  ]

  # Run the binary in two ways
  for mode, variant in MATRIX:
    task_out = '_test/tasks/%s/%s.%s.task.txt' % (mode, ex, variant)

    if mode == 'benchmark':
      if ShouldSkipBenchmark(ex):
        #log('Skipping benchmark of %s', ex)
        continue
      benchmark_tasks.append(task_out)

    elif mode == 'test':
      if ShouldSkipTest(ex):
        #log('Skipping test of %s', ex)
        continue

    cc_log_out = '_test/tasks/%s/%s.%s.log.txt' % (mode, ex, variant)
    py_log_out = '_test/tasks/%s/%s.py.log.txt' % (mode, ex)

    to_compare.append(cc_log_out)
    to_compare.append(py_log_out)

    b_example = '_bin/cxx-%s/%s-examples/%s' % (variant, translator, ex)
    n.build([task_out, cc_log_out], 'example-task', [b_example],
            variables=[
              ('bin', b_example),
              ('name', ex), ('impl', 'C++')])
    n.newline()


def NinjaGraph(n):

  n.comment('Translate, compile, and test mycpp examples.')
  n.comment('Generated by %s.' % __name__)
  n.newline()

  n.rule('touch',
         command='touch $out',
         description='touch $out')
  n.newline()
  n.rule('asdl-mypy',
         command='mycpp/NINJA-steps.sh asdl-mypy $in $out',
         description='asdl-mypy $in $out')
  n.newline()
  n.rule('asdl-cpp',
         command='mycpp/NINJA-steps.sh asdl-cpp $in $out_prefix',
         description='asdl-cpp $in $out_prefix')
  n.newline()

  # Two translators
  n.rule('translate-mycpp',
         command='mycpp/NINJA-steps.sh translate-mycpp $out $in',
         description='translate-mycpp $out $in')
  n.newline()
  n.rule('translate-pea',
         command='mycpp/NINJA-steps.sh translate-pea $out $in',
         description='translate-pea $out $in')
  n.newline()

  n.rule('wrap-cc',
         command='mycpp/NINJA-steps.sh wrap-cc $name $in $preamble_path $out',
         description='wrap-cc $name $in $preamble_path $out')
  n.newline()
  n.rule('task',
         # note: $out can be MULTIPLE FILES, shell-quoted
         command='mycpp/NINJA-steps.sh task $in $out',
         description='task $in $out')
  n.newline()
  n.rule('example-task',
         # note: $out can be MULTIPLE FILES, shell-quoted
         command='mycpp/NINJA-steps.sh example-task $name $impl $bin $out',
         description='example-task $name $impl $bin $out')
  n.newline()
  n.rule('typecheck',
         command='mycpp/NINJA-steps.sh typecheck $main_py $out $skip_imports',
         description='typecheck $main_py $out $skip_imports')
  n.newline()
  n.rule('logs-equal',
         command='mycpp/NINJA-steps.sh logs-equal $out $in',
         description='logs-equal $out $in')
  n.newline()
  n.rule('benchmark-table',
         command='mycpp/NINJA-steps.sh benchmark-table $out $in',
         description='benchmark-table $out $in')
  n.newline()

  # For simplicity, this is committed to the repo.  We could also have
  # build/dev.sh minimal generate it?
  with open('mycpp/examples/parse.translate.txt') as f:
    for line in f:
      path = line.strip()
      TRANSLATE_FILES['parse'].append(path)

  examples = ExamplesToBuild()
  #examples = ['cgi', 'containers', 'fib_iter']

  # Groups of targets.  Not all of these are run by default.
  phony = {
      # The 'mycpp-all' target is currently everything that starts with mycpp.
      # Or should this be mycpp-default / mycpp-logs-equal?

      'mycpp-typecheck': [],  # optional: for debugging only.  translation does it.
      'mycpp-strip': [],  # optional: strip binaries.  To see how big they are.

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

  #
  # Build and run unit tests
  #

  for test_path in sorted(UNIT_TESTS):
    cc_files = UNIT_TESTS[test_path]

    # assume names are unique
    test_name = os.path.basename(test_path)

    UNIT_TEST_MATRIX = [
        ('cxx', 'dbg'),
        ('cxx', 'testgc'),

        # Clang and GCC have different implementations of ASAN and UBSAN
        ('cxx', 'asan'),
        ('cxx', 'ubsan'),

        ('clang', 'asan'),
        ('clang', 'ubsan'),

        ('clang', 'coverage'),
    ]

    for (compiler, variant) in UNIT_TEST_MATRIX:
      b = '_bin/%s-%s/mycpp-unit/%s' % (compiler, variant, test_name)

      main_cc = '%s.cc' % test_path

      # for gHeap.Report() and Protect()
      mycpp_unit_flags = '-D GC_DEBUG -D GC_PROTECT'

      if test_name == 'mylib_old_test':
        mycpp_unit_flags += ' -D LEAKY_BINDINGS'

      # Don't get collection here yet
      if test_name == 'leaky_types_test' and variant == 'testgc':
        continue

      unit_test_vars = [
          ('compiler', compiler),
          ('variant', variant),
          ('more_cxx_flags', "'%s'" % mycpp_unit_flags)
      ]

      n.build([b], 'compile_and_link', [main_cc] + cc_files,
              variables=unit_test_vars)
      n.newline()

      key = 'mycpp-unit-%s-%s' % (compiler, variant)
      if key not in phony:
        phony[key] = []
      phony[key].append(b)


  #
  # ASDL schema that examples/parse.py depends on
  #

  prefix = '_test/asdl/expr_asdl'
  n.build([prefix + '.cc', prefix + '.h'], 'asdl-cpp', 'mycpp/examples/expr.asdl',
          variables=[('out_prefix', prefix)])

  #
  # Build and run examples/
  #

  to_compare = []
  benchmark_tasks = []

  for ex in examples:
    n.comment('---')
    n.comment(ex)
    n.comment('---')
    n.newline()

    # TODO: make a phony target for these, since they're not strictly necessary.
    # Translation does everything that type checking does.  Type checking only
    # is useful for debugging.
    t = '_test/tasks/typecheck/%s.log.txt' % ex
    main_py = 'mycpp/examples/%s.py' % ex

    # expr.asdl needs to import pylib.collections_, which doesn't type check
    skip_imports = 'T' if (ex == 'parse') else "''"

    n.build([t], 'typecheck', 
            # TODO: Use mycpp/examples/parse.typecheck.txt
            EXAMPLES_PY.get(ex, []) + [main_py],
            variables=[('main_py', main_py), ('skip_imports', skip_imports)])
    n.newline()
    phony['mycpp-typecheck'].append(t)

    # Run Python.
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

      log_out = '%s.log.txt' % prefix
      n.build([task_out, log_out], 'example-task',
              EXAMPLES_PY.get(ex, []) + ['mycpp/examples/%s.py' % ex],
              variables=[
                  ('bin', main_py),
                  ('name', ex), ('impl', 'Python')])

      n.newline()

    for translator in ['mycpp', 'pea']:
      TranslatorSubgraph(n, translator, ex, to_compare, benchmark_tasks, phony)

  # Compare the log of all examples
  out = '_test/logs-equal.txt'
  n.build([out], 'logs-equal', to_compare)
  n.newline()

  phony['mycpp-logs-equal'].append(out)

  # Timing of benchmarks
  out = '_test/benchmark-table.tsv'
  n.build([out], 'benchmark-table', benchmark_tasks)
  n.newline()

  #
  # Write phony rules we accumulated
  #

  mycpp_all = []
  pea_all = []
  for name in sorted(phony):
    deps = phony[name]
    if deps:
      n.build([name], 'phony', deps)
      n.newline()

      if name.startswith('mycpp-'):
        mycpp_all.append(name)
      if name.startswith('pea-'):
        pea_all.append(name)

  # All groups
  n.build(['mycpp-all'], 'phony', mycpp_all)
  n.build(['pea-all'], 'phony', pea_all)

