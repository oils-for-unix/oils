#!/usr/bin/env python2
"""
braces_test.py: Tests for braces.py
"""

import sys
import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import word_part_e, compound_word
from asdl import format as fmt
from core.util import log
from core.test_lib import Tok
from osh import braces  # module under test
from osh import word_parse_test


# Silly wrapper
def _assertReadWord(*args):
  return word_parse_test._assertReadWord(*args)


def _PrettyPrint(n):
  """Prints in color."""
  ast_f = fmt.DetectConsoleOutput(sys.stdout)
  tree = n.PrettyTree()
  fmt.PrintTree(tree, ast_f)


class BracesTest(unittest.TestCase):

  def testRangePartDetect(self):
    CASES = [
        ('', None),
        ('1', None),
        ('1..', None),
        ('1..3', ('1', '3')),
        ('3..-10..-2', ('3', '-10', -2)),
        ('3..-10..-2..', None), # nope!  unexpected trailing tokens

        ('a', None),
        ('a..', None),
        ('a..z', ('a', 'z')),
        ('a..z..', None),
        ('z..a..-1', ('z', 'a', -1)),
    ]
    for s, expected in CASES:
      tok = Tok(Id.Lit_Chars, s)
      part = braces._RangePartDetect(tok)
      if expected is None:
        self.assert_(part is None)
      elif len(expected) == 2:
        s, e = expected
        self.assertEqual(s, part.start)
        self.assertEqual(e, part.end)
        #self.assertEqual(runtime.NO_SPID, part.step)

      elif len(expected) == 3:
        s, e, step = expected
        self.assertEqual(s, part.start)
        self.assertEqual(e, part.end)
        self.assertEqual(step, part.step)

      else:
        raise AssertionError

      log('%r\t%s', s, part)

  def testBraceDetect(self):
    w = _assertReadWord(self, '}')
    tree = braces._BraceDetect(w)
    self.assertEqual(None, tree)

    w = _assertReadWord(self, ',')
    tree = braces._BraceDetect(w)
    self.assertEqual(None, tree)

    w = _assertReadWord(self, 'B-{a,b}-E')
    tree = braces._BraceDetect(w)
    self.assertEqual(3, len(tree.parts))
    _PrettyPrint(tree)
    print('--')

    # Multiple parts for each alternative
    w = _assertReadWord(self, 'B-{a"a",b"b",c"c"}-E')
    tree  = braces._BraceDetect(w)
    self.assertEqual(3, len(tree.parts))
    _PrettyPrint(tree)
    print('--')

    # Multiple expansion
    w = _assertReadWord(self, 'B-{a,b}--{c,d}-E')
    tree = braces._BraceDetect(w)
    self.assertEqual(5, len(tree.parts))
    _PrettyPrint(tree)
    print('--')

    # Nested expansion
    w = _assertReadWord(self, 'B-{a,b,c,={d,e}}-E')
    tree = braces._BraceDetect(w)
    _PrettyPrint(tree)
    self.assertEqual(3, len(tree.parts))  # B- {} -E

    middle_part = tree.parts[1]
    self.assertEqual(word_part_e.BracedTuple, middle_part.tag)
    self.assertEqual(4, len(middle_part.words))  # a b c ={d,e}

    last_alternative = middle_part.words[3]
    self.assertEqual(2, len(last_alternative.parts)) # = {d,e}

    second_part = last_alternative.parts[1]
    self.assertEqual(word_part_e.BracedTuple, second_part.tag)
    self.assertEqual(2, len(second_part.words)) # {d,e}

    # Another nested expansion
    w = _assertReadWord(self, 'B-{a,={b,c}=,d}-E')
    tree = braces._BraceDetect(w)
    _PrettyPrint(tree)
    self.assertEqual(3, len(tree.parts))  # B- {} -E

    middle_part = tree.parts[1]
    self.assertEqual(word_part_e.BracedTuple, middle_part.tag)
    self.assertEqual(3, len(middle_part.words))  # a ={b,c}= d

    first_alternative = middle_part.words[0]
    _PrettyPrint(first_alternative)
    self.assertEqual(1, len(first_alternative.parts))  # a
    #print('!!', first_alternative)

    middle_alternative = middle_part.words[1]
    self.assertEqual(3, len(middle_alternative.parts))  # = {b,c} =

    middle_part2 = middle_alternative.parts[1]
    self.assertEqual(word_part_e.BracedTuple, middle_part2.tag)
    self.assertEqual(2, len(middle_part2.words))  # b c

    # Third alternative is a Compound with zero parts
    w = _assertReadWord(self, '{a,b,}')
    tree = braces._BraceDetect(w)
    _PrettyPrint(tree)
    self.assertEqual(1, len(tree.parts))
    self.assertEqual(3, len(tree.parts[0].words))

  def testBraceExpand(self):
    w = _assertReadWord(self, 'hi')
    results = braces._BraceExpand(w.parts)
    self.assertEqual(1, len(results))
    for parts in results:
      _PrettyPrint(compound_word(parts))
      print('')

    w = _assertReadWord(self, 'B-{a,b}-E')
    tree = braces._BraceDetect(w)
    self.assertEqual(3, len(tree.parts))
    _PrettyPrint(tree)

    results = braces._BraceExpand(tree.parts)
    self.assertEqual(2, len(results))
    for parts in results:
      _PrettyPrint(compound_word(parts))
      print('')

    w = _assertReadWord(self, 'B-{a,={b,c,d}=,e}-E')
    tree = braces._BraceDetect(w)
    self.assertEqual(3, len(tree.parts))
    _PrettyPrint(tree)

    results = braces._BraceExpand(tree.parts)
    self.assertEqual(5, len(results))
    for parts in results:
      _PrettyPrint(compound_word(parts))
      print('')

    w = _assertReadWord(self, 'B-{a,b}-{c,d}-E')
    tree = braces._BraceDetect(w)
    self.assertEqual(5, len(tree.parts))
    _PrettyPrint(tree)

    results = braces._BraceExpand(tree.parts)
    self.assertEqual(4, len(results))
    for parts in results:
      _PrettyPrint(compound_word(parts))
      print('')


if __name__ == '__main__':
  unittest.main()
