#!/usr/bin/env python2
"""target_lang_test.py: test out MyPy-compatible code we generated

Similar to mycpp/demo/target_lang.cc
"""

import collections
import unittest

from typing import List


class TargetLangTest(unittest.TestCase):

    def testFoo(self):
        # type: () -> None

        print(dir(collections))

        pass


if __name__ == '__main__':
    unittest.main()
