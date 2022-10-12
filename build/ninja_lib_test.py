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


MATRIX = [
    ('cxx', 'dbg'),
    ('cxx', 'opt'),
]

class NinjaTest(unittest.TestCase):

  def testSourcesForBinary(self):
    n = ninja_syntax.Writer(sys.stdout)
    n = ninja_syntax.FakeWriter(n)

    ru = ninja_lib.Rules(n)

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

  def testBuild(self):
    n = ninja_syntax.Writer(sys.stdout)
    ru = ninja_lib.Rules(n)

    config = ('cxx', 'dbg', None)
    ru.compile('foo.o', 'foo.cc', [], config)

    matrix = MATRIX
    ru.cc_library('//mycpp/ab', ['mycpp/a.cc', 'mycpp/b.cc'])
    ru.cc_library('//mycpp/z', ['mycpp/z.cc'])

    ru.cc_binary('mycpp/a_test.cc', matrix=matrix)

    ru.asdl_cc('mycpp/examples/foo.asdl')

    # TODO:
    # - Make cc_library lazy
    # - Make ASDL lazily produce a 'compile' action, in addition to the 'asdl-cpp'
    # - Both are with respect to a configuration

    # Should we also have WritePhony() and so forth?

  def testShWrap(self):
    # TODO: add py_binary and so forth
    pass

  def testAdvanced(self):
    # TODO:
    # - Transitive deps with cc_library()
    # - Diamond dependencies
    # - Circular dependencies
    pass


if __name__ == '__main__':
  unittest.main()
