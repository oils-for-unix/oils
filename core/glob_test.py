#!/usr/bin/env python
from __future__ import print_function
"""
glob_test.py: Tests for glob.py
"""

import re
import unittest

import libc
from asdl import py_meta
from core import glob_
from osh.meta import glob as g


class GlobEscapeTest(unittest.TestCase):

  def testEscapeUnescape(self):
    esc = glob_.GlobEscape
    unesc = glob_._GlobUnescape

    pairs = [
        (r'\*.py', '*.py'),
        (r'\?.py', '?.py'),
        (r'\[a\-z\]\[\[\:punct\:\]\]', '[a-z][[:punct:]]'),
        (r'\\n', r'\n'),
    ]
    for e, u in pairs:
      self.assertEqual(e, esc(u))
      self.assertEqual(u, unesc(e))

  def testLooksLikeGlob(self):
    # The way to test bash behavior is:
    #   $ shopt -s nullglob; argv [    # not a glob
    #   $ shopt -s nullglob; argv []   # is a glob
    #   $ shopt -s nullglob; argv [][  # is a glob
    CASES = [
        (r'[]', True),
        (r'[][', True),
        (r'][', False),  # no balanced pair
        (r'\[]', False),  # no balanced pair
        (r'[', False),  # no balanced pair
        (r']', False),  # no balanced pair
        (r'echo', False),
        (r'status=0', False),

        (r'*', True),
        (r'\*', False),
        (r'\*.sh', False),

        ('\\', False),
        ('*\\', True),

        ('?', True),
    ]
    for pat, expected in CASES:
      self.assertEqual(expected, glob_.LooksLikeGlob(pat),
                       '%s: expected %r' % (pat, expected))

  def testGlobStripRegexes(self):
    s = 'aabbccdd'

    # ${v%c*}  # shortest suffix
    m = re.match('^(.*)c.*$', s)
    self.assertEqual('aabbc', m.group(1))

    # ${v%%c*}  # longest suffix
    m = re.match('^(.*?)c.*$', s)
    self.assertEqual('aabb', m.group(1))

    # ${v#*b}  # shortest prefix
    m = re.match('^.*?b(.*)$', s)
    self.assertEqual('bccdd', m.group(1))

    # ${v##*b}  # longest prefix
    m = re.match('^.*b(.*)$', s)
    self.assertEqual('ccdd', m.group(1))

  def testPatSubRegexes(self):
    # x=~/git/oil
    # ${x//git*/X/}

    # git*
    r1 = re.compile('git.*')
    result = r1.sub('X', '~/git/oil')
    self.assertEqual('~/X', result)

    r2 = re.compile('[a-z]')
    result = r2.sub('X', 'a-b-c')
    self.assertEqual('X-X-X', result)

    # Substitute the first one only
    r2 = re.compile('[a-z]')
    result = r2.sub('X', 'a-b-c', count=1)
    self.assertEqual('X-b-c', result)

  def testGlobToExtendedRegex(self):
    CASES = [
        # glob input, (regex, err)
        ('*.py', '.*\.py', None),
        ('*.?', '.*\..', None),
        ('<*>', '<.*>', None),

        #('\\*', '\\*', None),  # not a glob, a string
        # Hard case: a literal * and then a glob
        #('\\**', '\\**', None),
        #('c:\\foo', 'c:\\\\foo', None),

        ('abc', None, None),  # not a glob

        # TODO: These should be parsed
        ('[[:space:]]', None, True),
        ('[abc]', None, True),
        ('[abc\[]', None, True),
    ]
    for glob, expected_regex, expected_err in CASES:
      regex, err = glob_.GlobToExtendedRegex(glob)
      self.assertEqual(expected_regex, regex,
          '%s: expected %r, got %r' % (glob, expected_regex, regex))
      self.assertEqual(expected_err, err,
          '%s: expected %r, got %r' % (glob, expected_err, err))

  def assertASTEqual(self, expected_ast, ast):
    """Asserts that 2 ASDL-defined ASTs are equal."""
    expected_is_node = isinstance(expected_ast, py_meta.CompoundObj)
    given_is_node = isinstance(ast, py_meta.CompoundObj)
    if not expected_is_node and not given_is_node:
      self.assertEqual(expected_ast, ast)
      return

    self.assertEqual(expected_ast.tag, ast.tag)
    if not hasattr(expected_ast, '__slots__'):
      return

    self.assertEqual(expected_ast.__slots__, ast.__slots__)
    for attr in expected_ast.__slots__:
      exp_slot, slot = getattr(expected_ast, attr), getattr(ast, attr)
      if isinstance(slot, list):
        for exp_elem, elem in zip(exp_slot, slot):
          self.assertASTEqual(exp_elem, elem)
      else:
        self.assertASTEqual(exp_slot, slot)

  def testGlobToAST(self):
    CASES = [
        # (glob input, expected ast, has error)
        ('*.py', [g.Star()] + [g.Literal(c) for c in '.py'], False),
        ('*.?', [g.Star(), g.Literal('.'), g.QMark()], False),
        ('<*>', [g.Literal('<'), g.Star(), g.Literal('>')], False),

        # not globs
        ('abc', None, False),
        ('\\*', None, False),
        ('c:\\foo', None, False),

        # character class globs
        ('[[:space:]]', [g.CharClassExpr(False, '[:space:]')], False),
        ('[abc]', [g.CharClassExpr(False, 'abc')], False),
        ('[abc\[]', [g.CharClassExpr(False, 'abc[')], False),
        ('[!not]', [g.CharClassExpr(True, 'not')], False),
        ('[!*?!\]\[]', [g.CharClassExpr(True, '*?!][')], False),

        # a literal * and then a glob
        ('\\**', [g.EscapedChar('*'), g.Star()], False),

        # invalid globs
        ('bad_close]', None, True),
        ('too_nested[[[]]]', None, True),
        ('not_closed[a-z', None, True),
    ]
    for glob, expected_parts, expected_err in CASES:
      if expected_parts:
        expected_ast = g.glob(expected_parts)
      else:
        expected_ast = None

      ast, err = glob_.GlobParser().Parse(glob)
      self.assertASTEqual(expected_ast, ast)
      self.assertEqual(expected_err, err is not None,
          '%s: expected %r, got %r' % (glob, expected_err, err))

  def disabled_testPatSubRegexesLibc(self):
    r = libc.regex_parse('^(.*)git.*(.*)')
    print(r)

    # It matches.  But we need to get the positions out!
    print(libc.regex_match('^(.*)git.*(.*)', '~/git/oil'))

    # Or should we make a match in a loop?
    # We have to keep advancing the string until there are no more matches.


if __name__ == '__main__':
  unittest.main()
