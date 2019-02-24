#!/usr/bin/python
"""
ui.py
"""
from __future__ import print_function

import sys

# Only for GetTerminalSize().  OSH should implement that function in C to avoid
# dependencies.
import fcntl
import struct
import termios

import traceback


_RESET = '\033[0;0m'
_BOLD = '\033[1m'
_UNDERLINE = '\033[4m'
_REVERSE = '\033[7m'  # reverse video

_YELLOW = '\033[33m'
_BLUE = '\033[34m'
#_MAGENTA = '\033[35m'
_CYAN = '\033[36m'


# ANSI escape codes affect the prompt!
# https://superuser.com/questions/301353/escape-non-printing-characters-in-a-function-for-a-bash-prompt
#
# Readline understands \x01 and \x02, while bash understands \[ and \].

PROMPT_BOLD = '\x01%s\x02' % _BOLD
PROMPT_RESET = '\x01%s\x02' % _RESET
PROMPT_UNDERLINE = '\x01%s\x02' % _UNDERLINE
PROMPT_REVERSE = '\x01%s\x02' % _REVERSE


if 0:
  DEBUG_F = open('_tmp/demo-debug', 'w')
else:
  DEBUG_F = open('/dev/null', 'w')


def log(msg, *args, **kwargs):
  if args:
    msg = msg % args
  f = kwargs.get('file', sys.stderr)
  print(msg, file=f)
  f.flush()


def GetTerminalSize():
  # fd 0 = stdin.  The arg has to be 4 bytes for some reason.
  try:
    b = fcntl.ioctl(0, termios.TIOCGWINSZ, '1234')
  except IOError:
    # TODO: Should dynamically fall back on MinimalDisplay?
    return 25, 80

  #log('%r', b)
  cr = struct.unpack('hh', b)  # 2 short integers
  #log('%s', cr)
  return cr


class _IDisplay(object):
  """Interface for completion displays."""

  def __init__(self, comp_state, num_lines_cap, f):
    self.comp_state = comp_state
    self.num_lines_cap = num_lines_cap
    self.f = f

  def PrintCandidates(self, *args):
    try:
      self._PrintCandidates(*args)
    except Exception as e:
      traceback.print_exc()

  def SetPromptLength(self, i):
    # NiceDisplay needs this to return to original location.
    pass

  def Reset(self):
    """Call this in between commands."""
    pass

  def ShowPromptOnRight(self):
    # Doesn't apply to MinimalDisplay
    pass

  def EraseLines(self):
    # Doesn't apply to MinimalDisplay
    pass

  def PrintRequired(self, msg, *args):
    # This gets called with "nothing to display"
    pass

  def PrintOptional(self, msg, *args):
    pass

  def OnWindowChange(self):
    # MinimalDisplay doesn't care about terminal width.
    pass


class MinimalDisplay(_IDisplay):
  """A display with minimal dependencies.
  
  It doesn't output color or depend on the terminal width.
  It could be useful if we ever have a browser build!  We can see completion
  without testing it.
  """
  def __init__(self, comp_state, num_lines_cap=10, f=sys.stdout):
    _IDisplay.__init__(self, comp_state, num_lines_cap, f)

    self.reader = None

  def SetReader(self, r):
    """Dependency injection."""
    self.reader = r

  def _RedrawPrompt(self):
    # NOTE: This has to reprint the prompt and the command line!
    # Like bash, we SAVE the prompt and print it, rather than re-evaluating it.
    self.f.write(self.reader.CurrentRenderedPrompt())
    self.f.write(self.comp_state.orig_line)

  def _PrintCandidates(self, unused_subst, matches, unused_match_len):
    #log('_PrintCandidates %s', matches)
    self.f.write('\n')  # need this
    common_prefix_pos = self.comp_state.common_prefix_pos
    assert common_prefix_pos != -1

    too_many = False
    i = 0
    for m in matches:
      self.f.write(' %s\n' % m[common_prefix_pos:])

      if i == self.num_lines_cap:
        too_many = True
        i += 1  # Count this one
        break

      i += 1

    if too_many:
      num_left = len(matches) - i
      if num_left:
        self.f.write(' ... and %d more\n' % num_left)

    self._RedrawPrompt()

  def PrintRequired(self, msg, *args):
    self.f.write('\n')
    if args:
      msg = msg % args
    self.f.write(' %s\n' % msg)  # need a newline
    self._RedrawPrompt()


def _PrintPacked(matches, max_match_len, term_width, max_lines, f):
  # With of each candidate.  2 spaces between each.
  w = max_match_len + 2

  # Number of candidates per line.  Don't print in first or last column.
  num_per_line = max(1, (term_width-2) // w)

  fmt = '%-' + str(w) + 's'
  num_lines = 0

  too_many = False
  remainder = num_per_line - 1
  i = 0  # num matches
  for m in matches:
    if i % num_per_line == 0:
      f.write(' ')  # 1 space left gutter

    f.write(fmt % m)

    if i % num_per_line == remainder:
      f.write('\n')  # newline (leaving 1 space right gutter)
      num_lines += 1

      # Check if we've printed enough lines
      if num_lines == max_lines:
        too_many = True
        i += 1  # count this one
        break
    i += 1

  # Write last line break, unless it came out exactly.
  if i % num_per_line != 0:
    #log('i = %d, num_per_line = %d, i %% num_per_line = %d',
    #    i, num_per_line, i % num_per_line)

    f.write('\n')
    num_lines += 1

  if too_many:
    # TODO: Save this in the Display class
    fmt2 = _BOLD + _BLUE + '%' + str(term_width-2) + 's' + _RESET
    num_left = len(matches) - i
    if num_left:
      f.write(fmt2 % '... and %d more\n' % num_left)
      num_lines += 1

  return num_lines


def _PrintLong(matches, max_match_len, term_width, max_lines, descriptions, f):
  """Print flags with descriptions, one per line.

  Args:
    descriptions: dict of { prefix-stripped match -> description }

  Returns:
    The number of lines printed.
  """
  #log('desc = %s', descriptions)

  # Subtract 3 chars: 1 for left and right margin, and then 1 for the space in
  # between.
  max_desc = max(0, term_width - max_match_len - 3)
  fmt = ' %-' + str(max_match_len) + 's ' + _YELLOW + '%s' + _RESET + '\n'

  num_lines = 0

  # rl_match is a raw string, which may or may not have a trailing space
  for rl_match in matches:
    desc = descriptions.get(rl_match) or ''
    if max_desc == 0:  # the window is not wide enough for some flag
      f.write(' %s\n' % rl_match)
    else:
      if len(desc) > max_desc:
        desc = desc[:max_desc-5] + ' ... '
      f.write(fmt % (rl_match, desc))

    num_lines += 1

    if num_lines == max_lines:
      # right justify
      fmt2 = _BOLD + _BLUE + '%' + str(term_width-1) + 's' + _RESET
      num_left = len(matches) - num_lines
      if num_left:
        f.write(fmt2 % '... and %d more\n' % num_left)
        num_lines += 1
      break

  return num_lines


class NiceDisplay(_IDisplay):
  """Methods to display completion candidates and other messages.

  This object has to remember how many lines we last drew, in order to erase
  them before drawing something new.

  It's also useful for:
  - Stripping off the common prefix according to OUR rules, not readline's.
  - displaying descriptions of flags and builtins
  """
  def __init__(self, comp_state, f=sys.stdout, num_lines_cap=10,
               bold_line=False):
    """
    Args:
      bold_line: Should user's entry be bold?
    """
    _IDisplay.__init__(self, comp_state, num_lines_cap, f)

    self.bold_line = bold_line

    self.last_prompt_len = -1  # invalid

    self.width_is_dirty = True
    self.term_width = -1  # invalid

    self.num_lines_last_displayed = 0

    self.c_count = 0
    self.m_count = 0

    # hash of matches -> count.  Has exactly ONE entry at a time.
    self.dupes = {}

  def Reset(self):
    """Call this in between commands."""
    self.num_lines_last_displayed = 0
    self.dupes.clear()

  def SetPromptLength(self, i):
    self.last_prompt_len = i

  def _ReturnToPrompt(self, num_lines):
    # NOTE: We can't use ANSI terminal codes to save and restore the prompt,
    # because the screen may have scrolled.  Instead we have to keep track of
    # how many lines we printed and the original column of the cursor.

    orig_len = len(self.comp_state.orig_line)

    self.f.write('\x1b[%dA' % num_lines)  # UP
    assert self.last_prompt_len != -1
    n = orig_len + self.last_prompt_len
    self.f.write('\x1b[%dC' % n)  # RIGHT

    if self.bold_line:
      self.f.write(_BOLD)  # Experiment

    self.f.flush()

  def _PrintCandidates(self, unused_subst, matches, unused_max_match_len):
    term_width = self._GetTerminalWidth()

    # Variables set by the completion generator.  They should always exist,
    # because we can't get "matches" without calling that function.
    common_prefix_pos = self.comp_state.common_prefix_pos

    self.f.write('\n')

    self.EraseLines()  # Delete previous completions!
    log('_PrintCandidates %r', unused_subst, file=DEBUG_F)

    # Figure out if the user hit TAB multiple times to show more matches.
    # It's not correct to hash the line itself, because two different lines can
    # have the same completions:
    #
    # ls <TAB>
    # ls --<TAB>
    #
    # This is because there is a common prefix.
    # So instead use the hash of all matches as the identity.

    # This could be more accurate but I think it's good enough.
    comp_id = hash(''.join(matches))
    if comp_id in self.dupes:
      self.dupes[comp_id] += 1
    else:
      self.dupes.clear()  # delete the old ones
      self.dupes[comp_id] = 1

    max_lines = self.num_lines_cap * self.dupes[comp_id]

    assert common_prefix_pos != -1
    if common_prefix_pos == 0:  # slight optimization for first word
      to_display = matches
    else:
      to_display = [m[common_prefix_pos:] for m in matches]

    # Calculate max length after stripping prefix.
    max_match_len = max(len(m) for m in to_display)

    # TODO: NiceDisplay should truncate when max_match_len > term_width?
    # Also truncate when a single candidate is super long?

    # Print and go back up.  But we have to ERASE these before hitting enter!
    if self.comp_state.get('DESC'):  # exists and is NON EMPTY
      num_lines = _PrintLong(to_display, max_match_len, term_width,
                             max_lines, self.comp_state['DESC'], self.f)
    else:
      num_lines = _PrintPacked(to_display, max_match_len, term_width,
                               max_lines, self.f)

    self._ReturnToPrompt(num_lines+1)
    self.num_lines_last_displayed = num_lines

    self.c_count += 1

  def PrintRequired(self, msg, *args):
    """
    Print a message below the prompt, and then return to the location on the
    prompt line.
    """
    if args:
      msg = msg % args

    # This will mess up formatting
    assert not msg.endswith('\n'), msg

    self.f.write('\n')

    self.EraseLines()
    log('PrintOptional %r', msg, file=DEBUG_F)

    # Truncate to terminal width
    max_len = self._GetTerminalWidth() - 2
    if len(msg) > max_len:
      msg = msg[:max_len-5] + ' ... '

    # NOTE: \n at end is REQUIRED.  Otherwise we get drawing problems when on
    # the last line.
    fmt = _BOLD + _BLUE + '%' + str(max_len) + 's' + _RESET + '\n'
    self.f.write(fmt % msg)

    self._ReturnToPrompt(2)

    self.num_lines_last_displayed = 1
    self.m_count += 1

  def PrintOptional(self, msg, *args):
    self.PrintRequired(msg, *args)

  def ShowPromptOnRight(self, rendered):
    n = self._GetTerminalWidth() - 2 - len(rendered)
    spaces = ' ' * n

    # We avoid drawing problems if we print it on its own line:
    # - inserting text doesn't push it to the right
    # - you can't overwrite it
    self.f.write(spaces + _REVERSE + ' ' + rendered + ' ' + _RESET + '\r\n')

  def EraseLines(self):
    """Clear N lines one-by-one.

    Assume the cursor is right below thep rompt:

    ish$ echo hi
    _ <-- HERE

    That's the first line to erase out of N.  After erasing them, return it
    there.
    """
    if self.bold_line:
      self.f.write(_RESET)  # if command is bold
      self.f.flush()

    n = self.num_lines_last_displayed

    log('EraseLines %d (c = %d, m = %d)', n, self.c_count, self.m_count,
        file=DEBUG_F)

    if n == 0:
      return

    for i in xrange(n):
      # 2K would clear the ENTIRE line, but isn't strictly necessary.
      self.f.write('\x1b[0K')
      self.f.write('\x1b[%dB' % 1)  # go down one line

    # Now go back up
    self.f.write('\x1b[%dA' % n)
    self.f.flush()  # Without this, output will look messed up

  def _GetTerminalWidth(self):
    if self.width_is_dirty:
      _, self.term_width = GetTerminalSize()
      self.width_is_dirty = False
    return self.term_width

  def OnWindowChange(self):
    # Only do it for the NEXT completion.  The signal handler can be run in
    # between arbitrary bytecodes, and we don't want a single completion
    # display to be shown with different widths.
    self.width_is_dirty = True

