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

import collections
import os
import sys


def log(msg, *args):
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)


# Matrix of configurations

COMPILERS_VARIANTS = [
    ('cxx', 'dbg'),
    ('cxx', 'opt'),
    ('cxx', 'asan'),
    ('cxx', 'asan+gcalways'),
    ('cxx', 'asan32+gcalways'),
    ('cxx', 'ubsan'),

    #('clang', 'asan'),
    ('clang', 'dbg'),  # compile-quickly
    ('clang', 'opt'),  # for comparisons
    ('clang', 'ubsan'),  # finds different bugs
    ('clang', 'coverage'),
]

GC_PERF_VARIANTS = [
    ('cxx', 'opt+bumpleak'),
    ('cxx', 'opt+bumproot'),
    ('cxx', 'opt+bumpsmall'),
    ('cxx', 'asan+bumpsmall'),
    ('cxx', 'opt+nopool'),

    # TODO: should be binary with different files
    ('cxx', 'opt+tcmalloc'),

    # For tracing allocations, or debugging
    ('cxx', 'uftrace'),

    # Test performance of 32-bit build.  (It uses less memory usage, but can be
    # slower.)
    ('cxx', 'opt32'),
]

OTHER_VARIANTS = [
    ('cxx', 'opt+bigint'),
    ('cxx', 'opt+souffle'),
    ('cxx', 'asan+bigint'),
]

SMALL_TEST_MATRIX = [
    ('cxx', 'asan'),
    ('cxx', 'ubsan'),
    ('clang', 'coverage'),
]


def ConfigDir(config):
    compiler, variant, more_cxx_flags = config
    if more_cxx_flags is None:
        return '%s-%s' % (compiler, variant)
    else:
        # -D CPP_UNIT_TEST -> D_CPP_UNIT_TEST
        flags_str = more_cxx_flags.replace('-', '').replace(' ', '_')
        return '%s-%s-%s' % (compiler, variant, flags_str)


def ObjPath(src_path, config):
    rel_path, _ = os.path.splitext(src_path)
    return '_build/obj/%s/%s.o' % (ConfigDir(config), rel_path)


# Used namedtuple since it doesn't have any state
CcBinary = collections.namedtuple(
    'CcBinary',
    'main_cc symlinks implicit deps matrix phony_prefix preprocessed bin_path')


class CcLibrary(object):
    """
    Life cycle:
    
    1. A cc_library is first created
    2. A cc_binary can depend on it
       - maybe writing rules, and ensuring uniques per configuration
    3. The link step needs the list of objects
    4. The tarball needs the list of sources for binary
    """

    def __init__(self, label, srcs, implicit, deps, headers,
                 generated_headers):
        self.label = label
        self.srcs = srcs  # queried by SourcesForBinary
        self.implicit = implicit
        self.deps = deps
        self.headers = headers
        # TODO: asdl() rule should add to this.
        # Generated headers are different than regular headers.  The former need an
        # implicit dep in Ninja, while the latter can rely on the .d mechanism.
        self.generated_headers = generated_headers

        self.obj_lookup = {}  # config -> list of objects
        self.preprocessed_lookup = {}  # config -> boolean

    def _CalculateImplicit(self, ru):
        """ Compile actions for cc_library() also need implicit deps on generated headers"""

        out_deps = set()
        ru._TransitiveClosure(self.label, self.deps, out_deps)
        unique_deps = sorted(out_deps)

        implicit = list(self.implicit)  # copy
        for label in unique_deps:
            cc_lib = ru.cc_libs[label]
            implicit.extend(cc_lib.generated_headers)
        return implicit

    def MaybeWrite(self, ru, config, preprocessed):
        if config not in self.obj_lookup:  # already written by some other cc_binary()
            implicit = self._CalculateImplicit(ru)

            objects = []
            for src in self.srcs:
                obj = ObjPath(src, config)
                ru.compile(obj, src, self.deps, config, implicit=implicit)
                objects.append(obj)

            self.obj_lookup[config] = objects

        if preprocessed and config not in self.preprocessed_lookup:
            implicit = self._CalculateImplicit(ru)

            for src in self.srcs:
                # no output needed
                ru.compile('',
                           src,
                           self.deps,
                           config,
                           implicit=implicit,
                           maybe_preprocess=True)
            self.preprocessed_lookup[config] = True


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

        self.cc_bins = []  # list of CcBinary() objects to write
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

    def WriteRules(self):
        for cc_bin in self.cc_bins:
            self.WriteCcBinary(cc_bin)

    def compile(self,
                out_obj,
                in_cc,
                deps,
                config,
                implicit=None,
                maybe_preprocess=False):
        """ .cc -> compiler -> .o """

        implicit = implicit or []

        compiler, variant, more_cxx_flags = config
        if more_cxx_flags is None:
            flags_str = "''"
        else:
            assert "'" not in more_cxx_flags, more_cxx_flags  # can't handle single quotes
            flags_str = "'%s'" % more_cxx_flags

        v = [('compiler', compiler), ('variant', variant),
             ('more_cxx_flags', flags_str)]
        if maybe_preprocess:
            # Limit it to certain configs
            if more_cxx_flags is None and variant in ('dbg', 'opt'):
                pre = '_build/preprocessed/%s-%s/%s' % (compiler, variant,
                                                        in_cc)
                self.n.build(pre,
                             'preprocess', [in_cc],
                             implicit=implicit,
                             variables=v)
        else:
            self.n.build([out_obj],
                         'compile_one', [in_cc],
                         implicit=implicit,
                         variables=v)

        self.n.newline()

    def link(self, out_bin, main_obj, deps, config):
        """ list of .o -> linker -> executable, along with stripped version """
        compiler, variant, _ = config

        assert isinstance(out_bin, str), out_bin
        assert isinstance(main_obj, str), main_obj

        objects = [main_obj]
        for label in deps:
            try:
                cc_lib = self.cc_libs[label]
            except KeyError:
                raise RuntimeError("Couldn't resolve label %r" % label)

            o = cc_lib.obj_lookup[config]
            objects.extend(o)

        v = [('compiler', compiler), ('variant', variant),
             ('more_link_flags', "''")]
        self.n.build([out_bin], 'link', objects, variables=v)
        self.n.newline()

        # Strip any .opt binaries
        if variant.startswith('opt') or variant.startswith('opt32'):
            stripped = out_bin + '.stripped'
            symbols = out_bin + '.symbols'
            self.n.build([stripped, symbols], 'strip', [out_bin])
            self.n.newline()

    def comment(self, s):
        self.n.comment(s)
        self.n.newline()

    def cc_library(
            self,
            label,
            srcs=None,
            implicit=None,
            deps=None,
            # note: headers is only used for tarball manifest, not compiler command line
            headers=None,
            generated_headers=None):

        # srcs = [] is allowed for _gen/asdl/hnode.asdl.h
        if srcs is None:
            raise RuntimeError('cc_library %r requires srcs' % label)

        implicit = implicit or []
        deps = deps or []
        headers = headers or []
        generated_headers = generated_headers or []

        if label in self.cc_libs:
            raise RuntimeError('%s was already defined' % label)

        self.cc_libs[label] = CcLibrary(label, srcs, implicit, deps, headers,
                                        generated_headers)

    def _TransitiveClosure(self, name, deps, unique_out):
        """
        Args:
          name: for error messages
        """
        for label in deps:
            if label in unique_out:
                continue
            unique_out.add(label)

            try:
                cc_lib = self.cc_libs[label]
            except KeyError:
                raise RuntimeError('Undefined label %s in %s' % (label, name))

            self._TransitiveClosure(cc_lib.label, cc_lib.deps, unique_out)

    def cc_binary(
            self,
            main_cc,
            symlinks=None,
            implicit=None,  # for COMPILE action, not link action
            deps=None,
            matrix=None,  # $compiler $variant
            phony_prefix=None,
            preprocessed=False,
            bin_path=None,  # default is _bin/$compiler-$variant/rel/path
    ):
        symlinks = symlinks or []
        implicit = implicit or []
        deps = deps or []
        if not matrix:
            raise RuntimeError("Config matrix required")

        cc_bin = CcBinary(main_cc, symlinks, implicit, deps, matrix,
                          phony_prefix, preprocessed, bin_path)

        self.cc_bins.append(cc_bin)

    def WriteCcBinary(self, cc_bin):
        c = cc_bin

        out_deps = set()
        self._TransitiveClosure(c.main_cc, c.deps, out_deps)
        unique_deps = sorted(out_deps)

        # save for SourcesForBinary()
        self.cc_binary_deps[c.main_cc] = unique_deps

        compile_imp = list(c.implicit)
        for label in unique_deps:
            cc_lib = self.cc_libs[label]  # should exit
            # compile actions of binaries that have ASDL label deps need the
            # generated header as implicit dep
            compile_imp.extend(cc_lib.generated_headers)

        for config in c.matrix:
            if len(config) == 2:
                config = (config[0], config[1], None)

            for label in unique_deps:
                cc_lib = self.cc_libs[label]  # should exit

                cc_lib.MaybeWrite(self, config, c.preprocessed)

            # Compile main object, maybe with IMPLICIT headers deps
            main_obj = ObjPath(c.main_cc, config)
            self.compile(main_obj,
                         c.main_cc,
                         c.deps,
                         config,
                         implicit=compile_imp)
            if c.preprocessed:
                self.compile('',
                             c.main_cc,
                             c.deps,
                             config,
                             implicit=compile_imp,
                             maybe_preprocess=True)

            config_dir = ConfigDir(config)
            bin_dir = '_bin/%s' % config_dir

            if c.bin_path:
                # e.g. _bin/cxx-dbg/oils_for_unix
                bin_ = '%s/%s' % (bin_dir, c.bin_path)
                bin_subdir, _, bin_name = c.bin_path.rpartition('/')
                if bin_subdir:
                    bin_dir = '%s/%s' % (bin_dir, bin_subdir)
                else:
                    bin_name = c.bin_path

            else:
                # e.g. _gen/mycpp/examples/classes.mycpp
                rel_path, _ = os.path.splitext(c.main_cc)

                # Put binary in _bin/cxx-dbg/mycpp/examples, not _bin/cxx-dbg/_gen/mycpp/examples
                if rel_path.startswith('_gen/'):
                    rel_path = rel_path[len('_gen/'):]

                bin_ = '%s/%s' % (bin_dir, rel_path)

            # Link with OBJECT deps
            self.link(bin_, main_obj, unique_deps, config)

            # Make symlinks
            for symlink in c.symlinks:
                # Must explicitly specify bin_path to have a symlink, for now
                assert c.bin_path is not None
                self.n.build(['%s/%s' % (bin_dir, symlink)],
                             'symlink', [bin_],
                             variables=[('dir', bin_dir), ('target', bin_name),
                                        ('new', symlink)])
                self.n.newline()

            if c.phony_prefix:
                key = '%s-%s' % (c.phony_prefix, config_dir)
                if key not in self.phony:
                    self.phony[key] = []
                self.phony[key].append(bin_)

    def SourcesForBinary(self, main_cc):
        """
        Used for preprocessed metrics, release tarball, _build/oils.sh, etc.
        """
        deps = self.cc_binary_deps[main_cc]
        sources = [main_cc]
        for label in deps:
            sources.extend(self.cc_libs[label].srcs)
        return sources

    def HeadersForBinary(self, main_cc):
        deps = self.cc_binary_deps[main_cc]
        headers = []
        for label in deps:
            headers.extend(self.cc_libs[label].headers)
            headers.extend(self.cc_libs[label].generated_headers)
        return headers

    def asdl_library(self,
                     asdl_path,
                     deps=None,
                     pretty_print_methods=True,
                     abbrev_module=None):

        deps = deps or []

        # SYSTEM header, _gen/asdl/hnode.asdl.h
        deps.append('//asdl/hnode.asdl')
        deps.append('//display/pretty.asdl')

        # to create _gen/mycpp/examples/expr.asdl.h
        prefix = '_gen/%s' % asdl_path

        out_cc = prefix + '.cc'
        out_header = prefix + '.h'

        asdl_flags = []

        if pretty_print_methods:
            outputs = [out_cc, out_header]
        else:
            outputs = [out_header]
            asdl_flags.append('--no-pretty-print-methods')

        if abbrev_module:
            asdl_flags.append('--abbrev-module=%s' % abbrev_module)

        debug_mod = prefix + '_debug.py'
        outputs.append(debug_mod)

        # Generating syntax_asdl.h does NOT depend on hnode_asdl.h existing ...
        self.n.build(outputs,
                     'asdl-cpp', [asdl_path],
                     implicit=['_bin/shwrap/asdl_main'],
                     variables=[
                         ('action', 'cpp'),
                         ('out_prefix', prefix),
                         ('asdl_flags', ' '.join(asdl_flags)),
                         ('debug_mod', debug_mod),
                     ])
        self.n.newline()

        # ... But COMPILING anything that #includes it does.
        # Note: assumes there's a build rule for this "system" ASDL schema

        srcs = [out_cc] if pretty_print_methods else []
        # Define lazy CC library
        self.cc_library(
            '//' + asdl_path,
            srcs=srcs,
            deps=deps,
            # For compile_one steps of files that #include this ASDL file
            generated_headers=[out_header],
        )

    def py_binary(self, main_py, deps_base_dir='_build/NINJA', template='py'):
        """Wrapper for Python script with dynamically discovered deps

        Args:
          template: py, mycpp, or pea

        Example:
          _bin/shwrap/mycpp_main wraps mycpp/mycpp_main.py
            - using dependencies from prebuilt/ninja/mycpp.mycpp_main/deps.txt
            - with the 'shwrap-mycpp' template defined in build/ninja-lib.sh
        """
        rel_path, _ = os.path.splitext(main_py)
        # asdl/asdl_main.py -> asdl.asdl_main
        py_module = rel_path.replace('/', '.')

        deps_path = os.path.join(deps_base_dir, py_module, 'deps.txt')
        with open(deps_path) as f:
            deps = [line.strip() for line in f]

        deps.remove(main_py)  # raises ValueError if it's not there

        shwrap_name = os.path.basename(rel_path)
        self.n.build('_bin/shwrap/%s' % shwrap_name,
                     'write-shwrap', [main_py] + deps,
                     variables=[('template', template)])
        self.n.newline()

    def souffle_binary(self, souffle_cpp):
        """
        Compile souffle C++ into a native executable.
        """
        rel_path, _ = os.path.splitext(souffle_cpp)
        basename = os.path.basename(rel_path)

        souffle_obj = '_build/obj/datalog/%s.o' % basename
        self.n.build([souffle_obj],
                     'compile_one',
                     souffle_cpp,
                     variables=[('compiler', 'cxx'), ('variant', 'opt'),
                                ('more_cxx_flags', "'-Ivendor -std=c++17'")])

        souffle_bin = '_bin/datalog/%s' % basename
        self.n.build([souffle_bin],
                     'link',
                     souffle_obj,
                     variables=[('compiler', 'cxx'), ('variant', 'opt'),
                                ('more_link_flags', "'-lstdc++fs'")])

        self.n.newline()


_SHWRAP = {
    'mycpp': '_bin/shwrap/mycpp_main',
    'mycpp-souffle': '_bin/shwrap/mycpp_main_souffle',
}

# TODO: should have dependencies with sh_binary
RULES_PY = 'build/ninja-rules-py.sh'


def mycpp_binary(ru,
                 py_module,
                 preamble=None,
                 translator='mycpp',
                 matrix=None,
                 bin_path=None,
                 symlinks=None,
                 deps=None):
    assert py_module.count('.') == 1, py_module
    # e.g. bin/oils_for_unix
    py_rel_path = py_module.replace('.', '/')

    symlinks = symlinks or []
    deps = deps or []
    matrix = matrix or COMPILERS_VARIANTS
    if preamble is None:
        preamble = py_rel_path + '_preamble.h'

    n = ru.n

    with open('_build/NINJA/%s/translate.txt' % py_module) as f:
        deps1 = [line.strip() for line in f]

    prefix = '_gen/%s.%s' % (py_rel_path, translator)
    shwrap_path = _SHWRAP[translator]

    variables = [
        ('py_module', py_module),
        ('shwrap_path', shwrap_path),
        ('out_prefix', prefix),
        ('preamble', preamble),
    ]

    outputs = [prefix + '.cc', prefix + '.h']
    n.build(outputs,
            'mycpp-gen',
            deps1,
            implicit=[shwrap_path, RULES_PY],
            variables=variables)

    ru.cc_binary('_gen/%s.%s.cc' % (py_rel_path, translator),
                 bin_path=bin_path,
                 symlinks=symlinks,
                 preprocessed=True,
                 matrix=matrix,
                 deps=deps)
