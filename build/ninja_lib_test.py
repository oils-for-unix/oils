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

    actions = [b.rule for b in n.build_calls]
    # preprocess could be optional?
    self.assertEqual([
        'compile_one', 'preprocess',
        'compile_one', 'preprocess',
        'compile_one', 'preprocess', 'link'],
        actions)

    last = n.build_calls[-1]
    self.assertEqual([
        '_build/obj/cxx-dbg/mycpp/a_test.o',
        '_build/obj/cxx-dbg/mycpp/a.o',
        '_build/obj/cxx-dbg/mycpp/b.o',
        ], last.inputs)

    # It's NOT used in a binary, so not instantiated
    ru.cc_library('//mycpp/z', ['mycpp/z.cc'])
    self.assertEqual(7, len(n.build_calls))

    self.assertEqual(7, n.num_build_targets())

  def testTransitiveDeps(self):
    # TODO: cc_library() with deps
    pass

  def testDiamondDeps(self):
    # TODO: make sure there aren't duplicates
    pass

  def testCircularDeps(self):
    # Should be disallowed I think
    pass

  def testSourcesForBinary(self):
    n, ru = self._Rules()

    ru.cc_library('//mycpp/y', ['mycpp/y.cc', 'mycpp/y2.cc'])
    ru.cc_library('//mycpp/z', ['mycpp/z.cc'])

    # cc_library() is lazy
    self.assertEqual(0, len(n.build_calls))

    ru.cc_binary(
        'mycpp/a_test.cc', deps=['//mycpp/y', '//mycpp/z'], matrix=MATRIX)
    self.assertEqual(19, len(n.build_calls))

    first = n.build_calls[0]
    self.assertEqual(['_build/obj/cxx-dbg/mycpp/a_test.o'], first.outputs)
    self.assertEqual('compile_one', first.rule)
    self.assertEqual(['mycpp/a_test.cc'], first.inputs)

    srcs = ru.SourcesForBinary('mycpp/a_test.cc')
    self.assertEqual(
        ['mycpp/a_test.cc', 'mycpp/y.cc', 'mycpp/y2.cc', 'mycpp/z.cc'],
        srcs)

    log('generated %d targets', n.num_build_targets())

  def test_asdl(self):
    n, ru = self._Rules()
    ru.asdl_cc('mycpp/examples/foo.asdl')

    self.assertEqual(1, len(n.build_calls))

    first = n.build_calls[0]
    self.assertEqual('asdl-cpp', first.rule)

    ru.asdl_cc('mycpp/examples/foo.asdl', pretty_print_methods=False)

  def test_cc_binary_to_asdl(self):
    n, ru = self._Rules()
    pass

  def test_cc_library_to_asdl(self):
    n, ru = self._Rules()
    pass

  def test_asdl_to_asdl(self):
    n, ru = self._Rules()

    ru.asdl_cc('asdl/hnode.asdl', pretty_print_methods=False)
    # There's no cc_library() in this case

    ru.asdl_cc('frontend/syntax.asdl')

    return

    # TODO: It should automatically look it up, generate a cc_binary, etc.
    # Then uses it on examples/parse -> expr.asdl
    ru.cc_binary(
        'foo.cc',
        deps = ['//frontend/syntax.asdl'],
        matrix = MATRIX1)

  def testShWrap(self):
    # TODO: Rename to py_binary or py_tool
    pass


if __name__ == '__main__':
  unittest.main()
