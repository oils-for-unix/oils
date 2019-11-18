#!/usr/bin/env python2
"""
match_test.py: Tests for match.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id, Id_str
from core.util import log
from frontend  import match  # module under test


class MatchTest(unittest.TestCase):

  def testShouldHijack(self):
    self.assertEqual(
        False, match.ShouldHijack('# comment\n[line 2]'))
    self.assertEqual(
        False, match.ShouldHijack('#!/usr/bin/python\n'))
    self.assertEqual(
        False, match.ShouldHijack(''))
    self.assertEqual(
        False, match.ShouldHijack('\n'))

    self.assertEqual(
        True, match.ShouldHijack('#!/usr/bin/env bash\n'))

    self.assertEqual(
        True, match.ShouldHijack('#!/bin/bash\n[line 2]'))
    self.assertEqual(
        True, match.ShouldHijack('#!/bin/bash -e\n[line 2]'))
    self.assertEqual(
        True, match.ShouldHijack('#!/bin/sh\n[line 2]\n'))
    self.assertEqual(
        True, match.ShouldHijack('#!/bin/sh -e\n[line 2]\n'))

    # Unlikely but OK
    self.assertEqual(
        True, match.ShouldHijack('#!/usr/bin/env sh\n'))

  def testBraceRangeLexer(self):
    lex = match.BraceRangeLexer('1..3')
    while True:
      id_, val = lex.Next()
      log('%s %r', Id_str(id_), val)
      if id_ == Id.Eol_Tok:
        break


if __name__ == '__main__':
  unittest.main()
