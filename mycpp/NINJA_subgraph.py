#!/usr/bin/env python2
"""
mycpp/NINJA_subgraph.py

Code Layout:

  mycpp/
    NINJA_subgraph.py  # This file describes dependencies programmatically
    NINJA-steps.sh     # Invoked by Ninja rules

    build.sh           # wrappers invoked by the Toil and devtools/release.sh
    test.sh            # test driver for unit tests and examples

    examples/
      cgi.py
      varargs.py
      varargs_preamble.h

Output Layout:

  _gen/
    mycpp/
      examples/
        cgi.mycpp.cc
        cgi_raw.mycpp.cc
        cgi.pea.cc
        cgi_raw.pea.cc
        expr.asdl.{h,cc}

  _build/
    obj/
      cxx-dbg/
        gc_heap_test.o  # not translated
        gc_builtins.o   
        _gen/
          mycpp/
            examples/
              cgi.mycpp.o
              cgi.mycpp.o.d
              cgi.pea.o
              cgi.pea.o.d
              expr.asdl.o
              expr.asdl.o.d
      cxx-gcevery/
      cxx-opt/
      clang-coverage/

  _bin/
    cxx-dbg/
      mycpp/
        gc_heap_test
        examples/
          cgi.mycpp
          classes.mycpp
          cgi.pea
          classes.pea
    cxx-opt/
      mycpp/
        examples/
          cgi.mycpp.stripped
    cxx-gcevery/
      mycpp/
        gc_heap_test
    clang-coverage/


  _test/
    tasks/        # *.txt and *.task.txt for .wwz
      typecheck/  # optionally run
      test/       # py, gcevery, asan, opt
      benchmark/

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

from build.NINJA_subgraph import asdl_cpp  # could be NINJA_lib?
from build.NINJA_lib import log, ObjPath


# special ones in examples.sh:
# - parse
# - lexer_main -- these use Oil code
# - pgen2_demo -- uses pgen2

def ShouldSkipBuild(name):
  if name.startswith('invalid_'):
    return True

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
    'mycpp/gc_mylib.cc',
    'mycpp/gc_heap.cc',

    # files we haven't added StackRoots to
    'mycpp/leaky_containers.cc',
    'mycpp/leaky_builtins.cc',
    'mycpp/leaky_mylib.cc',
]

VARIANTS_GC = 1            # Run with garbage collector on, cxx-gcevery
VARIANTS_LEAKY = 2

# Unit tests that run with garbage collector on.
UNIT_TESTS = {
    'mycpp/gc_heap_test.cc': VARIANTS_GC,
    'mycpp/gc_stress_test.cc': VARIANTS_GC,
    'mycpp/gc_builtins_test.cc': VARIANTS_GC,
    'mycpp/gc_mylib_test.cc': VARIANTS_GC,

    'mycpp/leaky_builtins_test.cc': VARIANTS_LEAKY,
    'mycpp/leaky_containers_test.cc': VARIANTS_LEAKY,
    'mycpp/leaky_str_test.cc': VARIANTS_LEAKY,
    'mycpp/leaky_mylib_test.cc': VARIANTS_LEAKY,

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

# Unused.  Could use mycpp/examples/parse.typecheck.txt
EXAMPLES_PY = {
    'parse': [],
}

# Linking _bin/cxx-dbg/mycpp-examples/parse depends on expr.asdl.o
EXAMPLES_CC = {
    'parse': ['_gen/mycpp/examples/expr.asdl.cc'],
}

# We need IMPLICIT header dependencies too.
# Compiling _build/obj-mycpp/cxx-asan/parse.o depends brings parse_preamble.h,
# which brings in expr.asdl.h
EXAMPLES_H = {
    'parse': [ '_gen/mycpp/examples/expr.asdl.h',
               '_gen/asdl/hnode.asdl.h',
             ],
}

COMPILERS_VARIANTS = [
    # mainly for unit tests
    ('cxx', 'gcstats'),
    ('cxx', 'gcevery'),

    ('cxx', 'dbg'),
    ('cxx', 'opt'),
    ('cxx', 'asan'),
    ('cxx', 'ubsan'),

    #('clang', 'asan'),
    ('clang', 'dbg'),  # compile-quickly
    ('clang', 'opt'),  # for comparisons
    ('clang', 'ubsan'),  # finds different bugs
    ('clang', 'coverage'),
]

def TranslatorSubgraph(n, translator, ex, phony):
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
          variables=[
            ('name', ex),
            ('preamble_path', preamble_path),
            ('translator', translator)])

  n.newline()

  if translator == 'pea':
    phony['pea-translate'].append(main_cc_src)

  if translator == 'mycpp':
    example_matrix = COMPILERS_VARIANTS
  else:
    # pea just has one variant for now
    example_matrix = [
        ('cxx', 'gcevery')
    ]

  # Compile C++.
  for compiler, variant in example_matrix:
    compile_vars = [
        ('compiler', compiler), ('variant', variant), ('more_cxx_flags', "''")
    ]
    link_vars = [
        ('compiler', compiler), ('variant', variant),
    ]

    main_obj = ObjPath(main_cc_src, compiler, variant)

    n.build(main_obj, 'compile_one', [main_cc_src],
            implicit=EXAMPLES_H.get(ex, []),
            variables=compile_vars)
    n.newline()

    b = '_bin/%s-%s/mycpp/examples/%s.%s' % (compiler, variant, ex, translator)

    src_deps = GC_RUNTIME + EXAMPLES_CC.get(ex, [])
    obj_deps = [ObjPath(src, compiler, variant) for src in src_deps]

    n.build(b, 'link', [main_obj] + obj_deps, variables=link_vars)
    n.newline()

    if translator == 'pea':
      phony['pea-compile'].append(b)

    if translator == 'mycpp':
      key = 'mycpp-examples-%s-%s' % (compiler, variant)
      if key not in phony:
        phony[key] = []
      phony[key].append(b)

    if variant == 'opt':
      stripped = '_bin/%s-%s/mycpp/examples/%s.%s.stripped' % (compiler, variant, ex, translator)
      # no symbols
      n.build([stripped, ''], 'strip', [b],
              variables=[('variant', variant)])
      n.newline()
      phony['mycpp-strip'].append(stripped)




def NinjaGraph(n):

  n.comment('Generated by %s' % __name__)
  n.newline()

  # Running build/NINJA_main.py
  this_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

  n.variable('NINJA_REPO_ROOT', os.path.dirname(this_dir))
  n.newline()

  # TODO: could go in bin/NINJA_subgraph
  n.rule('gen-osh-eval',
         command='mycpp/NINJA-steps.sh gen-osh-eval $out_prefix $in',
         description='gen-osh-eval $out_prefix $in')
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
         command='mycpp/NINJA-steps.sh wrap-cc $out $translator $name $in $preamble_path',
         description='wrap-cc $out $translator $name $in $preamble_path $out')
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
  # osh_eval.  Could go in bin/NINJA_subgraph.py
  #

  with open('_build/NINJA/osh_eval/translate.txt') as f:
    deps = [line.strip() for line in f]

  prefix = '_gen/bin/osh_eval.mycpp'
  n.build([prefix + '.cc'], 'gen-osh-eval', deps,
          implicit=['_bin/shwrap/mycpp_main'],
          variables=[('out_prefix', prefix)])

  #
  # Individual object files
  #

  cc_sources = []

  for srcs in EXAMPLES_CC.values():  # generated code
    cc_sources.extend(srcs)

  cc_sources.extend(UNIT_TESTS.keys())  # test main() with GC on

  cc_sources.extend(GC_RUNTIME)

  cc_sources = sorted(set(cc_sources))  # make unique

  for (compiler, variant) in COMPILERS_VARIANTS:
    compile_vars = [
        ('compiler', compiler),
        ('variant', variant),
        ('more_cxx_flags', "''"),
    ]
    link_vars = [
        ('compiler', compiler),
        ('variant', variant),
    ]

    #
    # Build all objects
    #

    for src_path in cc_sources:
      obj_path = ObjPath(src_path, compiler, variant)

      n.build(obj_path, 'compile_one', [src_path], variables=compile_vars)
      n.newline()

    #
    # Build and run unit tests
    #

    for main_cc in sorted(UNIT_TESTS):
      which_variants = UNIT_TESTS[main_cc]

      cc_files = GC_RUNTIME

      # assume names are unique
      test_name, _ = os.path.splitext(os.path.basename(main_cc))

      b = '_bin/%s-%s/mycpp/%s' % (compiler, variant, test_name)

      # Hack: avoid illegal combinations
      test_runs_under_variant = False
      if which_variants == VARIANTS_GC and variant in (
          'dbg', 'asan', 'ubsan', 'gcevery', 'gcstats', 'coverage'):
        test_runs_under_variant = True

      if which_variants == VARIANTS_LEAKY and variant in (
          'dbg', 'asan', 'ubsan', 'coverage'):
        test_runs_under_variant = True

      if not test_runs_under_variant:
        continue

      compile_vars = [
          ('compiler', compiler),
          ('variant', variant),
          ('more_cxx_flags', "''")
      ]

      obj_paths = [ObjPath(main_cc, compiler, variant)]
      obj_paths.extend(ObjPath(dep_cc, compiler, variant) for dep_cc in cc_files)

      n.build([b], 'link', obj_paths,
              variables=link_vars)
      n.newline()

      key = 'mycpp-unit-%s-%s' % (compiler, variant)
      if key not in phony:
        phony[key] = []
      phony[key].append(b)


  #
  # ASDL schema that examples/parse.py depends on
  #

  asdl_cpp(n, 'mycpp/examples/expr.asdl')

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
      TranslatorSubgraph(n, translator, ex, phony)

      # Don't run it for now; just compile
      if translator == 'pea':
            continue

      # minimal
      MATRIX = [
          ('test', 'asan'),  # TODO: gcevery is better!
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

        cc_log_out = '_test/tasks/%s/%s.%s.%s.log.txt' % (mode, ex, translator, variant)
        py_log_out = '_test/tasks/%s/%s.py.log.txt' % (mode, ex)

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
  out = '_test/mycpp-logs-equal.txt'
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

  pea_all = []
  for name in sorted(phony):
    deps = phony[name]
    if deps:
      n.build([name], 'phony', deps)
      n.newline()

      if name.startswith('pea-'):
        pea_all.append(name)

  # All groups
  n.build(['pea-all'], 'phony', pea_all)

