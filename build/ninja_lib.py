#!/usr/bin/env python2
"""
ninja_lib.py

Runtime options:

  CXXFLAGS     Additional flags to pass to the C++ compiler

Notes on ninja_syntax.py:

- escape_path() seems wrong?
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


# Matrix of configurations
# - Used as-is by mycpp/examples
# - mycpp unit tests can be restricted by 'test_runs_under_variant'.
# - cpp/ adds uftrace, etc.

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
    ('cxx', 'gcverbose'),
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


class CcLibrary(object):
  """
  Life cycle:
  
  1. A cc_library is first created
  2. A cc_binary can depend on it
     - maybe writing rules, and ensuring uniques per configuration
  3. The link step needs the list of objects
  4. The tarball needs the list of sources for binary
  """

  def __init__(self, label, srcs, implicit, deps):
    self.label = label
    self.srcs = srcs  # queried by SourcesForBinary
    self.implicit = implicit
    self.deps = deps

    self.obj_lookup = {}  # config -> list of objects

  def MaybeWrite(self, ru, config):
    if config in self.obj_lookup:  # already written by some other cc_binary()
      return

    compiler, variant = config

    objects = []
    for src in self.srcs:
      obj = ObjPath(src, compiler, variant)
      objects.append(obj)

      ru.compile(obj, src, self.deps, config, implicit=self.implicit)

    self.obj_lookup[config] = objects


class Rules(object):
  """High-level wrapper for NinjaWriter

  What should it handle?

  - The (compiler, variant) matrix loop
  - Implicit deps for generated code
  - Phony convenience targets

  Maybe: exporting data to test runner

  Terminology:

  Ninja has
  - rules, which are like Bazel "actions"
  - build targets

  Our library has:
  - Build config: (compiler, variant), and more later

  - Labels: identifiers starting with //, which are higher level than Ninja
    "targets"
    cc_library:
      //mycpp/runtime

      //mycpp/examples/expr.asdl
      //frontend/syntax.asdl

  - Deps are lists of labels, and have a transitive closure

  - H Rules / High level rules?  B rules / Boil?
    cc_binary, cc_library, asdl, etc.
  """
  def __init__(self, n):
    self.n = n  # direct ninja writer

    #self.generated_headers = {}  # ASDL filename -> header name
    #self.asdl = {}  # label -> True if ru.compile(config) has been called?

    self.cc_libs = {}  # label -> CcLibrary object
    self.cc_binary_deps = {}  # main_cc -> list of LABELS
    self.phony = {}  # list of phony targets

  def AddPhony(self, phony_to_add):
    self.phony.update(phony_to_add)

  def WritePhony(self):
    for name in sorted(self.phony):
      targets = self.phony[name]
      if targets:
        self.n.build([name], 'phony', targets)
        self.n.newline()

  def compile(self, out_obj, in_cc, deps, config, implicit=None):
    # deps: //mycpp/examples/expr.asdl -> then look up the headers it exports?

    # TODO: implicit deps for ASDL
    implicit = implicit or []

    compiler, variant = config

    v = [('compiler', compiler), ('variant', variant), ('more_cxx_flags', "''")]
    self.n.build([out_obj], 'compile_one', [in_cc], implicit=implicit, variables=v)
    self.n.newline()

    if variant in ('dbg', 'opt'):
      pre = '_build/preprocessed/%s-%s/%s' % (compiler, variant, in_cc)
      self.n.build(pre, 'preprocess', [in_cc], implicit=implicit, variables=v)
      self.n.newline()

  def link(self, out_bin, main_obj, deps, config):
    compiler, variant = config

    assert isinstance(out_bin, str), out_bin
    assert isinstance(main_obj, str), main_obj
    objects = [main_obj]
    for label in deps:

      # TODO: for ASDL label, call n.compile() on demand?  
      # So you can just have an asdl() rule, and no binary ever depends on it,
      # then you don't get those rules.

      key = (label, compiler, variant)
      try:
        cc_lib = self.cc_libs[label]
      except KeyError:
        raise RuntimeError("Couldn't resolve label %r" % label)

      o = cc_lib.obj_lookup[config]
      objects.extend(o)

    v = [('compiler', compiler), ('variant', variant)]
    self.n.build([out_bin], 'link', objects, variables=v)
    self.n.newline()

    # Strip any .opt binariies
    if variant == 'opt':
      stripped = out_bin + '.stripped'
      symbols = out_bin + '.symbols'
      self.n.build([stripped, symbols], 'strip', [out_bin])
      self.n.newline()

  def _GeneratedHeader(self, label):
    # for implicit deps of 'compile'
    #
    # //mycpp/examples/expr.asdl -> _gen/mycpp/examples/expr.asdl.h
    # And then parse.mycpp.cc needs this implicit dep
    pass

  def _TranslationUnit(self, label, path, implicit=None):
    implicit = implicit or []

    # TODO:
    # - cc_library() and asdl() should call this
    # - append to a data structure
    # - and then when cc_binary() is called, it goes through its transitive
    #   closure of labels, and gets translation units
    # - and then for each config (compiler, variant), it calls n.compile() on the translation unit
    #   - n.compile() can have implicit deps due to ASDL headers
    #   - TODO: this part probably needs unit tests
    pass

  def cc_library(self, label, srcs, implicit=None, deps=None):
    implicit = implicit or []
    deps = deps or []

    if label in self.cc_libs:
      raise RuntimeError('%s was already defined' % label)

    self.cc_libs[label] = CcLibrary(label, srcs, implicit, deps)

  def cc_binary(self, main_cc,
      top_level=False,
      implicit=None,  # for COMPILE action, not link action
      deps=None, matrix=None,  # $compiler $variant
      phony_prefix=None,
      ):
    implicit = implicit or []
    deps = deps or []
    if not matrix:
      raise RuntimeError("Config matrix required")

    self.cc_binary_deps[main_cc] = deps
    for config in matrix:
      compiler, variant = config

      # Compile main object, maybe with IMPLICIT headers deps
      main_obj = ObjPath(main_cc, compiler, variant)
      self.compile(main_obj, main_cc, deps, config, implicit=implicit)

      for label in deps:
        cc_lib = self.cc_libs[label]
        cc_lib.MaybeWrite(self, config)

      if top_level:
        # e.g. _bin/cxx-dbg/osh_eval
        basename = os.path.basename(main_cc)
        first_name = basename.split('.')[0]
        bin_= '_bin/%s-%s/%s' % (compiler, variant, first_name)
      else:
        # e.g. _gen/mycpp/examples/classes.mycpp
        rel_path, _ = os.path.splitext(main_cc)

        # Put binary in _bin/cxx-dbg/mycpp/examples, not _bin/cxx-dbg/_gen/mycpp/examples
        if rel_path.startswith('_gen/'):
          rel_path = rel_path[len('_gen/'):]

        bin_= '_bin/%s-%s/%s' % (compiler, variant, rel_path)

      # Link with OBJECT deps
      self.link(bin_, main_obj, deps, config)

      if phony_prefix:
        key = '%s-%s-%s' % (phony_prefix, compiler, variant)
        if key not in self.phony:
          self.phony[key] = []
        self.phony[key].append(bin_)

  def SourcesForBinary(self, main_cc):
    """
    Used for getting sources of _gen/bin/osh_eval.mycpp.cc, etc.
    """
    deps = self.cc_binary_deps[main_cc]
    sources = [main_cc]
    for label in deps:
      sources.extend(self.cc_libs[label].srcs)
    return sources

  def asdl_cc(self, asdl_path, pretty_print_methods=True):
    # to create _gen/mycpp/examples/expr.asdl.h
    prefix = '_gen/%s' % asdl_path
    out_header = prefix + '.h'
    if pretty_print_methods:
      outputs = [prefix + '.cc', out_header]
      asdl_flags = '' 
    else:
      outputs = [out_header]
      asdl_flags = '--no-pretty-print-methods'

    #self.generated_headers[asdl_path] = out_header

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
