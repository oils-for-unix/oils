#!/usr/bin/env python
"""
glob_test.py: Tests for glob.py
"""

import re
import unittest

import libc
from core import glob_


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

    # NOTE: This should be regcomp
    r = re.compile('(^.*)git.*(.*)')

    result = r.sub(r'\1' + 'X' + r'\2', '~/git/oil')
    self.assertEqual('~/X', result)

  def testPatSubRegexesLibc(self):
    r = libc.regex_parse('^(.*)git.*(.*)')
    print(r)

    # It matches.  But we need to get the positions out!
    print libc.regex_match('^(.*)git.*(.*)', '~/git/oil')

    # Or should we make a match in a loop?
    # We have to keep advancing the string until there are no more matches.





if __name__ == '__main__':
  unittest.main()
