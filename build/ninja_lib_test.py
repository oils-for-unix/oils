#!/usr/bin/env python2
"""
ninja_lib_test.py: Tests for ninja_lib.py
"""
from __future__ import print_function

import sys
import unittest

from build.ninja_lib import log
from build import ninja_lib  # module under test
from vendor import ninja_syntax

CONFIG = ('cxx', 'dbg', None)

MATRIX1 = [CONFIG]


MATRIX = [
    ('cxx', 'dbg'),
    ('cxx', 'opt'),
]


def CallFor(n, output_name):
  for b in n.build_calls:
    if b.outputs[0] == output_name:
      return b
  else:
    raise RuntimeError('%s not found' % output_name)


class NinjaTest(unittest.TestCase):

  def _Rules(self):
    n = ninja_syntax.Writer(sys.stdout)
    n = ninja_syntax.FakeWriter(n)

    ru = ninja_lib.Rules(n)
    return n, ru

  def test_cc_library_IsLazy(self):
    n, ru = self._Rules()

    ru.cc_library('//mycpp/ab', ['mycpp/a.cc', 'mycpp/b.cc'])
    self.assertEqual(0, len(n.build_calls))

    ru.cc_binary(
        'mycpp/a_test.cc',
        deps = ['//mycpp/ab'],
        matrix = MATRIX1)

    ru.WriteRules()

    actions = [b.rule for b in n.build_calls]
    self.assertEqual([
        'compile_one',
        'compile_one',
        'compile_one',
        'link'],
        actions)

    last = n.build_calls[-1]
    self.assertEqual([
        '_build/obj/cxx-dbg/mycpp/a_test.o',
        '_build/obj/cxx-dbg/mycpp/a.o',
        '_build/obj/cxx-dbg/mycpp/b.o',
        ], last.inputs)

    # It's NOT used in a binary, so not instantiated
    ru.cc_library('//mycpp/z', ['mycpp/z.cc'])
    self.assertEqual(4, len(n.build_calls))

    self.assertEqual(4, n.num_build_targets())

  def testDiamondDeps(self):
    n, ru = self._Rules()

    # e
    # |
    # d 
    # | \
    # b  c
    # | /
    # a 

    ru.cc_library('//mycpp/e', srcs = ['mycpp/e.cc'])  # leaf
    ru.cc_library('//mycpp/d', srcs = ['mycpp/d.cc'], deps = ['//mycpp/e'])  # diamond
    ru.cc_library('//mycpp/b', srcs = ['mycpp/b.cc'], deps = ['//mycpp/d'])
    ru.cc_library('//mycpp/c', srcs = ['mycpp/c.cc'], deps = ['//mycpp/d'])
    ru.cc_binary('mycpp/a.cc', deps = ['//mycpp/b', '//mycpp/c'], matrix = MATRIX1)

    ru.WriteRules()

    actions = [b.rule for b in n.build_calls]
    self.assertEqual([
        'compile_one',  # e
        'compile_one',  # d
        'compile_one',  # c
        'compile_one',  # b
        'compile_one',  # a
        'link'],
        actions)

    b = CallFor(n, '_bin/cxx-dbg/mycpp/a')
    print(b)
    self.assertEqual([
        '_build/obj/cxx-dbg/mycpp/a.o',
        '_build/obj/cxx-dbg/mycpp/b.o',
        '_build/obj/cxx-dbg/mycpp/c.o',
        '_build/obj/cxx-dbg/mycpp/d.o',
        '_build/obj/cxx-dbg/mycpp/e.o',
        ],
        sorted(b.inputs))

  def testCircularDeps(self):
    # Should be disallowed I think
    pass

  def testSourcesForBinary(self):
    n, ru = self._Rules()

    ru.cc_library('//mycpp/y', srcs = ['mycpp/y.cc', 'mycpp/y2.cc'])
    ru.cc_library('//mycpp/z', srcs = ['mycpp/z.cc'], deps = ['//mycpp/y'])

    # cc_library() is lazy
    self.assertEqual(0, len(n.build_calls))

    ru.cc_binary(
        'mycpp/a_test.cc', deps = ['//mycpp/z'], matrix = MATRIX)

    ru.WriteRules()

    self.assertEqual(11, len(n.build_calls))

    srcs = ru.SourcesForBinary('mycpp/a_test.cc')
    self.assertEqual(
        ['mycpp/a_test.cc', 'mycpp/y.cc', 'mycpp/y2.cc', 'mycpp/z.cc'],
        srcs)

    log('generated %d targets', n.num_build_targets())

  def test_asdl(self):
    n, ru = self._Rules()
    ru.asdl_library('mycpp/examples/foo.asdl')

    self.assertEqual(1, len(n.build_calls))

    first = n.build_calls[0]
    self.assertEqual('asdl-cpp', first.rule)

    # ru.asdl_library('mycpp/examples/foo.asdl', pretty_print_methods=False)

  def test_cc_binary_to_asdl(self):
    n, ru = self._Rules()

    ru.asdl_library('asdl/hnode.asdl', pretty_print_methods = False)  # REQUIRED
    ru.asdl_library('display/pretty.asdl')

    ru.asdl_library('mycpp/examples/expr.asdl')

    ru.cc_binary(
        '_gen/mycpp/examples/parse.mycpp.cc',
        deps = ['//mycpp/examples/expr.asdl'],
        matrix = MATRIX1)

    ru.WriteRules()

    actions = [b.rule for b in n.build_calls]
    print(actions)
    self.assertEqual([
        'asdl-cpp',
        'asdl-cpp',
        'asdl-cpp',
        'compile_one',
        'compile_one',
        'compile_one',
        'link'],
        actions)

    compile_parse = CallFor(n, '_build/obj/cxx-dbg/_gen/mycpp/examples/parse.mycpp.o')

    # Important implicit dependencies on generated headers!
    self.assertEqual([
        '_gen/asdl/hnode.asdl.h',
        '_gen/display/pretty.asdl.h',
        '_gen/mycpp/examples/expr.asdl.h',
        ],
        compile_parse.implicit)

    last = n.build_calls[-1]

    self.assertEqual([
        '_build/obj/cxx-dbg/_gen/mycpp/examples/parse.mycpp.o',
        '_build/obj/cxx-dbg/_gen/display/pretty.asdl.o',
        '_build/obj/cxx-dbg/_gen/mycpp/examples/expr.asdl.o',
        ],
        last.inputs)

  def test_asdl_to_asdl(self):
    n, ru = self._Rules()

    ru.asdl_library('asdl/hnode.asdl', pretty_print_methods = False)  # REQUIRED
    ru.asdl_library('display/pretty.asdl')

    ru.asdl_library('asdl/examples/demo_lib.asdl')

    # 'use' in ASDL creates this dependency
    ru.asdl_library(
        'asdl/examples/typed_demo.asdl',
        deps = ['//asdl/examples/demo_lib.asdl'])
    
    actions = [call.rule for call in n.build_calls]
    self.assertEqual(['asdl-cpp', 'asdl-cpp', 'asdl-cpp', 'asdl-cpp'], actions)

    ru.cc_binary(
        'asdl/gen_cpp_test.cc',
        deps = ['//asdl/examples/typed_demo.asdl'],
        matrix = MATRIX1)

    ru.WriteRules()

    actions = [call.rule for call in n.build_calls]
    print(actions)
    self.assertEqual([
        'asdl-cpp', 'asdl-cpp', 'asdl-cpp', 'asdl-cpp',
        'compile_one',
        'compile_one',  # compile demo_lib
        'compile_one',  # compile typed_demo
        'compile_one',  # compile gen_cpp_test
        'link',
        ],
        actions)

    c = CallFor(n, '_build/obj/cxx-dbg/_gen/asdl/examples/typed_demo.asdl.o')
    print(c)

    # typed_demo depends on demo_lib, so compiling typed_demo.asdl.c depends on
    # the header demo_lib.asdl.h
    self.assertEqual(
        [ '_gen/asdl/examples/demo_lib.asdl.h',
          '_gen/asdl/hnode.asdl.h',
          '_gen/display/pretty.asdl.h' ],
        sorted(c.implicit))

    c = CallFor(n, '_build/obj/cxx-dbg/asdl/gen_cpp_test.o')
    print(c)
    print(c.implicit)
    self.assertEqual(
        [ '_gen/asdl/examples/demo_lib.asdl.h',
          '_gen/asdl/examples/typed_demo.asdl.h',
          '_gen/asdl/hnode.asdl.h',
          '_gen/display/pretty.asdl.h',
        ],
        sorted(c.implicit))

  def testShWrap(self):
    # TODO: Rename to py_binary or py_tool
    pass


if __name__ == '__main__':
  unittest.main()
