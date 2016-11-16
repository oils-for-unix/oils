#!/usr/bin/env python3
"""
ui.py - User interface constructs.
"""

import sys


def Clear():
  sys.stdout.write('\033[2J')  # clear screen
  sys.stdout.write('\033[2;0H')  # Move to 2,0  (below status bar)
  sys.stdout.flush()


class StatusLine(object):

  def __init__(self, row_num=3, width=200):
    # NOTE: '%-80s' % msg doesn't do this, because it doesn't pad at the end
    self.width = width
    self.row_num = row_num

  def _FormatMessage(self, msg):
    max_width = self.width - 4  # two spaces on each side
    # Truncate if necessary.  TODO: could display truncation char?
    msg = msg[:max_width]

    num_end_spaces = max_width - len(msg) + 2  # at least 2 spaces at the end

    to_print = '  %s%s' % (msg, ' ' * num_end_spaces)
    return to_print

  def Write(self, msg, *args):
    if args:
      msg = msg % args

    sys.stdout.write('\033[s')  # save
    # TODO: When there is more than one option for completion, we scroll past
    # this.
    # TODO: Should status line be BELOW, and disappear after readline?
    # Or really it should be at the right margin?  At hit Ctrl-C to cancel?

    sys.stdout.write('\033[%d;0H' % self.row_num)  # Move the cursor

    sys.stdout.write('\033[7m')  # reverse video

    # Make sure you draw the same number of spaces
    # TODO: detect terminal width

    sys.stdout.write(self._FormatMessage(msg))

    sys.stdout.write('\033[0m')  # remove attributes

    sys.stdout.write('\033[u')  # restore
    sys.stdout.flush()


class NullStatusLine(object):

  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    pass


class TestStatusLine(object):

  def __init__(self):
    pass

  def Write(self, msg, *args):
    """NOTE: We could use logging?"""
    if args:
      msg = msg % args
    print('\t' + msg)


def MakeStatusLines():
  return [StatusLine(row_num=i) for i in range(3, 10)]


def PrintError(error_stack, pool, f):
  for token, msg in error_stack:
    if token:
      #print(token)
      #print(token.pool_index)
      i = token.pool_index
      if i == -1:
        line = '<token had no position info>'
        path = '<unknown>'
        line_num = -1
      else:
        line = pool.GetLine(i)
        path, line_num = pool.GetDebugInfo(i)
      print('Line %d of %r' % (line_num+1, path))
      print('  ' + line.rstrip())
      col = token.col
      length = token.length
      if col == -1:
        print('NO COL')
      else:
        sys.stdout.write('  ')
        # preserve tabs
        for c in line[:col]:
          sys.stdout.write('\t' if c == '\t' else ' ')
        sys.stdout.write('^')
        sys.stdout.write('~' * (length-1))
        sys.stdout.write('\n')
    else:
      #print('<no token>')
      pass

    print(msg, file=f)
    print('---')
  #print(error_stack, file=f)
