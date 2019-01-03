#!/usr/bin/python
"""
pyreadline.py

Let's think of the interactive shell prompt roughly as a state machine.

Inputs:
  - entering a line that's incomplete
  - entering a line that finishes a command
  - hitting TAB for complete
  - Ctrl-C to cancel a command in progress!  (make sure to delete stuff here)
  - Ctrl-C to cancel a completion in progress, for slow completions.
    - NOTE: if there are blocking NFS calls, completion should go in a
      thread/process?
  - EOF: Ctrl-D on an EMPTY line.
    (Ctrl-D on a non-empty line behaves just like hitting enter)
  - Terminal width change?  Or do we poll here?

Actions:
  - Display completions
    - Depends on terminal width.  When do we query that?
  - Display a 1-line message showing lack of completions ('no variables that
    begin with $')
  - Execute a command
  - Clear N lines below the prompt (has to happen a lot)
  - Exit shell

State:
  1. The prompt: PS1 or PS2  
  2. The number of lines to clear next
  3. The completion that is in progress.  The 'compopt' builtin affects this.

  NOTE: EraseLines() uses #2.

NOTES:
  - We don't care about terminal resizes, but we care about terminal width.

TODO for this demo:
  - reset terminal width on window change.  Or just query it before displaying
    anything?
  - simulate FileSystemAction on 'ls'
  - use PrintMessage() for progress (as well as for 'no completions')
  - If there are too many completions, display 5 or 10 rows, and then hit a key to see more?
    - this is better than zsh prompt
  - show descriptions of flags.  comp_state needs a separate dictionary then?
  - experiment with ordering?  You would have to disable readline sorting

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

#from core import ui


if 0:
  DEBUG_F = open('_tmp/demo-debug', 'w')
else:
  DEBUG_F = open('/dev/null', 'w')


def log(msg, *args, **kwargs):
  if args:
    msg = msg % args
  f = kwargs.get('f', sys.stderr)
  print(msg, file=f)
  f.flush()


# TODO: This should be implemented in C to avoid dependencies.
import fcntl
import struct
import termios


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
  def __init__(self, words, delay=None):
    self.words = words
    self.delay = delay

  def Matches(self, prefix):
    for w in self.words:
      if w.startswith(prefix):
        if self.delay is not None:
          time.sleep(self.delay)

        yield w


class RootCompleter(object):

  def __init__(self, display, comp_lookup, comp_state):
    """
    Args:
      comp_state: Mutated
    """
    self.display = display
    self.comp_lookup = comp_lookup
    self.comp_state = comp_state

  def Matches(self, comp):
    line = comp['line']
    self.comp_state['ORIG'] = line

    # Calculate the portion to complete

    i = line.rfind(' ')  # the last space
    if i == -1:  # FIRST WORD state, no prefix
      pos = 0
      to_complete = line
      prefix = ''
      # List of commands we know about
      completer = WordsAction(_COMMANDS)
    else:
      pos = i+1  # beginning of word to complete
      to_complete = line[pos:]
      prefix = line[:pos]

      # left-most space might be different than right-most
      j = line.find(' ')
      assert j != -1
      first = line[:j]

      # TODO: fallback
      completer = self.comp_lookup.get(first, _NULL_ACTION)

    # For the Display callback to look at
    self.comp_state['prefix_pos'] = pos

    i = 0
    start_time = time.time()
    for c in completer.Matches(to_complete):
      yield prefix + c + ' '
      # TODO: avoid calling time() so much?
      elapsed_ms = (time.time() - start_time) * 1000

      # NOTE: Ctrl-C works here!  You only get the first 5 candidates.
      # only print after 200ms
      i += 1
      if elapsed_ms > 200:
        plural = '' if i == 1 else 'es'
        #self.status_line.Write(
        #    '... %d match%s for %r in %d ms (Ctrl-C to cancel)', i,
        #    plural, line, elapsed_ms)

    if i == 0:
      self.display.PrintMessage('(no matches for %r)', line)
      pass


class CompletionCallback(object):

  def __init__(self, status_line, root_comp):
    #self.status_line = status_line
    self.root_comp = root_comp
    self.iter = None

  def Call(self, word_prefix, state):
    """Generate completions."""

    #log('Called with %r %r', word_prefix, state)
    if state == 0:  # initial completion
      # Save for later
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


def PrintPacked(matches, longest_match_len, term_width):
  w = longest_match_len + 2  # 2 spaces between each
  num_per_line = max(1, (term_width-2) // w)  # don't print in first or last column
  fmt = '%-' + str(w) + 's'
  num_lines = 0

  sys.stdout.write(' ')  # 1 space gutter
  remainder = num_per_line - 1
  for i, m in enumerate(matches):
    sys.stdout.write(fmt % m)
    if i % num_per_line == remainder:
      sys.stdout.write('\n ')  # 1 space gutter
      num_lines += 1

  # Write last line break, unless it came out exactly.
  if i % num_per_line != 0:
    sys.stdout.write('\n')
    num_lines += 1

  return num_lines


class Display(object):
  """Hook to display completion candidates.

  This is useful for:
  - stripping off the common prefix according to OUR rules
  - display builtin and flag help

  Problem: how do I detect where the bottom of the screen is?

  Features here:
  - limit the number of matches to 10 or so?
    - so then do you need an option to set this limit?  COMPLIMIT?
    - what does readline do?

  BUG: EraseLines() sometimes doesn't get called.  In particular when readline
  completes  something.
  """
  def __init__(self, status_line, comp_state, reader, term_width, max_lines=5):
    #self.status_line = status_line
    self.comp_state = comp_state
    self.reader = reader
    self.term_width = term_width
    self.max_lines = max_lines  # TODO: Respect this!
    self.num_lines_last_displayed = 0

    self.c_count = 0
    self.m_count = 0

  def Reset(self):
    """Call this in between commands."""
    self.num_lines_last_displayed = 0

  def _PrintCandidates(self, subst, matches, unused_longest_match_len):

    # These are set by the completion generator.  They should always exist,
    # because we can't get "matches" without calling that function.

    orig_len = len(self.comp_state['ORIG'])
    prefix_pos = self.comp_state['prefix_pos']

    if 0:
      log('')
      log('subst = %r', subst)
      log('matches = %s', matches)
      log('longest = %s', longest_match_len)
    print('')

    # Have to delete previous completions!
    #self.status_line.Write('display: erasing %d lines', self.num_lines_last_displayed)
    self.EraseLines()
    log('_PrintCandidates %r', subst, f=DEBUG_F)

    # TODO: should we quote these or not?
    if prefix_pos:
      to_display = [m[prefix_pos:] for m in matches]
    else:
      to_display = matches

    # Calculate our own
    longest_match_len = max(len(m) for m in to_display)

    #sys.stdout.write('\x1b[s')  # SAVE

    # Print and go back up.  But we have to ERASE these before hitting enter!
    num_lines = PrintPacked(to_display, longest_match_len, self.term_width)

    self.num_lines_last_displayed = num_lines

    #sys.stdout.write('\x1b[u')  # RESTORE

    if 1:
      # Move up.  Hm this works.  But I need to erase the candidates after
      # hitting enter!
      sys.stdout.write('\x1b[%dA' % (num_lines+1))  # UP

      # Also need to move back to the end of line, before readline?
      n = orig_len + len(self.reader.prompt_str)  # maybe change between PS1 and PS2
      sys.stdout.write('\x1b[%dC' % n)  # RIGHT

    self.c_count += 1

  def PrintCandidates(self, *args):
    try:
      self._PrintCandidates(*args)
    except Exception as e:
      import traceback
      traceback.print_exc()

  def PrintMessage(self, msg, *args):
    """
    Print a message below the prompt, and then return to the location on the
    prompt line.
    """
    orig_len = len(self.comp_state['ORIG'])

    if args:
      msg = msg % args

    # This will mess up formatting
    assert not msg.endswith('\n'), msg

    # hack to account for what readline does NOT do?
    # demo$ echo <TAB>
    # You get \r\n if there are completions, but none if there aren't?
    # I found this using 'script'.
    sys.stdout.write('\r\n')

    self.EraseLines()
    log('_PrintMessage %r', msg, f=DEBUG_F)

    # Truncate to terminal width
    max_len = self.term_width - 2
    if len(msg) > max_len:
      msg = msg[:max_len-5] + ' ... '

    fmt = '%' + str(max_len) + 's'
    sys.stdout.write(fmt % msg)
    sys.stdout.write('\r')  # go back to beginning of line

    # TODO: Save and restore position instead of doing this junk
    sys.stdout.write('\x1b[1A')  # 1 line up
    n = orig_len + len(self.reader.prompt_str)  # maybe change between PS1 and PS2
    sys.stdout.write('\x1b[%dC' % n)  # RIGHT
    sys.stdout.flush()

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
        f=DEBUG_F)

    if n == 0:
      return

    sys.stdout.write('\x1b[s')  # SAVE

    for i in xrange(n):
      # 2K would clear the ENTIRE line, but isn't strictly necessary.
      sys.stdout.write('\x1b[0K')
      sys.stdout.write('\x1b[%dB' % 1)  # go down one line

    sys.stdout.write('\x1b[u')  # RESTORE
    sys.stdout.flush()  # Without this, output will look messed up

    if 0:
      # Now go back up
      sys.stdout.write('\x1b[%dA' % n)
      sys.stdout.flush()  # Without this, output will look messed up


_PS1 = 'demo$ '
_PS2 = '> '  # A different length to test Display


def DoNothing(unused_frame, unused):
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
      #pass

    self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
    return line

  def Reset(self):
    self.prompt_str = _PS1
    del self.pending_lines[:]


def MainLoop(status_line, reader, display):
  while True:
    line = reader.GetLine()

    # Erase lines before execution, displaying PS2, or exit!
    #status_line.Write('loop: erasing %d lines', display.num_lines_last_displayed)
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

    parts = []
    for line in reader.pending_lines:
      if line.endswith('\\\n'):
        line = line[:-2]
      parts.append(line)
    cmd = ''.join(parts)

    os.system(cmd)

    display.Reset()
    reader.Reset()

_COMMANDS = ['echo', 'sleep', 'ls', 'clear', 'slowc', 'many']

ECHO_WORDS = [
    'zz', 'foo', 'bar', 'baz', 'spam', 'eggs', 'python', 'perl', 'pearl',
    # To simulate filenames with spaces
    'two words', 'three words here'
]


def main(argv):
  height, width = GetTerminalSize()
  #log('width = %d, height = %d', width, height)

  # Hm this can conflict with completion.  Display has to be aware of
  # it.
  # It also conflicts with the text of 'ls' and such!   Would have to delete it
  # before every command.
  #status_line = ui.StatusLine(row_num=height-1, width=width-1)
  status_line = None
  #status_line.Write('height = %d', height)

  fmt = '%' + str(width) + 's'
  #msg = "[Oil 0.6.pre11] Type 'help' or visit https://oilshell.org/help/ "
  msg = "For help, type 'help' or visit https://oilshell.org/help/0.6.pre11 "
  print(fmt % msg)

  # Right now this is used to set the original command.
  comp_state = {}

  reader = InteractiveLineReader()
  display = Display(status_line, comp_state, reader, width)

  comp_lookup = {
      'echo': WordsAction(ECHO_WORDS),
      'slowc': WordsAction([str(i) for i in xrange(20)], delay=0.1),
      'many': WordsAction(['--flag%d' % i for i in xrange(100)]),
  }
   
  root_comp = RootCompleter(display, comp_lookup, comp_state)
  readline.set_completer(CompletionCallback(status_line, root_comp))

  # If we do this, we get the whole line.  Then we need to use Display
  # to get it.
  readline.set_completer_delims('')


  # NOTE: Is this style hard to compile?  Maybe have to expand the args literally.
  readline.set_completion_display_matches_hook(
      lambda *args: display.PrintCandidates(*args)
  )

  readline.parse_and_bind('tab: complete')

  MainLoop(status_line, reader, display)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
