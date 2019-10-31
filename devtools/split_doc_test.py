#!/usr/bin/env python2
"""
split_doc_test.py: Tests for split_doc.py
"""
from __future__ import print_function

import unittest
from cStringIO import StringIO

import split_doc  # module under test


class FooTest(unittest.TestCase):

  def testStrict(self):
    entry_f = StringIO('''\
Title
=====

hello

''')

    meta_f = StringIO()
    content_f = StringIO()

    self.assertRaises(RuntimeError,
        split_doc.SplitDocument, {}, entry_f, meta_f, content_f, strict=True)

    print(meta_f.getvalue())
    print(content_f.getvalue())

  def testMetadataAndTitle(self):
    print('_' * 40)
    print()

    entry_f = StringIO('''\
---
foo: bar
---

Title
=====

hello

''')

    meta_f = StringIO()
    content_f = StringIO()

    split_doc.SplitDocument({'default': 'd'}, entry_f, meta_f, content_f)

    print(meta_f.getvalue())
    print(content_f.getvalue())

  def testMetadataAndTitleNoSpace(self):
    print('_' * 40)
    print()

    entry_f = StringIO('''\
---
foo: bar
---
No Space Before Title
=====================

hello

''')

    meta_f = StringIO()
    content_f = StringIO()

    split_doc.SplitDocument({'default': 'd'}, entry_f, meta_f, content_f)

    print(meta_f.getvalue())
    print(content_f.getvalue())

  def testTitleOnly(self):
    print('_' * 40)
    print()

    entry_f = StringIO('''\
No Space Before Title
=====================

hello

''')

    meta_f = StringIO()
    content_f = StringIO()

    split_doc.SplitDocument({'default': 'd'}, entry_f, meta_f, content_f)

    print(meta_f.getvalue())
    print(content_f.getvalue())


if __name__ == '__main__':
  unittest.main()
