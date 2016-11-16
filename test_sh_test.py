#!/usr/bin/python -S
"""
test_sh_test.py: Tests for test_sh.py
"""

import cStringIO
import pprint
import unittest

from test_sh import *  # module under test

TEST = cStringIO.StringIO("""\
### Env binding in readonly/declare disallowed
FOO=foo readonly v=$(tests/printenv.py FOO)
echo "v=$v"
# Shells allow this misleading construct, but the correct behavior is to
# disallow it at parse time.
# OK bash/dash/mksh stdout: v=None
# OK bash/dash/mksh status: 0
# status: 2
""")

TOKENS = list(LineIter(TEST))
CASE = ParseTestCase(Tokenizer(iter(TOKENS)))


class TestShTest(unittest.TestCase):

  def testLineIter(self):
    pprint.pprint(TOKENS)

    types = [type_ for line_num, type_, value in TOKENS]
    self.assertEqual(
        [ TEST_CASE_BEGIN, CODE, CODE, 
          KEY_VALUE, KEY_VALUE, KEY_VALUE,
          EOF], types)

    pprint.pprint(CASE)
    expected = {'status': '0', 'stdout': 'v=None\n', 'qualifier': 'OK'}
    self.assertEqual(expected, CASE['bash'])
    self.assertEqual(expected, CASE['dash'])
    self.assertEqual(expected, CASE['mksh'])

  def testCreateAssertions(self):
    print CreateAssertions(CASE, 'bash')

  def testRunCases(self):
    shells = [('bash', '/bin/bash'), ('osh', 'bin/osh')]
    RunCases([CASE], shells, lambda i, case: True, True)


if __name__ == '__main__':
  unittest.main()
