#!/usr/bin/python
from __future__ import print_function
"""
test_sh.py -- Test framework to compare shells.

TODO: 
  - Test should have a notion with KNOWN disagreement?  Between bash and dash.

Assertion help:
  stdout: A single line of expected stdout.  Newline is implicit.
  stdout-json: JSON-encoded string.  Use for the empty string (no newline),
    for unicode chars, etc.

  stderr: Ditto for stderr stream.
  status: Expected shell return code.  If not specified, the case must exit 0.

Results:
  PASS - we got the ideal, expected value
  OK   - we got a value that was not ideal, but expected
  N-I  - Not implemented (e.g. $'').  Assertions still checked (in case it
         starts working)
  BUG  - we verified the value of a known bug
  FAIL - we got an unexpected value.  If the implementation can't be changed,
         it should be converted to BUG or OK.  Otherwise it should be made to
         PASS.

TODO: maybe have KBUG and BUG?  KBUG is known bug, or intentional
incompatibility.  Like dash interpreting escapes in 'foo\n'.  An unintentional
bug is something else, like bash parsing errors.
IBUG / BUG / N-I are all variants of the same thing.

NOTE: The difference between OK and BUG is a matter of judgement.  If the ideal
behavior is a compile time error (code 2), a runtime error is generally OK.

If ALL shells agree on a broken behavior, they are all marked OK (but our
implementation will be PASS.)  But if the behavior is NOT POSIX compliant, then
it will be a BUG.

If one shell disagrees with others, that is generally a BUG.
"""

import json
import optparse
import os
import pprint
import re
import subprocess
import sys
import time


class ParseError(Exception):
  pass


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# Example:
# stdout: foo
#
# TODO: Also support
# mksh: status: 2
# bash/mksh status: 2
# bash/mksh stdout: hi there
#
# In other words, it could be (name, value) or (qualifier, name, value)

KEY_VALUE_RE = re.compile(r'''
   [#] \s+
   (?: (OK|BUG|N-I) \s+ ([\w+/]+) \s+ )?   # optional prefix
   ([\w\-]+)              # key
   :
   \s* (.*)               # value
''', re.VERBOSE)

# Line types
TEST_CASE_BEGIN = 0  # Starts with ###
KEY_VALUE = 1  # Metadata
CODE = 2  # Unquoted
EOF = 3


def LineIter(f):
  """Iterate over lines, classify them by token type, and parse token value."""
  for i, line in enumerate(f):
    if not line.strip():
      continue

    line_num = i+1  # 1-based

    if line.startswith('###'):
      desc = line[3:].strip()
      yield line_num, TEST_CASE_BEGIN, desc
      continue

    m = KEY_VALUE_RE.match(line)
    if m:
      qualifier, shells, name, value = m.groups()
      # HACK: Expected data should have the newline.
      if name in ('stdout', 'stderr'):
        value += '\n'
      yield line_num, KEY_VALUE, (qualifier, shells, name, value)
      continue

    if line.lstrip().startswith('#'):
      # Ignore comments
      #yield COMMENT, line
      continue

    # Non-empty line that doesn't start with '#'
    # NOTE: We need the original line to test the whitespace sensitive <<-.
    # And we need rstrip because we add newlines back below.
    yield line_num, CODE, line.rstrip()

  yield line_num, EOF, None


class Tokenizer(object):
  """Wrap a token iterator in a Tokenizer interface."""
  def __init__(self, it):
    self.it = it
    self.cursor = None
    self.next()

  def next(self):
    """Raises StopIteration when exhausted."""
    self.cursor = self.it.next()
    return self.cursor

  def peek(self):
    return self.cursor


# Format of a test script.
#
# -- Code is either literal lines, or a commented out code: value.
# code = (? line of code ?)*
#      | '# code:'  VALUE 
#
# -- Description, then key-value pairs surrounding code.
# test_case = '###' DESC
#             ( '#' KEY ':' VALUE )*
#             code
#             ( '#' KEY ':' VALUE )*
# 
# -- Should be a blank line after each test case.  Leading comments and code
# -- are OK.
# test_file = (COMMENT | CODE)* (test_case '\n')*  


def ParseKeyValue(tokens, case):
  """Parse commented-out metadata in a test case."""
  while True:
    _, kind, item = tokens.peek()
    if kind != KEY_VALUE:
      break
    qualifier, shells, name, value = item
    if qualifier:
      shells = shells.split('/')  # bash/dash/mksh
      for shell in shells:
        if shell not in case:
          case[shell] = {}
        case[shell][name] = value
        case[shell]['qualifier'] = qualifier
    else:
      case[name] = value

    tokens.next()


def ParseCodeLines(tokens, case):
  """Parse uncommented code in a test case."""
  _, kind, item = tokens.peek()
  if kind != CODE:
    raise ParseError('Expected a line of code (got %r, %r)' % (kind, item))
  code_lines = []
  while True:
    _, kind, item = tokens.peek()
    if kind != CODE:
      case['code'] = '\n'.join(code_lines) + '\n'
      return
    code_lines.append(item)
    tokens.next()


def ParseTestCase(tokens):
  """Parse a single test case and return it.
  
  If at EOF, return None.
  """
  line_num, kind, item = tokens.peek()
  if kind == EOF:
    return None

  assert kind == TEST_CASE_BEGIN, kind  # Invariant
  tokens.next()

  case = {'desc': item, 'line_num': line_num}
  #print case

  ParseKeyValue(tokens, case)
  #print 'KV1', case
  if 'code' in case:  # Got it through a key value pair
    return case

  ParseCodeLines(tokens, case)
  #print 'AFTER CODE', case
  ParseKeyValue(tokens, case)
  #print 'KV2', case

  return case


def ParseTestFile(tokens):
  #pprint.pprint(list(lines))
  #return
  test_cases = []
  try:
    # Skip over the header.  Setup code can go here, although would we have to
    # execute it on every case?
    while True:
      line_num, kind, item = tokens.peek()
      if kind == TEST_CASE_BEGIN:
        break
      tokens.next()

    while True:  # Loop over cases
      test_case = ParseTestCase(tokens)
      if test_case is None:
        break
      test_cases.append(test_case)

  except StopIteration:
    raise RuntimeError('Unexpected EOF parsing test cases')

  return test_cases


# ANSI color constants
_RESET = '\033[0;0m'
_BOLD = '\033[1m'

_RED = '\033[31m'
_GREEN = '\033[32m'
_YELLOW = '\033[33m'


COLOR_FAIL = ''.join([_RED, _BOLD, 'FAIL', _RESET])
COLOR_BUG = ''.join([_YELLOW, _BOLD, 'BUG', _RESET])
COLOR_NI = ''.join([_YELLOW, _BOLD, 'N-I', _RESET])
COLOR_OK = ''.join([_YELLOW, _BOLD, 'OK', _RESET])
COLOR_PASS = ''.join([_GREEN, _BOLD, 'PASS', _RESET])


def PrintResultRow(row):
  for result in row:
    if result == Result.FAIL:
      c = COLOR_FAIL
    elif result == Result.BUG:
      c = COLOR_BUG
    elif result == Result.NI:
      c = COLOR_NI
    elif result == Result.OK:
      c = COLOR_OK
    elif result == Result.PASS:
      c = COLOR_PASS
    else:
      raise AssertionError
    sys.stdout.write(c)
    sys.stdout.write('\t')


def CreateStringAssertion(d, key, assertions, qualifier=False):
  found = False

  exp = d.get(key)
  if exp is not None:
    a = EqualAssertion(key, exp, qualifier=qualifier)
    assertions.append(a)
    found = True

  exp_json = d.get(key + '-json')
  if exp_json is not None:
    exp = json.loads(exp_json, encoding='utf-8')
    a = EqualAssertion(key, exp, qualifier=qualifier)
    assertions.append(a)
    found = True

  return found


def CreateIntAssertion(d, key, assertions, qualifier=False):
  exp = d.get(key)
  if exp is not None:
    # For now, turn it into int
    a = EqualAssertion(key, int(exp), qualifier=qualifier)
    assertions.append(a)
    return True
  return False


def CreateAssertions(case, shell):
  assertions = []

  # Whether we found assertions
  stdout = False
  stderr = False
  status = False

  if shell in case:
    q = case[shell]['qualifier']
    if CreateStringAssertion(case[shell], 'stdout', assertions, qualifier=q):
      stdout = True
    if CreateStringAssertion(case[shell], 'stderr', assertions, qualifier=q):
      stderr = True
    if CreateIntAssertion(case[shell], 'status', assertions, qualifier=q):
      status = True

  if not stdout:
    CreateStringAssertion(case, 'stdout', assertions)
  if not stderr:
    CreateStringAssertion(case, 'stderr', assertions)
  if not status:
    CreateIntAssertion(case, 'status', assertions)
    
  #print 'SHELL', shell
  #pprint.pprint(case)
  #print assertions
  return assertions


class Result(object):
  """Possible test results.

  Order is important: the result of a cell is the minimum of the results of
  each assertions.
  """
  FAIL = 0
  BUG = 1
  NI = 2
  OK = 3
  PASS = 4


class EqualAssertion(object):
  """An expected value in a record."""
  def __init__(self, key, expected, qualifier=None):
    self.key = key
    self.expected = expected  # expected value
    self.qualifier = qualifier  # whether this was a special case?

  def __repr__(self):
    return '<EqualAssertion %s == %r>' % (self.key, self.expected)

  def Check(self, shell, record):
    actual = record[self.key]
    if actual != self.expected:
      msg = '%s %s: Expected %r, got %r' % (shell, self.key, self.expected,
          actual)
      return Result.FAIL, msg
    if self.qualifier == 'BUG':  # equal, but known bad
      return Result.BUG, ''
    if self.qualifier == 'N-I':  # equal, and known UNIMPLEMENTED
      return Result.NI, ''
    if self.qualifier == 'OK':  # equal, but ok (not ideal)
      return Result.OK, ''
    return Result.PASS, ''  # ideal behavior


# UNUSED
class NonzeroAssertion(object):
  """Check that an integer is not zero.

  NOTE: Do we need this now that we have qualifiers?
  """
  def __init__(self, key):
    self.key = key
    self.qualified = qualified  # whether this was a special case?

  def Check(self, shell, record):
    actual = record[self.key]
    if actual != 0:
      msg = '%s %s: Expected nonzero status, got %r' % (shell, self.key,
          actual)
      return Result.FAIL, msg
    if self.qualified:
      return Result.OK, ''
    return Result.PASS, ''


PIPE = subprocess.PIPE

def RunCases(cases, shells, case_predicate, verbose):
  #pprint.pprint(cases)

  sys.stdout.write(_BOLD)
  sys.stdout.write('case\tline\t')  # for line number and test number
  for sh_label, _ in shells:
    sys.stdout.write(sh_label)
    sys.stdout.write('\t')
  sys.stdout.write(_RESET)
  sys.stdout.write('\n')

  num_failed = 0
  num_bug = 0
  num_ni = 0
  num_ok = 0
  num_passed = 0
  num_skipped = 0

  for i, case in enumerate(cases):
    line_num = case['line_num']
    desc = case['desc']
    code = case['code']

    if not case_predicate(i, case):
      num_skipped += 1
      continue

    #print code

    debug_info = []  # by shell
    result_row = []

    for sh_label, sh_path in shells:

      #print '+', shell, case['desc']
      argv = [sh_path]  # TODO: Add flags
      p = subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE)
      p.stdin.write(code)
      p.stdin.close()

      actual = {}
      actual['stdout'] = p.stdout.read()
      actual['stderr'] = p.stderr.read()
      actual['status'] = p.wait()

      messages = []
      cell_result = Result.PASS

      # TODO: Warn about no assertions?  Well it will always test the error
      # code.
      assertions = CreateAssertions(case, sh_label)
      for a in assertions:
        result, msg = a.Check(sh_label, actual)
        # The minimum one wins.
        # If any failed, then the result is FAIL.
        # If any are OK, but none are FAIL, the result is OK.
        cell_result = min(cell_result, result)
        if msg:
          messages.append(msg)

      if cell_result != Result.PASS:
        debug_info.append(
            (sh_path, actual['stdout'], actual['stderr'], messages))

      result_row.append(cell_result)

      if cell_result == Result.FAIL:
        num_failed += 1
      elif cell_result == Result.BUG:
        num_bug += 1
      elif cell_result == Result.NI:
        num_ni += 1
      elif cell_result == Result.OK:
        num_ok += 1
      elif cell_result == Result.PASS:
        num_passed += 1
      else:
        raise AssertionError

    sys.stdout.write('%3d\t%3d\t' % (i, line_num))
    PrintResultRow(result_row)
    print(desc)  # repr(code)[:30]

    if verbose:
      for shell, stdout, stderr, messages in debug_info:
        for m in messages:
          print(m)
        print('%s stdout:' % shell)
        print(stdout)
        print('%s stderr:' % shell)
        print(stderr)

  print(
      '%d passed, %d ok, %d known unimplemented, %d known bugs, '
      '%d failed, %d skipped' % (num_passed, num_ok, num_ni, num_bug,
        num_failed, num_skipped))

  return num_failed == 0


RANGE_RE = re.compile('(\d+) \s* - \s* (\d+)', re.VERBOSE)


def ParseRange(range_str):
  try:
    d = int(range_str)
    return d, d  # singleton range
  except ValueError:
    m = RANGE_RE.match(range_str)
    if not m:
      raise RuntimeError('Invalid range %r' % range_str)
    b, e = m.groups()
    return int(b), int(e)


class RangePredicate(object):
  """Zero-based indexing, inclusive ranges."""

  def __init__(self, begin, end):
    self.begin = begin
    self.end = end

  def __call__(self, i, case):
    return self.begin <= i <= self.end


class RegexPredicate(object):
  """Filter by name."""

  def __init__(self, desc_re):
    self.desc_re = desc_re

  def __call__(self, i, case):
    return bool(self.desc_re.search(case['desc']))


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('test_sh.py [options] TEST_FILE shell...')
  p.add_option(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Show details about test execution')
  p.add_option(
      '--range', dest='range', default=None,
      help='Execute only a given test range, e.g. 5-10, 5-, -10, or 5')
  p.add_option(
      '--regex', dest='regex', default=None,
      help='Execute only tests whose description matches a given regex '
           '(case-insensitive)')
  p.add_option(
      '--list', dest='do_list', action='store_true', default=None,
      help='Just list tests')

  return p


def main(argv):
  o = Options()
  (opts, argv) = o.parse_args(argv)

  try:
    test_file = argv[1]
  except IndexError:
    o.print_usage()
    return 1

  shells = argv[2:]

  with open(test_file) as f:
    tokens = Tokenizer(LineIter(f))
    cases = ParseTestFile(tokens)

  if opts.do_list:
    for i, case in enumerate(cases):
      if opts.verbose:  # print the raw dictionary for debugging
        print(pprint.pformat(case))
      else:
        print('%d\t%s' % (i, case['desc']))
    return

  if opts.range:
    begin, end = ParseRange(opts.range)
    case_predicate = RangePredicate(begin, end)
  elif opts.regex:
    desc_re = re.compile(opts.regex, re.IGNORECASE)
    case_predicate = RegexPredicate(desc_re)
  else:
    case_predicate = lambda i, case: True

  shell_pairs = []
  for path in shells:
    name, _ = os.path.splitext(path)
    label = os.path.basename(name)
    shell_pairs.append((label, path))

  success = RunCases(cases, shell_pairs, case_predicate, opts.verbose)
  if not success:
    sys.exit(1)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
