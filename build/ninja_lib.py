#!/usr/bin/env python2
"""
ninja_lib.py
"""
from __future__ import print_function

import os


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)

# - Used as-is by mycpp/examples
# - mycpp unit tests can be restricted by 'test_runs_under_variant'.
# - cpp/ adds a few 

COMPILERS_VARIANTS_LEAKY = [
    ('cxx', 'dbg'),
    ('cxx', 'opt'),
    ('cxx', 'asan'),
    ('cxx', 'ubsan'),

    ('cxx', 'mallocleak'),

    #('clang', 'asan'),
    ('clang', 'dbg'),  # compile-quickly
    ('clang', 'opt'),  # for comparisons
    ('clang', 'ubsan'),  # finds different bugs
    ('clang', 'coverage'),
]

COMPILERS_VARIANTS = COMPILERS_VARIANTS_LEAKY + [
    # mainly for unit tests
    ('cxx', 'gcstats'),
    ('cxx', 'gcevery'),
]


def ObjPath(src_path, compiler, variant):
  rel_path, _ = os.path.splitext(src_path)
  return '_build/obj/%s-%s/%s.o' % (compiler, variant, rel_path)


def NinjaVars(compiler, variant):
  compile_vars = [
      ('compiler', compiler),
      ('variant', variant),
      ('more_cxx_flags', "''")
  ]
  link_vars = [
      ('compiler', compiler),
      ('variant', variant),
  ]
  return compile_vars, link_vars


def asdl_cpp(n, asdl_path, pretty_print_methods=True):
  # to create _gen/mycpp/examples/expr.asdl.h
  prefix = '_gen/%s' % asdl_path

  if pretty_print_methods:
    outputs = [prefix + '.cc', prefix + '.h']
    asdl_flags = '' 
  else:
    outputs = [prefix + '.h']
    asdl_flags = '--no-pretty-print-methods'

  debug_mod = '%s_debug.py' % prefix 
  outputs.append(debug_mod)

  # NOTE: Generating syntax_asdl.h does NOT depend on hnode_asdl.h, but
  # COMPILING anything that #includes it does.  That is handled elsewhere.

  n.build(outputs, 'asdl-cpp', asdl_path,
          implicit=['_bin/shwrap/asdl_main'],
          variables=[
            ('action', 'cpp'),
            ('out_prefix', prefix),
            ('asdl_flags', asdl_flags),
            ('debug_mod', debug_mod),
          ])
  n.newline()


# TODO: Move into cc_library()
GC_RUNTIME = [
    'mycpp/gc_mylib.cc',
    'mycpp/cheney_heap.cc',
    'mycpp/marksweep_heap.cc',

    # files we haven't added StackRoots to
    'mycpp/leaky_containers.cc',
    'mycpp/leaky_builtins.cc',
    'mycpp/leaky_mylib.cc',
]


def cc_binary(
    n,
    main_cc,
    asdl_deps=[],  # causes implicit header dep for compile action, and .o for link action
    matrix=[],  # $compiler $variant
    phony={},
    ):

  # Actions:
  #   compile_one main_cc
  #   link with objects, including GC runtime

  # So then asdl_cpp() also has to generated
  #
  #   compile_one of the .cc file, respecting matrix

  for compiler, variant in matrix:
    compile_vars, link_vars = NinjaVars(compiler, variant)

    main_obj = ObjPath(main_cc, compiler, variant)
    n.build(main_obj, 'compile_one', [main_cc], variables=compile_vars)
    n.newline()

    rel_path, _ = os.path.splitext(main_cc)

    b = '_bin/%s-%s/%s' % (compiler, variant, rel_path)

    cc_files = [main_cc] + GC_RUNTIME
    obj_paths = [ObjPath(dep_cc, compiler, variant) for dep_cc in cc_files]

    n.build([b], 'link', obj_paths, variables=link_vars)
    n.newline()

    key = 'mycpp-unit-%s-%s' % (compiler, variant)
    if key not in phony:
      phony[key] = []
    phony[key].append(b)
