#!/usr/bin/python
"""
pyreadline.py

Let's think of the interactive shell prompt roughly as a state machine.

Inputs:
  - Enter a line that finishes a command
  - Enter a line that's incomplete.
  - Hitting TAB to complete
    - which display multiple candidates or fill in a single candidate
  - Ctrl-C to cancel a COMMAND in progress.
  - Ctrl-C to cancel a COMPLETION in progress, for slow completions.
    - NOTE: if there are blocking NFS calls, completion should go in a
      thread/process?
  - EOF: Ctrl-D on an EMPTY line.
    (Ctrl-D on a non-empty line behaves just like hitting enter)
  - SIGWINCH: Terminal width change.

Actions:
  - Display completions, which depends on the terminal width.
  - Display a 1-line message showing lack of completions ('no variables that
    begin with $')
  - Execute a command
  - Clear N lines below the prompt (must happen frequently)
  - Exit the shell

State:
  - The terminal width.  Changes dynamically.
  - The prompt: PS1 or PS2.  (Or could save/restore here?)
  - The number of lines to clear next.  EraseLines() uses this.
  - The completion that is in progress.  The 'compopt' builtin affects this.
  - The number of times you have requested the same completion (to show more
    lines)

TODO for this demo:
  - copy in FileSystemAction?  That might make it somewhat usable.
    - how does 'ls' get both flag and path completion?  See bash-completion.
  - experiment with ordering?  You would have to disable readline sorting

LATER:
  - Could have a caching decorator, because we recompute candidates every time.
    For $PATH entries?

Readline settings to experiment with:

Variable: int rl_sort_completion_matches
  If an application sets this variable to 0, Readline will not sort the list of
  completions (which implies that it cannot remove any duplicate completions).
  The default value is 1, which means that Readline will sort the completions
  and, depending on the value of rl_ignore_completion_duplicates, will attempt
  to remove duplicate matches. 

We should handle all of this in OSH.
"""
from __future__ import print_function

import os
import readline
import signal
import sys
import time
import traceback

# Only for GetTerminalSize().  They should be implemented in C to avoid
# dependencies.
import fcntl
import struct
import termios


_RESET = '\033[0;0m'
_BOLD = '\033[1m'

_YELLOW = '\033[33m'
_BLUE = '\033[34m'
#_MAGENTA = '\033[35m'
_CYAN = '\033[36m'



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
  b = fcntl.ioctl(0, termios.TIOCGWINSZ, '1234')
  #log('%r', b)
  cr = struct.unpack('hh', b)  # 2 short integers
  #log('%s', cr)
  return cr


class NullAction(object):
  def Matches(self, prefix):
    return []

_NULL_ACTION = NullAction()


class WordsAction(object):
  """Yield a fixed list of completion candidates."""
  def __init__(self, words, delay=None):
    self.words = words
    self.delay = delay

  def Matches(self, prefix):
    for w in self.words:
      if w.startswith(prefix):
        if self.delay is not None:
          time.sleep(self.delay)

        yield w


class FlagsHelpAction(object):
  """Yield flags and their help.
  
  Return a list of TODO: This API can't be expressed in shell itself.  How do
  zsh and fish do it?
  """

  def __init__(self, flags):
    self.flags = flags  # a list of tuples

  def Matches(self, prefix):
    for flag, desc in self.flags:
      if flag.startswith(prefix):
        yield flag, desc


def MultiLineCommand(pending_lines):
  last_line_pos = 0
  parts = []
  for line in pending_lines:
    if line.endswith('\\\n'):
      line = line[:-2]
      last_line_pos += len(line)
    parts.append(line)
  cmd = ''.join(parts)
  return cmd, last_line_pos


def MakeCompletionRequest(lines):
  """Returns a 4-tuple or an error code.

  Cases we CAN complete:

    echo foo \
    f<TAB>

    echo foo \
    bar f<TAB>

  Cases we CAN'T complete:
    ec\
    h<TAB>    # complete 'o' ?
    
    echo f\
    o<TAB>    # complete 'o' ?
  """
  #log('pending_lines %s', pending_lines)

  # first word can't be split over multiple lines
  if len(lines) > 1 and ' ' not in lines[0]:
    return -1

  partial_cmd, last_line_pos = MultiLineCommand(lines)

  first = None  # the first word, or None if we're completing the first word
                # itself (and the candidate is in

  cmd_last_space_pos = partial_cmd.rfind(' ')
  if cmd_last_space_pos == -1:  # FIRST WORD state, no prefix
    prefix_pos = 0
    to_complete = partial_cmd
    prefix = ''

  else:  # Completing an argument, may be on any line
    # Find the first word with the left-most space.  (Not the right-most space
    # above).

    j = partial_cmd.find(' ')
    assert j != -1
    first = partial_cmd[:j]

    # The space has to be on the current line, or be the last char on the
    # previous line before the line continuation.  Otherwise we can't complete
    # anything.
    if cmd_last_space_pos < last_line_pos-1:
      return -2

    last_line = lines[-1]
    line_space_pos = last_line.rfind(' ')
    if line_space_pos == -1:  # space is on previous line
      prefix_pos = 0  # complete all of this line
    else:
      prefix_pos = line_space_pos + 1

    #log('space_pos = %d, last_line_pos = %d', line_space_pos, last_line_pos)

    to_complete = last_line[prefix_pos:]
    prefix = last_line[:prefix_pos]

  #log('X partial_cmd %r', partial_cmd, file=DEBUG_F)
  #log('X to_complete %r', to_complete, file=DEBUG_F)

  return first, to_complete, prefix, prefix_pos


class RootCompleter(object):
  """Dispatch to multiple completers."""

  def __init__(self, reader, display, comp_lookup, comp_state):
    """
    Args:
      reader: for completing the entire command, not just one line
      comp_lookup: Dispatch to completion logic for different commands
      comp_state: fields are added here for Display
    """
    self.reader = reader
    self.display = display
    self.comp_lookup = comp_lookup
    self.comp_state = comp_state

  def Matches(self, comp):
    line = comp['line']
    self.comp_state['ORIG'] = line

    #log('lines %s', self.reader.pending_lines, file=DEBUG_F)
    lines = list(self.reader.pending_lines)
    lines.append(line)

    result = MakeCompletionRequest(lines)
    if result == -1:
      self.display.PrintMessage("(can't complete first word spanning lines)")
      return
    if result == -2:
      self.display.PrintMessage("(can't complete last word spanning lines)")
      return

    # We have to add on prefix before sending it completer.  And then
    first, to_complete, prefix, prefix_pos = result

    # For the Display callback to look at
    self.comp_state['prefix_pos'] = prefix_pos

    # Reset this at the beginning of each completion.
    # Is there any way to avoid creating a duplicate dictionary each time?
    # I think every completer could have an optional PAYLOAD.
    # Yes that is better.
    # And maybe you can yield the original 'c' too, without prefix and ' '.
    self.comp_state['DESC'] = {}

    if first:
      completer = self.comp_lookup.get(first, _NULL_ACTION)
    else:
      completer = self.comp_lookup['__first']

    #log('to_complete: %r', to_complete, file=DEBUG_F)

    i = 0
    start_time = time.time()
    for match in completer.Matches(to_complete):
      if isinstance(match, tuple):
        flag, desc = match  # hack
        if flag.endswith('='):  # Hack for --color=auto
          rl_match = flag
        else:
          rl_match = flag + ' '
        self.comp_state['DESC'][rl_match] = desc  # save it for later
      else:
        rl_match = match + ' '

      yield prefix + rl_match
      # TODO: avoid calling time() so much?
      elapsed_ms = (time.time() - start_time) * 1000

      # NOTES:
      # - Ctrl-C works here!  You only get the first 5 candidates.
      # - These progress messages will not help if the file system hangs!  We
      #   might want to run "adversarial completions" in a separate process?
      i += 1
      if elapsed_ms > 200:
        plural = '' if i == 1 else 'es'
        self.display.PrintMessage(
            '... %d match%s for %r in %d ms (Ctrl-C to cancel)', i,
            plural, line, elapsed_ms)

    if i == 0:
      self.display.PrintMessage('(no matches for %r)', line)


class CompletionCallback(object):
  """Registered with the readline library and called for completions."""

  def __init__(self, root_comp):
    self.root_comp = root_comp
    self.iter = None

  def Call(self, word_prefix, state):
    """Generate completions."""
    if state == 0:  # initial completion
      orig_line = readline.get_line_buffer()
      comp = {'line': orig_line}
      self.iter = self.root_comp.Matches(comp)

    try:
      c = self.iter.next()
    except StopIteration:
      c = None
    return c

  def __call__(self, word_prefix, state):
    try:
      return self.Call(word_prefix, state)
    except Exception as e:
      # Readline swallows exceptions!
      print(e)
      raise


def PrintPacked(matches, max_match_len, term_width, max_lines):
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
      sys.stdout.write(' ')  # 1 space left gutter

    sys.stdout.write(fmt % m)

    if i % num_per_line == remainder:
      sys.stdout.write('\n')  # newline (leaving 1 space right gutter)
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

    sys.stdout.write('\n')
    num_lines += 1

  if too_many:
    # TODO: Save this in the Display class
    fmt2 = _BOLD + _BLUE + '%' + str(term_width-2) + 's' + _RESET
    num_left = len(matches) - i
    if num_left:
      sys.stdout.write(fmt2 % '... and %d more\n' % num_left)
      num_lines += 1

  return num_lines


def PrintLong(matches, max_match_len, term_width, max_lines, descriptions):
  """Print flags with descriptions, one per line.

  Args:
    descriptions: dict of { prefix-stripped match -> description }

  Returns:
    The number of lines printed.
  """
  #log('desc = %s', descriptions)

  # Why subtract 3?  1 char for left and right margin, and then 1 for the space
  # in between.
  max_desc = max(0, term_width - max_match_len - 3)
  fmt = ' %-' + str(max_match_len) + 's ' + _YELLOW + '%s' + _RESET

  num_lines = 0

  # rl_match is a raw string, which may or may not have a trailing space
  for rl_match in matches:
    desc = descriptions.get(rl_match) or ''
    if max_desc == 0:  # the window is not wide enough for some flag
      print(' %s' % rl_match)
    else:
      if len(desc) > max_desc:
        desc = desc[:max_desc-5] + ' ... '
      print(fmt % (rl_match, desc))

    num_lines += 1

    if num_lines == max_lines:
      # right justify
      fmt2 = _BOLD + _BLUE + '%' + str(term_width-1) + 's' + _RESET
      num_left = len(matches) - num_lines
      if num_left:
        sys.stdout.write(fmt2 % '... and %d more\n' % num_left)
        num_lines += 1
      break

  return num_lines


class Display(object):
  """Methods to display completion candidates and other messages.

  This object has to remember how many lines we last drew, in order to erase
  them before drawing something new.

  It's also useful for:
  - Stripping off the common prefix according to OUR rules, not readline's.
  - displaying descriptions of flags and builtins
  """
  def __init__(self, comp_state, reader):
    self.comp_state = comp_state
    self.reader = reader

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

  def _ReturnToPrompt(self, num_lines):
    # NOTE: We can't use ANSI terminal codes to save and restore the prompt,
    # because the screen may have scrolled.  Instead we have to keep track of
    # how many lines we printed and the original column of the cursor.

    orig_len = len(self.comp_state['ORIG'])
    prompt_len = len(self.reader.prompt_str)  # may change between PS1 and PS2

    sys.stdout.write('\x1b[%dA' % num_lines)  # UP
    n = orig_len + prompt_len
    sys.stdout.write('\x1b[%dC' % n)  # RIGHT
    sys.stdout.flush()

  def _PrintCandidates(self, subst, matches, unused_max_match_len):
    term_width = self._GetTerminalWidth()

    # Variables set by the completion generator.  They should always exist,
    # because we can't get "matches" without calling that function.
    prefix_pos = self.comp_state['prefix_pos']

    sys.stdout.write('\n')

    self.EraseLines()  # Delete previous completions!
    log('_PrintCandidates %r', subst, file=DEBUG_F)

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

    max_lines = 10 * self.dupes[comp_id]

    # TODO: should we quote these or not?
    if prefix_pos:
      to_display = [m[prefix_pos:] for m in matches]
    else:
      to_display = matches

    # Calculate max length after stripping prefix.
    max_match_len = max(len(m) for m in to_display)

    # Print and go back up.  But we have to ERASE these before hitting enter!
    if self.comp_state.get('DESC'):  # exists and is NON EMPTY
      num_lines = PrintLong(to_display, max_match_len, term_width,
                            max_lines, self.comp_state['DESC'])
    else:
      num_lines = PrintPacked(to_display, max_match_len, term_width,
                              max_lines)

    self._ReturnToPrompt(num_lines+1)
    self.num_lines_last_displayed = num_lines

    self.c_count += 1

  def PrintCandidates(self, *args):
    try:
      self._PrintCandidates(*args)
    except Exception as e:
      traceback.print_exc()

  def PrintMessage(self, msg, *args):
    """
    Print a message below the prompt, and then return to the location on the
    prompt line.
    """
    if args:
      msg = msg % args

    # This will mess up formatting
    assert not msg.endswith('\n'), msg

    sys.stdout.write('\n')

    self.EraseLines()
    log('_PrintMessage %r', msg, file=DEBUG_F)

    # Truncate to terminal width
    max_len = self._GetTerminalWidth() - 2
    if len(msg) > max_len:
      msg = msg[:max_len-5] + ' ... '

    fmt = _BOLD + _BLUE + '%' + str(max_len) + 's' + _RESET
    sys.stdout.write(fmt % msg)
    #sys.stdout.write('\r')  # go back to beginning of line

    sys.stdout.flush()  # required

    self._ReturnToPrompt(num_lines)
    self.num_lines_last_displayed = 1

    self.m_count += 1

  def EraseLines(self):
    """Clear N lines one-by-one.

    Assume the cursor is right below thep rompt:

    demo$ echo hi
    _     <-- HERE

    That's the first line to erase out of N.  After erasing them, return it
    there.
    """
    n = self.num_lines_last_displayed

    log('EraseLines %d (c = %d, m = %d)', n, self.c_count, self.m_count,
        file=DEBUG_F)

    if n == 0:
      return

    for i in xrange(n):
      # 2K would clear the ENTIRE line, but isn't strictly necessary.
      sys.stdout.write('\x1b[0K')
      sys.stdout.write('\x1b[%dB' % 1)  # go down one line

    # Now go back up
    sys.stdout.write('\x1b[%dA' % n)
    sys.stdout.flush()  # Without this, output will look messed up

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


_PS1 = 'demo$ '
_PS2 = '> '  # A different length to test Display


def DoNothing(unused1, unused2):
  pass


class InteractiveLineReader(object):
  """Simplified version of OSH prompt.

  Holds PS1 / PS2 state.
  """
  def __init__(self):
    self.prompt_str = ''
    self.pending_lines = []  # for completion to use
    self.Reset()  # initialize self.prompt_str

    # https://stackoverflow.com/questions/22916783/reset-python-sigint-to-default-signal-handler
    self.orig_handler = signal.getsignal(signal.SIGINT) 
    #log('%s', self.orig_handler)

  def GetLine(self):
    signal.signal(signal.SIGINT, self.orig_handler)  # raise KeyboardInterrupt
    try:
      line = raw_input(self.prompt_str) + '\n'  # newline required
    except KeyboardInterrupt:
      print('^C')
      line = ''
    except EOFError:
      print('^D')  # bash prints 'exit'; mksh prints ^D.
      line = None
    else:
      self.pending_lines.append(line)
    finally:
      # Ignore it usually, so we don't get KeyboardInterrupt in weird places.
      # NOTE: This can't be SIG_IGN, because that affects the child process.
      signal.signal(signal.SIGINT, DoNothing)

    self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
    return line

  def Reset(self):
    self.prompt_str = _PS1
    del self.pending_lines[:]


def MainLoop(reader, display):
  while True:
    line = reader.GetLine()

    # Erase lines before execution, displaying PS2, or exit!
    display.EraseLines()

    #log('got %r', line)
    if line is None:
      break

    if line == '':  # Ctrl-C
      display.Reset()
      reader.Reset()
      continue

    if line.endswith('\\\n'):
      continue

    # Take multiple lines from the reader, simulating the OSH parser.
    cmd, _ = MultiLineCommand(reader.pending_lines)

    os.system(cmd)

    display.Reset()
    reader.Reset()


_COMMANDS = [
    'echo', 'sleep', 'clear', 'slowc', 'many', 'toomany'
]

ECHO_WORDS = [
    'zz', 'foo', 'bar', 'baz', 'spam', 'eggs', 'python', 'perl', 'pearl',
    # To simulate filenames with spaces
    'two words', 'three words here',
]


def LoadFlags(path):
  flags = []
  with open(path) as f:
    for line in f:
      try:
        flag, desc = line.split(None, 1)
        desc = desc.strip()
      except ValueError:
        #log('Error: %r', line)
        #raise
        flag = line.strip()
        desc = None

      # TODO: do something with the description
      flags.append((flag, desc))
  return flags


def main(argv):
  _, term_width = GetTerminalSize()
  fmt = '%' + str(term_width) + 's'

  #msg = "[Oil 0.6.pre11] Type 'help' or visit https://oilshell.org/help/ "
  msg = "For help, type 'help' or visit https://oilshell.org/help/0.6.pre11 "
  print(fmt % msg)

  # Used to store the original line, flag descriptions, etc.
  comp_state = {}

  reader = InteractiveLineReader()
  display = Display(comp_state, reader)

  # Register a callback to receive terminal width changes.
  signal.signal(signal.SIGWINCH, lambda x, y: display.OnWindowChange())

  comp_lookup = {
      'echo': WordsAction(ECHO_WORDS),
      'slowc': WordsAction([str(i) for i in xrange(20)], delay=0.1),
      'many': WordsAction(['--flag%d' % i for i in xrange(50)]),
      'toomany': WordsAction(['--too%d' % i for i in xrange(1000)]),
  }

  flag_dir = argv[1]
  commands = []
  for cmd in os.listdir(flag_dir):
    path = os.path.join(flag_dir, cmd)
    flags = LoadFlags(path)
    comp_lookup[cmd] = FlagsHelpAction(flags)
    commands.append(cmd)

  comp_lookup['__first'] = WordsAction(commands + _COMMANDS)

  # Register a callback to generate completion candidates.
  root_comp = RootCompleter(reader, display, comp_lookup, comp_state)
  readline.set_completer(CompletionCallback(root_comp))

  # We want to parse the line ourselves, rather than use readline's naive
  # delimiter-based tokenization.
  readline.set_completer_delims('')

  # Register a callback to display completions.
  # NOTE: Is this style hard to compile?  Maybe have to expand the args
  # literally.
  readline.set_completion_display_matches_hook(
      lambda *args: display.PrintCandidates(*args)
  )

  readline.parse_and_bind('tab: complete')

  MainLoop(reader, display)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
