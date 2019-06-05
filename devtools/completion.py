#!/usr/bin/env python2
from __future__ import print_function
"""
completion.py
"""

__author__ = 'Andy Chu'


import re
import sys


class Error(Exception):
  pass


# e.g. class FooTest(
CLASS_RE = re.compile(r'\s*class (.*)\(')
# e.g. def testFoo(self
METHOD_RE = re.compile(r'\s*def (test.*)\(self')

def ParsePythonTest(f):
  current_test = None
  for line in f:
    match = CLASS_RE.match(line)
    if match:
      current_test = match.group(1)
      continue

    match = METHOD_RE.match(line)
    if match and current_test is not None:
      print('%s.%s' % (current_test, match.group(1)))

# e.g. foo() {
FUNC_RE = re.compile(r'^\s* (\S+) \(\) \s* \{', re.VERBOSE)

def MaybeParseBashActions(f):
  actions = []
  dispatch = False
  for line in f:
    match = FUNC_RE.match(line)
    if match:
      actions.append(match.group(1))
    # some line starts with "$@"
    line = line.lstrip()
    # unfortunately have to hard-code my test framework.  I know it accepts
    # function names.  Most other bash scripts don't.
    if line.startswith('"$@"') or line.startswith('taste-main "$@"'):
      dispatch = True

  if dispatch:
    for action in actions:
      print(action)


def main(argv):
  """Returns an exit code."""
  try:
    action = argv[1]
  except IndexError:
    raise Error('Action required')

  try:
    filename = argv[2]
  except IndexError:
    raise Error('Filename required')

  try:
    f = open(filename)
  except IOError:
    return 1

  if action == 'pyunit':
    ParsePythonTest(f)
  elif action == 'bash':
    MaybeParseBashActions(f)
  f.close()
  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except Error, e:
    print(e.args[0], file=sys.stderr)
    sys.exit(1)
