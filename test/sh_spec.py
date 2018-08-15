#!/usr/bin/env python
from __future__ import print_function
"""
sh_spec.py -- Test framework to compare shells.

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

NOTE: The difference between OK and BUG is a matter of judgement.  If the ideal
behavior is a compile time error (code 2), a runtime error is generally OK.

If ALL shells agree on a broken behavior, they are all marked OK (but our
implementation will be PASS.)  But if the behavior is NOT POSIX compliant, then
it will be a BUG.

If one shell disagrees with others, that is generally a BUG.

Example test case:

#### hello and fail
echo hello
echo world
exit 1
## status: 1
#
# ignored comment
#
## STDOUT:
hello
world
## END

"""

import collections
import cgi
import json
import optparse
import os
import pprint
import re
import subprocess
import sys
import time


# Magic strings for other variants of OSH.

# NOTE: osh_ALT is usually _bin/osh -- the release binary.
# It would be better to rename these osh-cpython and osh-ovm.  Have the concept
# of a suffix?  Then we can have osh-byterun too.

OTHER_OSH = ('osh_ALT', 'osh-byterun') 


class ParseError(Exception):
  pass


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# EXAMPLES:
## stdout: foo
## stdout-json: ""
#
# In other words, it could be (name, value) or (qualifier, name, value)

KEY_VALUE_RE = re.compile(r'''
   [#][#] \s+
   (?: (OK|BUG|N-I) \s+ ([\w+/]+) \s+ )?   # optional prefix
   ([\w\-]+)              # key
   :
   \s* (.*)               # value
''', re.VERBOSE)

END_MULTILINE_RE = re.compile(r'''
    [#][#] \s+ END
''', re.VERBOSE)

# Line types
TEST_CASE_BEGIN = 0  # Starts with ###
KEY_VALUE = 1  # Metadata
KEY_VALUE_MULTILINE = 2  # STDOUT STDERR
END_MULTILINE = 3  # STDOUT STDERR
PLAIN_LINE = 4  # Uncommented
EOF = 5


def LineIter(f):
  """Iterate over lines, classify them by token type, and parse token value."""
  for i, line in enumerate(f):
    if not line.strip():
      continue

    line_num = i+1  # 1-based

    if line.startswith('####'):
      desc = line[4:].strip()
      yield line_num, TEST_CASE_BEGIN, desc
      continue

    m = KEY_VALUE_RE.match(line)
    if m:
      qualifier, shells, name, value = m.groups()
      # HACK: Expected data should have the newline.
      if name in ('stdout', 'stderr'):
        value += '\n'

      if name in ('STDOUT', 'STDERR'):
        token_type = KEY_VALUE_MULTILINE
      else:
        token_type = KEY_VALUE
      yield line_num, token_type, (qualifier, shells, name, value)
      continue

    m = END_MULTILINE_RE.match(line)
    if m:
      yield line_num, END_MULTILINE, None
      continue

    if line.lstrip().startswith('#'):
      # Ignore comments
      #yield COMMENT, line
      continue

    # Non-empty line that doesn't start with '#'
    # NOTE: We need the original line to test the whitespace sensitive <<-.
    # And we need rstrip because we add newlines back below.
    yield line_num, PLAIN_LINE, line.rstrip('\n')

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
# code = PLAIN_LINE*
#      | '## code:'  VALUE
#
# -- Key value pairs can be single- or multi-line
# key_value = '##' KEY ':' VALUE
#             | KEY_VALUE_MULTILINE PLAIN_LINE* END_MULTILINE
#
# -- Description, then key-value pairs surrounding code.
# test_case = '####' DESC
#             key_value*
#             code
#             key_value*
#
# -- Should be a blank line after each test case.  Leading comments and code
# -- are OK.
# test_file = (COMMENT | PLAIN_LINE)* (test_case '\n')*


def AddMetadataToCase(case, qualifier, shells, name, value):
  shells = shells.split('/')  # bash/dash/mksh
  for shell in shells:
    if shell not in case:
      case[shell] = {}
    case[shell][name] = value
    case[shell]['qualifier'] = qualifier


def ParseKeyValue(tokens, case):
  """Parse commented-out metadata in a test case.

  The metadata must be contiguous.

  Args:
    tokens: Tokenizer
    case: dictionary to add to
  """
  while True:
    line_num, kind, item = tokens.peek()

    if kind == KEY_VALUE_MULTILINE:
      qualifier, shells, name, empty_value = item
      if empty_value:
        raise ParseError(
            'Line %d: got value %r for %r, but the value should be on the '
            'following lines' % (line_num, empty_value, name))

      value_lines = []
      while True:
        tokens.next()
        _, kind2, item2 = tokens.peek()
        if kind2 != PLAIN_LINE:
          break
        value_lines.append(item2)

      value = '\n'.join(value_lines) + '\n'

      name = name.lower()  # STDOUT -> stdout
      if qualifier:
        AddMetadataToCase(case, qualifier, shells, name, value)
      else:
        case[name] = value

      # END token is optional.
      if kind2 == END_MULTILINE:
        tokens.next()

    elif kind == KEY_VALUE:
      qualifier, shells, name, value = item

      if qualifier:
        AddMetadataToCase(case, qualifier, shells, name, value)
      else:
        case[name] = value

      tokens.next()

    else:  # Unknown token type
      break


def ParseCodeLines(tokens, case):
  """Parse uncommented code in a test case."""
  _, kind, item = tokens.peek()
  if kind != PLAIN_LINE:
    raise ParseError('Expected a line of code (got %r, %r)' % (kind, item))
  code_lines = []
  while True:
    _, kind, item = tokens.peek()
    if kind != PLAIN_LINE:
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

  assert kind == TEST_CASE_BEGIN, (line_num, kind, item)  # Invariant
  tokens.next()

  case = {'desc': item, 'line_num': line_num}

  ParseKeyValue(tokens, case)

  # For broken code
  if 'code' in case:  # Got it through a key value pair
    return case

  ParseCodeLines(tokens, case)
  ParseKeyValue(tokens, case)

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

  # For testing invalid unicode
  exp_repr = d.get(key + '-repr')
  if exp_repr is not None:
    exp = eval(exp_repr)
    a = EqualAssertion(key, exp, qualifier=qualifier)
    assertions.append(a)
    found = True

  return found


def CreateIntAssertion(d, key, assertions, qualifier=False):
  exp = d.get(key)  # expected
  if exp is not None:
    # For now, turn it into int
    a = EqualAssertion(key, int(exp), qualifier=qualifier)
    assertions.append(a)
    return True
  return False


def CreateAssertions(case, sh_label):
  """
  Given a raw test case and a shell label, create EqualAssertion instances to
  run.
  """
  assertions = []

  # Whether we found assertions
  stdout = False
  stderr = False
  status = False

  # So the assertion are exactly the same for osh and osh_ALT
  case_sh = 'osh' if sh_label in OTHER_OSH else sh_label

  if case_sh in case:
    q = case[case_sh]['qualifier']
    if CreateStringAssertion(case[case_sh], 'stdout', assertions, qualifier=q):
      stdout = True
    if CreateStringAssertion(case[case_sh], 'stderr', assertions, qualifier=q):
      stderr = True
    if CreateIntAssertion(case[case_sh], 'status', assertions, qualifier=q):
      status = True

  if not stdout:
    CreateStringAssertion(case, 'stdout', assertions)
  if not stderr:
    CreateStringAssertion(case, 'stderr', assertions)
  if not status:
    if 'status' in case:
      CreateIntAssertion(case, 'status', assertions)
    else:
      # If the user didn't specify a 'status' assertion, assert that the exit
      # code is 0.
      a = EqualAssertion('status', 0)
      assertions.append(a)

  #print 'SHELL', shell
  #pprint.pprint(case)
  #print(assertions)
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
      msg = '[%s %s] Expected %r, got %r' % (shell, self.key, self.expected,
          actual)
      return Result.FAIL, msg
    if self.qualifier == 'BUG':  # equal, but known bad
      return Result.BUG, ''
    if self.qualifier == 'N-I':  # equal, and known UNIMPLEMENTED
      return Result.NI, ''
    if self.qualifier == 'OK':  # equal, but ok (not ideal)
      return Result.OK, ''
    return Result.PASS, ''  # ideal behavior


PIPE = subprocess.PIPE

def RunCases(cases, case_predicate, shells, env, out):
  """
  Run a list of test 'cases' for all 'shells' and write output to 'out'.
  """
  #pprint.pprint(cases)

  out.WriteHeader(shells)

  stats = collections.defaultdict(int)
  stats['num_cases'] = len(cases)
  stats['osh_num_passed'] = 0
  stats['osh_num_failed'] = 0
  # Number of osh_ALT results that differed from osh.
  stats['osh_ALT_delta'] = 0

  # Make an environment for each shell.  $SH is the path to the shell, so we
  # can test flags, etc.
  sh_env = []
  for _, sh_path in shells:
    e = dict(env)
    e['SH'] = sh_path
    sh_env.append(e)

  # Determine which one (if any) is osh-cpython, for comparison against other
  # shells.
  osh_cpython_index = -1
  for i, (sh_label, _) in enumerate(shells):
    if sh_label == 'osh':
      osh_cpython_index = i
      break

  # Now run each case, and print a table.
  for i, case in enumerate(cases):
    line_num = case['line_num']
    desc = case['desc']
    code = case['code']

    if not case_predicate(i, case):
      stats['num_skipped'] += 1
      continue

    #print code

    result_row = []

    for shell_index, (sh_label, sh_path) in enumerate(shells):
      argv = [sh_path]  # TODO: Be able to test shell flags?
      try:
        p = subprocess.Popen(argv, env=sh_env[shell_index],
                             stdin=PIPE, stdout=PIPE, stderr=PIPE)
      except OSError as e:
        print('Error running %r: %s' % (sh_path, e), file=sys.stderr)
        sys.exit(1)

      p.stdin.write(code)
      p.stdin.close()

      actual = {}
      actual['stdout'] = p.stdout.read()
      actual['stderr'] = p.stderr.read()
      p.stdout.close()
      p.stderr.close()

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
        d = (i, sh_label, actual['stdout'], actual['stderr'], messages)
        out.AddDetails(d)

      result_row.append(cell_result)

      if cell_result == Result.FAIL:
        # Special logic: don't count osh_ALT beacuse its failures will be
        # counted in the delta.
        if sh_label not in OTHER_OSH:
          stats['num_failed'] += 1

        if sh_label == 'osh':
          stats['osh_num_failed'] += 1
      elif cell_result == Result.BUG:
        stats['num_bug'] += 1
      elif cell_result == Result.NI:
        stats['num_ni'] += 1
      elif cell_result == Result.OK:
        stats['num_ok'] += 1
      elif cell_result == Result.PASS:
        stats['num_passed'] += 1
        if sh_label == 'osh':
          stats['osh_num_passed'] += 1
      else:
        raise AssertionError

      if sh_label in OTHER_OSH:
        # This is only an error if we tried to run ANY OSH.
        if osh_cpython_index == -1:
          raise RuntimeError("Couldn't determine index of osh-cpython")

        other_result = result_row[shell_index]
        cpython_result = result_row[osh_cpython_index]
        if other_result != cpython_result:
          stats['osh_ALT_delta'] += 1

    out.WriteRow(i, line_num, result_row, desc)

  return stats


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


# ANSI color constants
_RESET = '\033[0;0m'
_BOLD = '\033[1m'

_RED = '\033[31m'
_GREEN = '\033[32m'
_YELLOW = '\033[33m'


COLOR_FAIL = ''.join([_RED, _BOLD, 'FAIL', _RESET])
COLOR_BUG = ''.join([_YELLOW, _BOLD, 'BUG', _RESET])
COLOR_NI = ''.join([_YELLOW, _BOLD, 'N-I', _RESET])
COLOR_OK = ''.join([_YELLOW, _BOLD, 'ok', _RESET])
COLOR_PASS = ''.join([_GREEN, _BOLD, 'pass', _RESET])


ANSI_CELLS = {
    Result.FAIL: COLOR_FAIL,
    Result.BUG: COLOR_BUG,
    Result.NI: COLOR_NI,
    Result.OK: COLOR_OK,
    Result.PASS: COLOR_PASS,
}

HTML_CELLS = {
    Result.FAIL: '<td class="fail">FAIL',
    Result.BUG: '<td class="bug">BUG',
    Result.NI: '<td class="n-i">N-I',
    Result.OK: '<td class="ok">ok',
    Result.PASS: '<td class="pass">pass',
}


class ColorOutput(object):

  def __init__(self, f, verbose):
    self.f = f
    self.verbose = verbose
    self.details = []

  def AddDetails(self, entry):
    self.details.append(entry)

  def BeginCases(self, test_file):
    self.f.write('%s\n' % test_file)

  def WriteHeader(self, shells):
    self.f.write(_BOLD)
    self.f.write('case\tline\t')  # for line number and test number
    for sh_label, _ in shells:
      self.f.write(sh_label)
      self.f.write('\t')
    self.f.write(_RESET)
    self.f.write('\n')

  def WriteRow(self, i, line_num, row, desc):
    self.f.write('%3d\t%3d\t' % (i, line_num))

    for result in row:
      c = ANSI_CELLS[result]
      self.f.write(c)
      self.f.write('\t')

    self.f.write(desc)
    self.f.write('\n')

    if self.verbose:
      self._WriteDetailsAsText(self.details)
      self.details = []

  def _WriteDetailsAsText(self, details):
    for case_index, shell, stdout, stderr, messages in details:
      print('case: %d' % case_index, file=self.f)
      for m in messages:
        print(m, file=self.f)
      print('%s stdout:' % shell, file=self.f)
      try:
        print(stdout.decode('utf-8'), file=self.f)
      except UnicodeDecodeError:
        print(stdout, file=self.f)
      print('%s stderr:' % shell, file=self.f)
      try:
        print(stderr.decode('utf-8'), file=self.f)
      except UnicodeDecodeError:
        print(stderr, file=self.f)
      print('', file=self.f)

  def _WriteStats(self, stats):
    self.f.write(
        '%(num_passed)d passed, %(num_ok)d ok, '
        '%(num_ni)d known unimplemented, %(num_bug)d known bugs, '
        '%(num_failed)d failed, %(num_skipped)d skipped\n' % stats)

  def EndCases(self, stats):
    self._WriteStats(stats)


class AnsiOutput(ColorOutput):
  pass


class HtmlOutput(ColorOutput):

  def __init__(self, f, verbose, spec_name, sh_labels, cases):
    ColorOutput.__init__(self, f, verbose)
    self.spec_name = spec_name
    self.sh_labels = sh_labels  # saved from header
    self.cases = cases  # for linking to code

  def _SourceLink(self, line_num, desc):
    return '<a href="%s.test.html#L%d">%s</a>' % (
        self.spec_name, line_num, cgi.escape(desc))

  def BeginCases(self, test_file):
    self.f.write('''\
<!DOCTYPE html>
<html>
  <head>
    <link href="../../web/spec-tests.css" rel="stylesheet">
  </head>
  <body>
    <p id="home-link">
      <a href=".">spec test index</a>
      /
      <a href="/">oilshell.org</a>
    </p>
    <h1>Results for %s</h1>
    <table>
    ''' % test_file)

  def EndCases(self, stats):
    self.f.write('</table>\n')
    self.f.write('<p>')
    self._WriteStats(stats)
    self.f.write('</p>')

    if self.details:
      self._WriteDetails()

    self.f.write('</body></html>')

  def _WriteDetails(self):
    self.f.write("<h2>Details on runs that didn't PASS</h2>")
    self.f.write('<table id="details">')

    for case_index, sh_label, stdout, stderr, messages in self.details:
      self.f.write('<tr>')
      self.f.write('<td><a name="details-%s-%s"></a><b>%s</b></td>' % (
        case_index, sh_label, sh_label))

      self.f.write('<td>')

      # Write description and link to the code
      case = self.cases[case_index]
      line_num = case['line_num']
      desc = case['desc']
      self.f.write('%d ' % case_index)
      self.f.write(self._SourceLink(line_num, desc))
      self.f.write('<br/><br/>\n')

      for m in messages:
        self.f.write('<span class="assertion">%s</span><br/>\n' % cgi.escape(m))
      if messages:
        self.f.write('<br/>\n')

      def _WriteRaw(s):
        self.f.write('<pre>')
        # We output utf-8-encoded HTML.  If we get invalid utf-8 as stdout
        # (which is very possible), then show the ASCII repr().
        try:
          s.decode('utf-8')
        except UnicodeDecodeError:
          valid_utf8 = repr(s)  # ASCII representation
        else:
          valid_utf8 = s
        self.f.write(cgi.escape(valid_utf8))
        self.f.write('</pre>')

      self.f.write('<i>stdout:</i> <br/>\n')
      _WriteRaw(stdout)

      self.f.write('<i>stderr:</i> <br/>\n')
      _WriteRaw(stderr)

      self.f.write('</td>')
      self.f.write('</tr>')

    self.f.write('</table>')

  def WriteHeader(self, shells):
    # TODO: Use oil template language for this...
    self.f.write('''
<thead>
  <tr>
  ''')

    columns = ['case'] + [sh_label for sh_label, _ in shells]
    for c in columns:
      self.f.write('<td>%s</td>' % c)
    self.f.write('<td class="case-desc">description</td>')

    self.f.write('''
  </tr>
</thead>
''')

  def WriteRow(self, i, line_num, row, desc):
    self.f.write('<tr>')
    self.f.write('<td>%3d</td>' % i)

    non_passing = False

    for result in row:
      c = HTML_CELLS[result]
      if result != Result.PASS:
        non_passing = True

      self.f.write(c)
      self.f.write('</td>')
      self.f.write('\t')

    self.f.write('<td class="case-desc">')
    self.f.write(self._SourceLink(line_num, desc))
    self.f.write('</td>')
    self.f.write('</tr>\n')

    # Show row with details link.
    if non_passing:
      self.f.write('<tr>')
      self.f.write('<td class="details-row"></td>')  # for the number

      for col_index, result in enumerate(row):
        self.f.write('<td class="details-row">')
        if result != Result.PASS:
          sh_label = self.sh_labels[col_index]
          self.f.write('<a href="#details-%s-%s">details</a>' % (i, sh_label))
        self.f.write('</td>')

      self.f.write('<td class="details-row"></td>')  # for the description
      self.f.write('</tr>\n')


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('sh_spec.py [options] TEST_FILE shell...')
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
  p.add_option(
      '--format', dest='format', choices=['ansi', 'html'], default='ansi',
      help="Output format (default 'ansi')")
  p.add_option(
      '--stats-file', dest='stats_file', default=None,
      help="File to write stats to")
  p.add_option(
      '--stats-template', dest='stats_template', default='',
      help="Python format string for stats")
  p.add_option(
      '--osh-failures-allowed', dest='osh_failures_allowed', type='int',
      default=0, help="Allow this number of osh failures")
  p.add_option(
      '--path-env', dest='path_env', default='',
      help="The full PATH, for finding binaries used in tests.")
  p.add_option(
      '--tmp-env', dest='tmp_env', default='',
      help="A temporary directory that the tests can use.")

  return p


def main(argv):
  # First check if bash is polluting the environment.  Tests rely on the
  # environment.
  v = os.getenv('RANDOM')
  if v is not None:
    raise AssertionError('got $RANDOM = %s' % v)
  v = os.getenv('PPID')
  if v is not None:
    raise AssertionError('got $PPID = %s' % v)

  o = Options()
  (opts, argv) = o.parse_args(argv)

  try:
    test_file = argv[1]
  except IndexError:
    o.print_usage()
    return 1

  shells = argv[2:]

  shell_pairs = []
  saw_osh = False
  for path in shells:
    name, _ = os.path.splitext(path)
    label = os.path.basename(name)
    if label == 'osh':
      # change the second 'osh' to 'osh_ALT' so it's distinct
      if saw_osh:
        label = 'osh_ALT'
      else:
        saw_osh = True
    shell_pairs.append((label, path))

  with open(test_file) as f:
    tokens = Tokenizer(LineIter(f))
    cases = ParseTestFile(tokens)

  # List test cases and return
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

  # Set up output style.  Also see asdl/format.py
  if opts.format == 'ansi':
    out = AnsiOutput(sys.stdout, opts.verbose)
  elif opts.format == 'html':
    spec_name = os.path.basename(test_file)
    spec_name = spec_name.split('.')[0]

    sh_labels = [label for label, _ in shell_pairs]

    out = HtmlOutput(sys.stdout, opts.verbose, spec_name, sh_labels, cases)
  else:
    raise AssertionError

  out.BeginCases(os.path.basename(test_file))

  if not opts.tmp_env:
    raise RuntimeError('--tmp-env required')
  if not opts.path_env:
    raise RuntimeError('--path-env required')
  env = {
    'TMP': os.path.normpath(opts.tmp_env),  # no .. or .
    'PATH': opts.path_env,
    # Copied from my own environment.  For now, we want to test bash and other
    # shells in utf-8 mode.
    'LANG': 'en_US.UTF-8',
  }
  stats = RunCases(cases, case_predicate, shell_pairs, env, out)
  out.EndCases(stats)

  stats['osh_failures_allowed'] = opts.osh_failures_allowed
  if opts.stats_file:
    with open(opts.stats_file, 'w') as f:
      f.write(opts.stats_template % stats)
      f.write('\n')  # bash 'read' requires a newline

  if stats['num_failed'] == 0:
    return 0

  allowed = opts.osh_failures_allowed
  all_count = stats['num_failed']
  osh_count = stats['osh_num_failed']
  if allowed == 0:
    log('')
    log('FATAL: %d tests failed (%d osh failures)', all_count, osh_count)
    log('')
  else:
    # If we got EXACTLY the allowed number of failures, exit 0.
    if allowed == all_count and all_count == osh_count:
      log('note: Got %d allowed osh failures (exit with code 0)', allowed)
      return 0
    else:
      log('')
      log('FATAL: Got %d failures (%d osh failures), but %d are allowed',
          all_count, osh_count, allowed)
      log('')

  return 1


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
