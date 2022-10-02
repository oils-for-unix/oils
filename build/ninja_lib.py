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


class Rules(object):
  """High-level wrapper for NinjaWriter

  What should it handle?

  - The (compiler, variant) matrix loop
  - Implicit deps for generated code
  - Phony convenience targets

  Maybe: exporting data to test runner
  """

  def __init__(self, n):
    self.n = n  # direct ninja writer
    self.cc_libs = {}
    self.phony = {}  # list of phony targets

  def cc_library(self, name, srcs, matrix=[]):
    for compiler, variant in matrix:
      compile_vars, _ = NinjaVars(compiler, variant)

      objects = []
      for src in srcs:
        obj = ObjPath(src, compiler, variant)
        objects.append(obj)

        self.n.build(obj, 'compile_one', [src], variables=compile_vars)
        self.n.newline()
      self.cc_libs[(name, compiler, variant)] = objects

  def cc_binary(
      self,
      main_cc,
      deps=[],
      # TODO: Put :mycpp/runtime label here
      # Also could put :asdl/examples/typed_arith, etc.
      asdl_deps=[],  # causes implicit header dep for compile action, and .o for link action

      matrix=[],  # $compiler $variant

      # TODO: tags?
      # if tags = 'mycpp-unit' then add to phony?
      phony={},
      ):

    for compiler, variant in matrix:
      compile_vars, link_vars = NinjaVars(compiler, variant)

      main_obj = ObjPath(main_cc, compiler, variant)
      self.n.build(main_obj, 'compile_one', [main_cc], variables=compile_vars)
      self.n.newline()

      rel_path, _ = os.path.splitext(main_cc)

      b = '_bin/%s-%s/%s' % (compiler, variant, rel_path)

      obj_paths = [main_obj]
      for dep in deps:
        o = self.cc_libs.get((dep, compiler, variant))
        if o is None:
          raise RuntimeError('Invalid cc_library %r' % dep)
        obj_paths.extend(o)

      self.n.build([b], 'link', obj_paths, variables=link_vars)
      self.n.newline()

      key = 'mycpp-unit-%s-%s' % (compiler, variant)
      if key not in phony:
        phony[key] = []
      phony[key].append(b)

  def asdl_cc(self, asdl_path, pretty_print_methods=True):
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

    self.n.build(outputs, 'asdl-cpp', [asdl_path],
            implicit=['_bin/shwrap/asdl_main'],
            variables=[
              ('action', 'cpp'),
              ('out_prefix', prefix),
              ('asdl_flags', asdl_flags),
              ('debug_mod', debug_mod),
            ])
    self.n.newline()
