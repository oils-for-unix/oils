"""
mycpp/NINJA_subgraph.py
"""

from __future__ import print_function

import os
import sys

from build.ninja_lib import log, COMPILERS_VARIANTS

def DefineTargets(ru):

  ru.py_binary(
      'mycpp/mycpp_main.py',
      deps_base_dir = 'prebuilt/ninja',
      template = 'mycpp')

  ru.cc_library(
      '//mycpp/cheney_heap', 
      srcs = ['mycpp/cheney_heap.cc'])

  # special test with -D
  ru.cc_binary(
      'mycpp/cheney_heap_test.cc',
      deps = ['//mycpp/cheney_heap'],
      matrix = [
        ('cxx', 'asan+cheney'),
        ('cxx', 'ubsan+cheney'),
        ('clang', 'coverage+cheney'),
      ],
      phony_prefix = 'mycpp-unit')

  ru.cc_library(
      '//mycpp/runtime', 
      # TODO: separate into //mycpp/runtime_{marksweep,bumpleak,cheney}
      deps = [ '//mycpp/cheney_heap' ],
      srcs = [
        'mycpp/bump_leak_heap.cc',
        'mycpp/gc_builtins.cc',
        'mycpp/gc_mylib.cc',
        'mycpp/gc_str.cc',
        'mycpp/mark_sweep_heap.cc',
      ]
  )

  # Special test with -D
  ru.cc_binary(
      'mycpp/bump_leak_heap_test.cc',
      deps = ['//mycpp/runtime'],
      matrix = [
        ('cxx', 'asan+bumpleak'),
        ('cxx', 'ubsan+bumpleak'),
        ('clang', 'coverage+bumpleak'),
      ],
      phony_prefix = 'mycpp-unit')

  for test_main in [
      'mycpp/mark_sweep_heap_test.cc',
      'mycpp/gc_heap_test.cc',
      'mycpp/gc_stress_test.cc',

      'mycpp/gc_builtins_test.cc',
      'mycpp/gc_mylib_test.cc',

      'mycpp/gc_dict_test.cc',
      'mycpp/gc_list_test.cc',
      'mycpp/gc_str_test.cc',
      'mycpp/gc_tuple_test.cc',

      'mycpp/small_str_test.cc',
  ]:
    ru.cc_binary(
        test_main,
        deps = ['//mycpp/runtime'],
        matrix = COMPILERS_VARIANTS,
        phony_prefix = 'mycpp-unit')

  for test_main in [
      'mycpp/demo/gc_header.cc',
      'mycpp/demo/hash_table.cc',
      'mycpp/demo/target_lang.cc',
      ]:
    ru.cc_binary(
        test_main,
        deps = ['//mycpp/runtime'],
        matrix = COMPILERS_VARIANTS,
        phony_prefix = 'mycpp-unit')

  # ASDL schema that examples/parse.py depends on
  ru.asdl_library(
      'mycpp/examples/expr.asdl')


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

  return to_test


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

def TranslatorSubgraph(ru, translator, ex):
  n = ru.n

  raw = '_gen/mycpp/examples/%s_raw.%s.cc' % (ex, translator)

  # Translate to C++
  if ex in TRANSLATE_FILES:
    to_translate = TRANSLATE_FILES[ex]
  else:
    to_translate = ['mycpp/examples/%s.py' % ex]

  # Implicit dependency: if the translator changes, regenerate source code.
  # But don't pass it on the command line.
  translator_wrapper = '_bin/shwrap/%s_main' % translator

  n.build(raw, 'translate-%s' % translator, to_translate,
          implicit=[translator_wrapper],
          variables=[('mypypath', '$NINJA_REPO_ROOT/mycpp')])

  p = 'mycpp/examples/%s_preamble.h' % ex
  # Ninja empty string!
  preamble_path = p if os.path.exists(p) else "''"

  main_cc_src = '_gen/mycpp/examples/%s.%s.cc' % (ex, translator)

  # Make a translation unit
  n.build(main_cc_src, 'wrap-cc', raw,
          implicit=[RULES_PY],
          variables=[
            ('name', ex),
            ('preamble_path', preamble_path),
            ('translator', translator)])

  n.newline()

  if translator == 'pea':
    ru.phony['pea-translate'].append(main_cc_src)

  if translator == 'mycpp':
    example_matrix = COMPILERS_VARIANTS
  else:
    # pea just has one variant for now
    example_matrix = [
        ('cxx', 'asan+gcalways')
    ]

  if translator == 'mycpp':
    phony_prefix = 'mycpp-examples'
  else:
    phony_prefix = ''

  deps = ['//mycpp/runtime'] 
  if ex == 'parse':
    deps = deps + ['//mycpp/examples/expr.asdl']

  ru.cc_binary(
      main_cc_src,
      deps = deps,
      matrix = example_matrix,
      phony_prefix = phony_prefix,
  )

  # TODO:
  # - restore lost 'pea-compile' tag?


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

  n.rule('translate-pea',
         command='_bin/shwrap/pea_main $mypypath $out $in',
         description='pea $mypypath $out $in')
  n.newline()

  n.rule('wrap-cc',
         command='build/ninja-rules-py.sh wrap-cc $out $translator $name $in $preamble_path',
         description='wrap-cc $out $translator $name $in $preamble_path $out')
  n.newline()
  n.rule('example-task',
         # note: $out can be MULTIPLE FILES, shell-quoted
         command='build/ninja-rules-py.sh example-task $name $impl $bin $out',
         description='example-task $name $impl $bin $out')
  n.newline()
  n.rule('typecheck',
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
  with open('mycpp/examples/parse.translate.txt') as f:
    for line in f:
      path = line.strip()
      TRANSLATE_FILES['parse'].append(path)

  examples = ExamplesToBuild()
  #examples = ['cgi', 'containers', 'fib_iter']

  # Groups of targets.  Not all of these are run by default.
  ph = {
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
  ru.AddPhony(ph)

  DefineTargets(ru)

  #
  # Build and run examples/
  #

  to_compare = []
  benchmark_tasks = []

  for ex in examples:
    ru.comment('- mycpp/examples/%s' % ex)

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
    ru.phony['mycpp-typecheck'].append(t)

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

      # TODO: This should be a Python stub!
      log_out = '%s.log' % prefix
      n.build([task_out, log_out], 'example-task',
              EXAMPLES_PY.get(ex, []) + ['mycpp/examples/%s.py' % ex],
              variables=[
                  ('bin', main_py),
                  ('name', ex), ('impl', 'Python')])

      n.newline()

    for translator in ['mycpp', 'pea']:
      TranslatorSubgraph(ru, translator, ex)

      # Don't run it for now; just compile
      if translator == 'pea':
        continue

      # minimal
      MATRIX = [
          ('test', 'asan'),  # TODO: asan+gcalways is better!
          ('benchmark', 'opt'),
      ]

      # Run the binary in two ways
      for mode, variant in MATRIX:
        task_out = '_test/tasks/%s/%s.%s.%s.task.txt' % (mode, ex, translator, variant)

        if mode == 'benchmark':
          if ShouldSkipBenchmark(ex):
            #log('Skipping benchmark of %s', ex)
            continue
          benchmark_tasks.append(task_out)

        elif mode == 'test':
          if ShouldSkipTest(ex):
            #log('Skipping test of %s', ex)
            continue

        cc_log_out = '_test/tasks/%s/%s.%s.%s.log' % (mode, ex, translator, variant)
        py_log_out = '_test/tasks/%s/%s.py.log' % (mode, ex)

        to_compare.append(cc_log_out)
        to_compare.append(py_log_out)

        # Only test cxx- variant
        b_example = '_bin/cxx-%s/mycpp/examples/%s.%s' % (variant, ex, translator)
        n.build([task_out, cc_log_out], 'example-task', [b_example],
                variables=[
                  ('bin', b_example),
                  ('name', ex), ('impl', 'C++')])
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

