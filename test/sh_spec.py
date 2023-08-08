#!/usr/bin/env python2
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
         For OSH this is behavior that was defined to be different?
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
import cStringIO
import errno
import json
import optparse
import os
import pprint
import re
import shutil
import subprocess
import sys
import time

from test import spec_lib
from doctools import html_head

log = spec_lib.log


# Magic strings for other variants of OSH.

# NOTE: osh_ALT is usually _bin/osh -- the release binary.
# It would be better to rename these osh-cpython and osh-ovm.  Have the concept
# of a suffix?

OSH_CPYTHON = ('osh', 'osh-dbg')
OTHER_OSH = ('osh_ALT',)

YSH_CPYTHON = ('ysh', 'ysh-dbg')
OTHER_YSH = ('oil_ALT',)


class ParseError(Exception):
  pass


# EXAMPLES:
## stdout: foo
## stdout-json: ""
#
# In other words, it could be (name, value) or (qualifier, name, value)

KEY_VALUE_RE = re.compile(r'''
   [#][#] \s+
   # optional prefix with qualifier and shells
   (?: (OK|BUG|N-I) \s+ ([\w+/]+) \s+ )?
   ([\w\-]+)              # key
   :
   \s* (.*)               # value
''', re.VERBOSE)

END_MULTILINE_RE = re.compile(r'''
    [#][#] \s+ END
''', re.VERBOSE)

# Line types
TEST_CASE_BEGIN = 0  # Starts with ####
KEY_VALUE = 1  # Metadata
KEY_VALUE_MULTILINE = 2  # STDOUT STDERR
END_MULTILINE = 3  # STDOUT STDERR
PLAIN_LINE = 4  # Uncommented
EOF = 5

LEX_OUTER = 0  # Ignore blank lines, e.g. for separating cases
LEX_RAW = 1  # Blank lines are significant


class Tokenizer(object):
  """Modal lexer!"""

  def __init__(self, f):
    self.f = f

    self.cursor = None
    self.line_num = 0

    self.next()

  def _ClassifyLine(self, line, lex_mode):
    if not line:  # empty
      return self.line_num, EOF, ''

    if lex_mode == LEX_OUTER and not line.strip():
      return None

    if line.startswith('####'):
      desc = line[4:].strip()
      return self.line_num, TEST_CASE_BEGIN, desc

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
      return self.line_num, token_type, (qualifier, shells, name, value)

    m = END_MULTILINE_RE.match(line)
    if m:
      return self.line_num, END_MULTILINE, None

    # If it starts with ##, it should be metadata.  This finds some typos.
    if line.lstrip().startswith('##'):
      raise RuntimeError('Invalid ## line %r' % line)

    if line.lstrip().startswith('#'):  # Ignore comments
      return None  # try again

    # Non-empty line that doesn't start with '#'
    # NOTE: We need the original line to test the whitespace sensitive <<-.
    # And we need rstrip because we add newlines back below.
    return self.line_num, PLAIN_LINE, line

  def next(self, lex_mode=LEX_OUTER):
    """Raises StopIteration when exhausted."""
    while True:
      line = self.f.readline()
      self.line_num += 1

      tok = self._ClassifyLine(line, lex_mode)
      if tok is not None:
        break

    self.cursor = tok
    return self.cursor

  def peek(self):
    return self.cursor


def AddMetadataToCase(case, qualifier, shells, name, value):
  shells = shells.split('/')  # bash/dash/mksh
  for shell in shells:
    if shell not in case:
      case[shell] = {}
    case[shell][name] = value
    case[shell]['qualifier'] = qualifier


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
#
# test_file = 
#   key_value*  -- file level metadata
#   (test_case '\n')*


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
        tokens.next(lex_mode=LEX_RAW)  # empty lines aren't skipped
        _, kind2, item2 = tokens.peek()
        if kind2 != PLAIN_LINE:
          break
        value_lines.append(item2)

      value = ''.join(value_lines)

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
      case['code'] = ''.join(code_lines)
      return
    code_lines.append(item)
    tokens.next(lex_mode=LEX_RAW)


def ParseTestCase(tokens):
  """Parse a single test case and return it.

  If at EOF, return None.
  """
  line_num, kind, item = tokens.peek()
  if kind == EOF:
    return None

  if kind != TEST_CASE_BEGIN:
    raise RuntimeError(
        "line %d: Expected TEST_CASE_BEGIN, got %r" % (line_num, [kind, item]))

  tokens.next()

  case = {'desc': item, 'line_num': line_num}

  ParseKeyValue(tokens, case)

  # For broken code
  if 'code' in case:  # Got it through a key value pair
    return case

  ParseCodeLines(tokens, case)
  ParseKeyValue(tokens, case)

  return case


_META_FIELDS = [
    'our_shell',
    'compare_shells',
    'suite',
    'tags',
    'oils_failures_allowed',
    ]


def ParseTestFile(test_file, tokens):
  """
  test_file: Only for error message
  """
  file_metadata = {}
  test_cases = []

  try:
    # Skip over the header.  Setup code can go here, although would we have to
    # execute it on every case?
    while True:
      line_num, kind, item = tokens.peek()
      if kind != KEY_VALUE:
        break

      qualifier, shells, name, value = item
      if qualifier is not None:
        raise RuntimeError('Invalid qualifier in spec file metadata')
      if shells is not None:
        raise RuntimeError('Invalid shells in spec file metadata')

      file_metadata[name] = value

      tokens.next()

    while True:  # Loop over cases
      test_case = ParseTestCase(tokens)
      if test_case is None:
        break
      test_cases.append(test_case)

  except StopIteration:
    raise RuntimeError('Unexpected EOF parsing test cases')

  for name in file_metadata:
    if name not in _META_FIELDS:
      raise RuntimeError('Invalid file metadata %r in %r' % (name, test_file))

  return file_metadata, test_cases


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
  case_sh = 'osh' if sh_label.startswith('osh') else sh_label

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

  no_traceback = SubstringAssertion('stderr', 'Traceback (most recent')
  assertions.append(no_traceback)

  #print 'SHELL', shell
  #pprint.pprint(case)
  #print(assertions)
  return assertions


class Result(object):
  """Result of an stdout/stderr/status assertion or of a (case, shell) cell.

  Order is important: the result of a cell is the minimum of the results of
  each assertion.
  """
  TIMEOUT = 0  # ONLY a cell result, not an assertion result
  FAIL = 1
  BUG = 2
  NI = 3
  OK = 4
  PASS = 5

  length = 6  # for loops


class EqualAssertion(object):
  """Check that two values are equal."""

  def __init__(self, key, expected, qualifier=None):
    self.key = key
    self.expected = expected  # expected value
    self.qualifier = qualifier  # whether this was a special case?

  def __repr__(self):
    return '<EqualAssertion %s == %r>' % (self.key, self.expected)

  def Check(self, shell, record):
    actual = record[self.key]
    if actual != self.expected:
      if len(str(self.expected)) < 40:
        msg = '[%s %s] Expected %r, got %r' % (shell, self.key, self.expected,
            actual)
      else:
        msg = '''
[%s %s]
Expected %r
Got      %r
''' % (shell, self.key, self.expected, actual)

      # TODO: Make this better and add a flag for it.
      if 0:
        import difflib
        for line in difflib.unified_diff(
            self.expected, actual, fromfile='expected', tofile='actual'):
          print(repr(line))

      return Result.FAIL, msg
    if self.qualifier == 'BUG':  # equal, but known bad
      return Result.BUG, ''
    if self.qualifier == 'N-I':  # equal, and known UNIMPLEMENTED
      return Result.NI, ''
    if self.qualifier == 'OK':  # equal, but ok (not ideal)
      return Result.OK, ''
    return Result.PASS, ''  # ideal behavior


class SubstringAssertion(object):
  """Check that a string like stderr doesn't have a substring."""

  def __init__(self, key, substring):
    self.key = key
    self.substring = substring

  def __repr__(self):
    return '<SubstringAssertion %s == %r>' % (self.key, self.substring)

  def Check(self, shell, record):
    actual = record[self.key]
    if self.substring in actual:
      msg = '[%s %s] Found %r' % (shell, self.key, self.substring)
      return Result.FAIL, msg
    return Result.PASS, ''


class Stats(object):
  def __init__(self, num_cases, sh_labels):
    self.counters = collections.defaultdict(int)
    c = self.counters
    c['num_cases'] = num_cases
    c['oils_num_passed'] = 0
    c['oils_num_failed'] = 0
    # Number of osh_ALT results that differed from osh.
    c['oils_ALT_delta'] = 0

    self.by_shell = {}
    for sh in sh_labels:
      self.by_shell[sh] = collections.defaultdict(int)
    self.nonzero_results = collections.defaultdict(int)

    self.tsv_rows = []

  def Inc(self, counter_name):
    self.counters[counter_name] += 1

  def Get(self, counter_name):
    return self.counters[counter_name]

  def Set(self, counter_name, val):
    self.counters[counter_name] = val

  def ReportCell(self, case_num, cell_result, sh_label):
    self.tsv_rows.append((str(case_num), sh_label, TEXT_CELLS[cell_result]))

    self.by_shell[sh_label][cell_result] += 1
    self.nonzero_results[cell_result] += 1

    c = self.counters
    if cell_result == Result.TIMEOUT:
      c['num_timeout'] += 1
    elif cell_result == Result.FAIL:
      # Special logic: don't count osh_ALT because its failures will be
      # counted in the delta.
      if sh_label not in OTHER_OSH + OTHER_YSH:
        c['num_failed'] += 1

      if sh_label in OSH_CPYTHON + YSH_CPYTHON:
        c['oils_num_failed'] += 1
    elif cell_result == Result.BUG:
      c['num_bug'] += 1
    elif cell_result == Result.NI:
      c['num_ni'] += 1
    elif cell_result == Result.OK:
      c['num_ok'] += 1
    elif cell_result == Result.PASS:
      c['num_passed'] += 1
      if sh_label in OSH_CPYTHON + YSH_CPYTHON:
        c['oils_num_passed'] += 1
    else:
      raise AssertionError()

  def WriteTsv(self, f):
    f.write('case\tshell\tresult\n')
    for row in self.tsv_rows:
      f.write('\t'.join(row))
      f.write('\n')


PIPE = subprocess.PIPE

def RunCases(cases, case_predicate, shells, env, out, opts):
  """
  Run a list of test 'cases' for all 'shells' and write output to 'out'.
  """
  if opts.trace:
    for _, sh in shells:
      log('\tshell: %s', sh)
      print('\twhich $SH: ', end='', file=sys.stderr)
      subprocess.call(['which', sh])

  #pprint.pprint(cases)

  sh_labels = [sh_label for sh_label, _ in shells]

  out.WriteHeader(sh_labels)
  stats = Stats(len(cases), sh_labels)

  # Make an environment for each shell.  $SH is the path to the shell, so we
  # can test flags, etc.
  sh_env = []
  for _, sh_path in shells:
    e = dict(env)
    e[opts.sh_env_var_name] = sh_path
    sh_env.append(e)

  # Determine which one (if any) is osh-cpython, for comparison against other
  # shells.
  osh_cpython_index = -1
  for i, (sh_label, _) in enumerate(shells):
    if sh_label in OSH_CPYTHON:
      osh_cpython_index = i
      break

  timeout_dir = os.path.abspath('_tmp/spec/timeouts')
  try:
    shutil.rmtree(timeout_dir)
    os.mkdir(timeout_dir)
  except OSError:
    pass

  # Now run each case, and print a table.
  for i, case in enumerate(cases):
    line_num = case['line_num']
    desc = case['desc']
    code = case['code']

    if opts.trace:
      log('case %d: %s', i, desc)

    if not case_predicate(i, case):
      stats.Inc('num_skipped')
      continue

    if opts.do_print:
      print('#### %s' % case['desc'])
      print(case['code'])
      print()
      continue

    stats.Inc('num_cases_run')

    result_row = []

    for shell_index, (sh_label, sh_path) in enumerate(shells):
      timeout_file = os.path.join(timeout_dir, '%02d-%s' % (i, sh_label))
      if opts.timeout:
        if opts.timeout_bin:
          # This is what smoosh itself uses.  See smoosh/tests/shell_tests.sh
          # QUIRK: interval can only be a whole number
          argv = [
              opts.timeout_bin,
              '-t', opts.timeout,
              # Somehow I'm not able to get this timeout file working?  I think
              # it has a bug when using stdin.  It waits for the background
              # process too.

              #'-i', '1',
              #'-l', timeout_file
          ]
        else:
          # This kills hanging tests properly, but somehow they fail with code
          # -9?
          #argv = ['timeout', '-s', 'KILL', opts.timeout]

          # s suffix for seconds
          argv = ['timeout', opts.timeout + 's']
      else:
        argv = []
      argv.append(sh_path)

      # dash doesn't support -o posix
      if opts.posix and sh_label != 'dash':
        argv.extend(['-o', 'posix'])

      if opts.trace:
        log('\targv: %s', ' '.join(argv))

      case_env = sh_env[shell_index]

      # Unique dir for every test case and shell
      tmp_base = os.path.normpath(opts.tmp_env)  # no . or ..
      case_tmp_dir = os.path.join(tmp_base, '%02d-%s' % (i, sh_label))

      try:
        os.makedirs(case_tmp_dir)
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise

      # Some tests assume _tmp exists
      try:
        os.mkdir(os.path.join(case_tmp_dir, '_tmp'))
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise

      case_env['TMP'] = case_tmp_dir

      if opts.pyann_out_dir:
        case_env = dict(case_env)
        case_env['PYANN_OUT'] = os.path.join(opts.pyann_out_dir, '%d.json' % i)

      try:
        p = subprocess.Popen(argv, env=case_env, cwd=case_tmp_dir,
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

      if opts.timeout_bin and os.path.exists(timeout_file):
        cell_result = Result.TIMEOUT
      elif not opts.timeout_bin and actual['status'] == 124:
        cell_result = Result.TIMEOUT
      else:
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

        if cell_result != Result.PASS or opts.details:
          d = (i, sh_label, actual['stdout'], actual['stderr'], messages)
          out.AddDetails(d)

      result_row.append(cell_result)

      stats.ReportCell(i, cell_result, sh_label)

      if sh_label in OTHER_OSH:
        # This is only an error if we tried to run ANY OSH.
        if osh_cpython_index == -1:
          raise RuntimeError("Couldn't determine index of osh-cpython")

        other_result = result_row[shell_index]
        cpython_result = result_row[osh_cpython_index]
        if other_result != cpython_result:
          stats.Inc('oils_ALT_delta')

    out.WriteRow(i, line_num, result_row, desc)

  return stats


# ANSI color constants
_RESET = '\033[0;0m'
_BOLD = '\033[1m'

_RED = '\033[31m'
_GREEN = '\033[32m'
_YELLOW = '\033[33m'
_PURPLE = '\033[35m'


TEXT_CELLS = {
    Result.TIMEOUT: 'TIME',
    Result.FAIL: 'FAIL',
    Result.BUG: 'BUG',
    Result.NI: 'N-I',
    Result.OK: 'ok',
    Result.PASS: 'pass',
}

ANSI_COLORS = {
    Result.TIMEOUT: _PURPLE,
    Result.FAIL: _RED,
    Result.BUG: _YELLOW,
    Result.NI: _YELLOW,
    Result.OK: _YELLOW,
    Result.PASS: _GREEN,
}

def _AnsiCells():
  lookup = {}
  for i in xrange(Result.length):
    lookup[i] = ''.join([ANSI_COLORS[i], _BOLD, TEXT_CELLS[i], _RESET])
  return lookup

ANSI_CELLS = _AnsiCells()


HTML_CELLS = {
    Result.TIMEOUT: '<td class="timeout">TIME',
    Result.FAIL: '<td class="fail">FAIL',
    Result.BUG: '<td class="bug">BUG',
    Result.NI: '<td class="n-i">N-I',
    Result.OK: '<td class="ok">ok',
    Result.PASS: '<td class="pass">pass',
}


def _ValidUtf8String(s):
  """Return an arbitrary string as a readable utf-8 string.

  We output utf-8 to either HTML or the console.  If we get invalid utf-8 as
  stdout/stderr (which is very possible), then show the ASCII repr().
  """
  try:
    s.decode('utf-8')
    return s  # it decoded OK
  except UnicodeDecodeError:
    return repr(s)  # ASCII representation


class Output(object):

  def __init__(self, f, verbose):
    self.f = f
    self.verbose = verbose
    self.details = []

  def BeginCases(self, test_file):
    pass

  def WriteHeader(self, sh_labels):
    pass

  def WriteRow(self, i, line_num, row, desc):
    pass

  def EndCases(self, sh_labels, stats):
    pass

  def AddDetails(self, entry):
    self.details.append(entry)

  # Helper function
  def _WriteDetailsAsText(self, details):
    for case_index, shell, stdout, stderr, messages in details:
      print('case: %d' % case_index, file=self.f)
      for m in messages:
        print(m, file=self.f)

      # Assume the terminal can show utf-8, but we don't want random binary.
      print('%s stdout:' % shell, file=self.f)
      print(_ValidUtf8String(stdout), file=self.f)

      print('%s stderr:' % shell, file=self.f)
      print(_ValidUtf8String(stderr), file=self.f)

      print('', file=self.f)


class TeeOutput(object):
  """For multiple outputs in one run, e.g. HTML and TSV.

  UNUSED
  """

  def __init__(self, outs):
    self.outs = outs

  def BeginCases(self, test_file):
    for out in self.outs:
      out.BeginCases(test_file)

  def WriteHeader(self, sh_labels):
    for out in self.outs:
      out.WriteHeader(sh_labels)

  def WriteRow(self, i, line_num, row, desc):
    for out in self.outs:
      out.WriteRow(i, line_num, row, desc)

  def EndCases(self, sh_labels, stats):
    for out in self.outs:
      out.EndCases(sh_labels, stats)

  def AddDetails(self, entry):
    for out in self.outs:
      out.AddDetails(entry)


class TsvOutput(Output):
  """Write a plain-text TSV file.

  UNUSED since we are outputting LONG format with --tsv-output.
  """

  def WriteHeader(self, sh_labels):
    self.f.write('case\tline\t')  # case number and line number
    for sh_label in sh_labels:
      self.f.write(sh_label)
      self.f.write('\t')
    self.f.write('\n')

  def WriteRow(self, i, line_num, row, desc):
    self.f.write('%3d\t%3d\t' % (i, line_num))

    for result in row:
      c = TEXT_CELLS[result]
      self.f.write(c)
      self.f.write('\t')

    # note: 'desc' could use QSN, but just ignore it for now
    #self.f.write(desc)
    self.f.write('\n')


class AnsiOutput(Output):

  def BeginCases(self, test_file):
    self.f.write('%s\n' % test_file)

  def WriteHeader(self, sh_labels):
    self.f.write(_BOLD)
    self.f.write('case\tline\t')  # case number and line number
    for sh_label in sh_labels:
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

  def _WriteShellSummary(self, sh_labels, stats):
    if len(stats.nonzero_results) <= 1:  # Skip trivial summaries
      return

    # Reiterate header
    self.f.write(_BOLD)
    self.f.write('\t\t')
    for sh_label in sh_labels:
      self.f.write(sh_label)
      self.f.write('\t')
    self.f.write(_RESET)
    self.f.write('\n')

    # Write totals by cell.  
    for result in sorted(stats.nonzero_results, reverse=True):
      self.f.write('\t%s' % ANSI_CELLS[result])
      for sh_label in sh_labels:
        self.f.write('\t%d' % stats.by_shell[sh_label][result])
      self.f.write('\n')

    # The bottom row is all the same, but it helps readability.
    self.f.write('\ttotal')
    for sh_label in sh_labels:
      self.f.write('\t%d' % stats.counters['num_cases_run'])
    self.f.write('\n')

  def EndCases(self, sh_labels, stats):
    print()
    self._WriteShellSummary(sh_labels, stats)


class HtmlOutput(Output):

  def __init__(self, f, verbose, spec_name, sh_labels, cases):
    Output.__init__(self, f, verbose)
    self.spec_name = spec_name
    self.sh_labels = sh_labels  # saved from header
    self.cases = cases  # for linking to code
    self.row_html = []  # buffered

  def _SourceLink(self, line_num, desc):
    return '<a href="%s.test.html#L%d">%s</a>' % (
        self.spec_name, line_num, cgi.escape(desc))

  def BeginCases(self, test_file):
    css_urls = [ '../../../web/base.css', '../../../web/spec-tests.css' ]
    title = '%s: spec test case results' % self.spec_name
    html_head.Write(self.f, title, css_urls=css_urls)

    self.f.write('''\
  <body class="width60">
    <p id="home-link">
      <a href=".">spec test index</a>
      /
      <a href="/">oilshell.org</a>
    </p>
    <h1>Results for %s</h1>
    <table>
    ''' % test_file)

  def _WriteShellSummary(self, sh_labels, stats):
    # NOTE: This table has multiple <thead>, which seems OK.
    self.f.write('''
<thead>
  <tr class="table-header">
  ''')

    columns = ['status'] + sh_labels + ['']
    for c in columns:
      self.f.write('<td>%s</td>' % c)

    self.f.write('''
  </tr>
</thead>
''')

    # Write totals by cell.
    for result in sorted(stats.nonzero_results, reverse=True):
      self.f.write('<tr>')

      self.f.write(HTML_CELLS[result])
      self.f.write('</td> ')

      for sh_label in sh_labels:
        self.f.write('<td>%d</td>' % stats.by_shell[sh_label][result])

      self.f.write('<td></td>')
      self.f.write('</tr>\n')

    # The bottom row is all the same, but it helps readability.
    self.f.write('<tr>')
    self.f.write('<td>total</td>')
    for sh_label in sh_labels:
      self.f.write('<td>%d</td>' % stats.counters['num_cases_run'])
    self.f.write('<td></td>')
    self.f.write('</tr>\n')

    # Blank row for space.
    self.f.write('<tr>')
    for i in xrange(len(sh_labels) + 2):
      self.f.write('<td style="height: 2em"></td>')
    self.f.write('</tr>\n')

  def WriteHeader(self, sh_labels):
    f = cStringIO.StringIO()

    f.write('''
<thead>
  <tr class="table-header">
  ''')

    columns = ['case'] + sh_labels
    for c in columns:
      f.write('<td>%s</td>' % c)
    f.write('<td class="case-desc">description</td>')

    f.write('''
  </tr>
</thead>
''')

    self.row_html.append(f.getvalue())

  def WriteRow(self, i, line_num, row, desc):
    f = cStringIO.StringIO()
    f.write('<tr>')
    f.write('<td>%3d</td>' % i)

    show_details = False

    for result in row:
      c = HTML_CELLS[result]
      if result not in (Result.PASS, Result.TIMEOUT):  # nothing to show
        show_details = True

      f.write(c)
      f.write('</td>')
      f.write('\t')

    f.write('<td class="case-desc">')
    f.write(self._SourceLink(line_num, desc))
    f.write('</td>')
    f.write('</tr>\n')

    # Show row with details link.
    if show_details:
      f.write('<tr>')
      f.write('<td class="details-row"></td>')  # for the number

      for col_index, result in enumerate(row):
        f.write('<td class="details-row">')
        if result != Result.PASS:
          sh_label = self.sh_labels[col_index]
          f.write('<a href="#details-%s-%s">details</a>' % (i, sh_label))
        f.write('</td>')

      f.write('<td class="details-row"></td>')  # for the description
      f.write('</tr>\n')

    self.row_html.append(f.getvalue())  # buffer it

  def _WriteStats(self, stats):
    self.f.write(
        '%(num_passed)d passed, %(num_ok)d OK, '
        '%(num_ni)d not implemented, %(num_bug)d BUG, '
        '%(num_failed)d failed, %(num_timeout)d timeouts, '
        '%(num_skipped)d cases skipped\n' % stats.counters)

  def EndCases(self, sh_labels, stats):
    self._WriteShellSummary(sh_labels, stats)

    # Write all the buffered rows
    for h in self.row_html:
      self.f.write(h)

    self.f.write('</table>\n')
    self.f.write('<pre>')
    self._WriteStats(stats)
    if stats.Get('oils_num_failed'):
      self.f.write('%(oils_num_failed)d failed under osh\n' % stats.counters)
    self.f.write('</pre>')

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

        # stdout might contain invalid utf-8; make it valid;
        valid_utf8 = _ValidUtf8String(s)

        self.f.write(cgi.escape(valid_utf8))
        self.f.write('</pre>')

      self.f.write('<i>stdout:</i> <br/>\n')
      _WriteRaw(stdout)

      self.f.write('<i>stderr:</i> <br/>\n')
      _WriteRaw(stderr)

      self.f.write('</td>')
      self.f.write('</tr>')

    self.f.write('</table>')


def MakeTestEnv(opts):
  if not opts.tmp_env:
    raise RuntimeError('--tmp-env required')
  if not opts.path_env:
    raise RuntimeError('--path-env required')
  env = {
    'PATH': opts.path_env,
    'LANG': opts.lang_env,
  }
  for p in opts.env_pair:
    name, value = p.split('=', 1)
    env[name] = value

  return env


def _DefaultSuite(spec_name):
  if spec_name.startswith('ysh-'):
    suite = 'ysh'
  elif spec_name.startswith('hay'):  # hay.test.sh is ysh
    suite = 'ysh'

  elif spec_name.startswith('tea-'):
    suite = 'tea'
  else:
    suite = 'osh'

  return suite


def ParseTestList(test_files):
    for test_file in test_files:
      with open(test_file) as f:
        tokens = Tokenizer(f)
        try:
          file_metadata, cases = ParseTestFile(test_file, tokens)
        except RuntimeError as e:
          log('ERROR in %r', test_file)
          raise

      tmp = os.path.basename(test_file)
      spec_name = tmp.split('.')[0]  # foo.test.sh -> foo

      suite = file_metadata.get('suite') or _DefaultSuite(spec_name)

      tmp = file_metadata.get('tags')
      tags = tmp.split() if tmp else []

      # Don't need compare_shells, etc. to decide what to run

      row = {'spec_name': spec_name, 'suite': suite, 'tags': tags}
      #print(row)
      yield row


def main(argv):
  # First check if bash is polluting the environment.  Tests rely on the
  # environment.
  v = os.getenv('RANDOM')
  if v is not None:
    raise AssertionError('got $RANDOM = %s' % v)
  v = os.getenv('PPID')
  if v is not None:
    raise AssertionError('got $PPID = %s' % v)

  p = optparse.OptionParser('%s [options] TEST_FILE shell...' % sys.argv[0])
  spec_lib.DefineCommon(p)
  spec_lib.DefineShSpec(p)
  opts, argv = p.parse_args(argv)

  # --print-tagged to figure out what to run
  if opts.print_tagged:
    to_find = opts.print_tagged
    for row in ParseTestList(argv[1:]):
      if to_find in row['tags']:
        print(row['spec_name'])
    return 0

  # --print-table to figure out what to run
  if opts.print_table:
    for row in ParseTestList(argv[1:]):
      print('%(suite)s\t%(spec_name)s' % row)
      #print(row)
    return 0

  #
  # Now deal with a single file
  #

  try:
    test_file = argv[1]
  except IndexError:
    p.print_usage()
    return 1

  with open(test_file) as f:
    tokens = Tokenizer(f)
    file_metadata, cases = ParseTestFile(test_file, tokens)

  # List test cases and return
  if opts.do_list:
    for i, case in enumerate(cases):
      if opts.verbose:  # print the raw dictionary for debugging
        print(pprint.pformat(case))
      else:
        print('%d\t%s' % (i, case['desc']))
    return 0

  # for test/spec-cpp.sh
  if opts.print_spec_suite:
    tmp = os.path.basename(test_file)
    spec_name = tmp.split('.')[0]  # foo.test.sh -> foo

    suite = file_metadata.get('suite') or _DefaultSuite(spec_name)
    print(suite)
    return 0

  if opts.verbose:
    for k, v in file_metadata.items():
      print('\t%-20s: %s' % (k, v), file=sys.stderr)
    print('', file=sys.stderr)

  if opts.oils_bin_dir:

    shells = []

    if opts.compare_shells:
      comp = file_metadata.get('compare_shells')
      # Compare 'compare_shells' and Python
      shells.extend(comp.split() if comp else [])

    # Always run with the Python version
    our_shell = file_metadata.get('our_shell', 'osh')  # default is OSH
    shells.append(os.path.join(opts.oils_bin_dir, our_shell))

    # Legacy OVM/CPython build
    if opts.ovm_bin_dir:
      shells.append(os.path.join(opts.ovm_bin_dir, our_shell))

    # New C++ build
    if opts.oils_cpp_bin_dir:
      shells.append(os.path.join(opts.oils_cpp_bin_dir, our_shell))

    # Overwrite it when --oils-bin-dir is set
    # It's no longer a flag
    opts.oils_failures_allowed = \
        int(file_metadata.get('oils_failures_allowed', 0))

  else:
    # TODO: remove this mode?
    shells = argv[2:]

  shell_pairs = spec_lib.MakeShellPairs(shells)

  if opts.range:
    begin, end = spec_lib.ParseRange(opts.range)
    case_predicate = spec_lib.RangePredicate(begin, end)
  elif opts.regex:
    desc_re = re.compile(opts.regex, re.IGNORECASE)
    case_predicate = spec_lib.RegexPredicate(desc_re)
  else:
    case_predicate = lambda i, case: True

  out_f = sys.stderr if opts.do_print else sys.stdout

  # Set up output style.  Also see asdl/format.py
  if opts.format == 'ansi':
    out = AnsiOutput(out_f, opts.verbose)

  elif opts.format == 'html':
    spec_name = os.path.basename(test_file)
    spec_name = spec_name.split('.')[0]

    sh_labels = [label for label, _ in shell_pairs]

    out = HtmlOutput(out_f, opts.verbose, spec_name, sh_labels, cases)

  else:
    raise AssertionError()

  out.BeginCases(os.path.basename(test_file))

  env = MakeTestEnv(opts)
  stats = RunCases(cases, case_predicate, shell_pairs, env, out, opts)

  out.EndCases([sh_label for sh_label, _ in shell_pairs], stats)

  if opts.tsv_output:
    with open(opts.tsv_output, 'w') as f:
      stats.WriteTsv(f)

  # TODO: Could --stats-{file,template} be a separate awk step on .tsv files?
  stats.Set('oils_failures_allowed', opts.oils_failures_allowed)
  if opts.stats_file:
    with open(opts.stats_file, 'w') as f:
      f.write(opts.stats_template % stats.counters)
      f.write('\n')  # bash 'read' requires a newline

  if stats.Get('num_failed') == 0:
    return 0

  # spec/smoke.test.sh -> smoke
  test_name = os.path.basename(test_file).split('.')[0]

  allowed = opts.oils_failures_allowed
  all_count = stats.Get('num_failed')
  oils_count = stats.Get('oils_num_failed')
  if allowed == 0:
    log('')
    log('%s: FATAL: %d tests failed (%d oils failures)', test_name, all_count,
        oils_count)
    log('')
  else:
    # If we got EXACTLY the allowed number of failures, exit 0.
    if allowed == all_count and all_count == oils_count:
      log('%s: note: Got %d allowed oils failures (exit with code 0)',
          test_name, allowed)
      return 0
    else:
      log('')
      log('%s: FATAL: Got %d failures (%d oils failures), but %d are allowed',
          test_name, all_count, oils_count, allowed)
      log('')

  return 1


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt as e:
    print('%s: interrupted with Ctrl-C' % sys.argv[0], file=sys.stderr)
    sys.exit(1)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
