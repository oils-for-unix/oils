#!/usr/bin/env python2
"""
glob_test.py: Tests for glob.py
"""
from __future__ import print_function

import re
import unittest

from frontend import match
from osh import glob_


class GlobEscapeTest(unittest.TestCase):

  def testEscapeUnescape(self):
    esc = glob_.GlobEscape
    unesc = glob_.GlobUnescape

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
        (r'[a]', True),
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


def _ReadTokens(s):
  lex = match.GlobLexer(s)
  return list(lex.Tokens())


class GlobParserTest(unittest.TestCase):

  def testGlobLexer(self):
    print(_ReadTokens(''))
    print(_ReadTokens('*.py'))
    print(_ReadTokens(r'\*.py'))
    print(_ReadTokens('[abc]'))
    print(_ReadTokens('\\'))  # Enf
    print(_ReadTokens('\\x'))
    print(_ReadTokens(r'\\'))
    print(_ReadTokens(r'[[:alpha:]]'))
    print(_ReadTokens(r'[?]'))

  def testGlobParser(self):
    CASES = [
        # (glob input, expected AST, expected extended regexp, has error)
        ('*.py', r'.*\.py', False),
        ('*.?', r'.*\..', False),
        ('<*>', r'<.*>', False),
        ('\**+', r'\*.*\+', False),
        ('\**', r'\*.*', False),
        ('*.[ch]pp', r'.*\.[ch]pp', False),

        # not globs
        ('abc', 'abc', False),
        ('\\*', '\\*', False),
        ('c:\\foo', 'c:foo', False),
        ('strange]one', 'strange\\]one', False),

        # character class globs
        ('[[:space:]abc]', '[[:space:]abc]', False),
        ('[abc]', '[abc]', False),
        (r'[\a\b\c]', r'[\a\b\c]', False),
        ('[abc\[]', r'[abc\[]', False),
        ('[!not]', '[^not]', False),
        ('[^also_not]', '[^also_not]', False),
        ('[!*?!\\[]', '[^*?!\\[]', False),
        ('[!\]foo]', r'[^\]foo]', False),

        # invalid globs
        ('not_closed[a-z', 'not_closed\\[a-z', True),
        ('[[:spa[ce:]]', '\\[\\[:spa\\[ce:\\]\\]', True),

        # Regression test for IndexError.
        ('[', '\\[', True),
        ('\\', '\\\\', True),
        (']', '\\]', False),
    ]
    for glob, expected_ere, expected_err in CASES:
      print('===')
      print(glob)
      regex, warnings = glob_.GlobToERE(glob)
      self.assertEqual(
          expected_ere, regex,
          'Expected %r to translate to %r, got %r' % (glob, expected_ere, regex))

      print('regex   : %s' % regex)
      print('warnings: %s' % warnings)


if __name__ == '__main__':
  unittest.main()
