#!/usr/bin/python
"""
pyreadline.py
"""
from __future__ import print_function

import readline
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


USE_DELIMS = False
#USE_DELIMS = True


def Words(prefix):
  #log('Words')
  words = ['foo', 'bar', 'baz', 'spam', 'eggs']
  first = 'echo '
  #first = 'echo\\ '  # Test quoting

  if USE_DELIMS:
    pass
  else:
    words = [first + w for w in words]

  #log('words = %s', words)
  for w in words:
    if w.startswith(prefix):
      yield w + ' '


class Callback(object):
  def __init__(self, comp):
    self.comp = comp
    self.iter = None

  # Another idea:
  # Take word_prefix and then slice the whole line?
  # Then parse it?

  # First, Rest, VarName
  # Tilde Sub too

  def Call(self, word_prefix, state):

    #log('Called with %r %r', word_prefix, state)

    if state == 0:
      self.comp['ORIG'] = readline.get_line_buffer()

      # the whole thing
      # get_line_buffer()
      #
      # # parsed
      # get_begidx()  # parsed
      # get_endidx()  # parsed
      #
      # But how do we REPLACE a word

      self.iter = Words(word_prefix)
      #log('init iter %s', self.iter)

    try:
      c = self.iter.next()
    except StopIteration:
      c = None
    #log('-> %r', c)
    return c

  def __call__(self, word_prefix, state):
    try:
      return self.Call(word_prefix, state)
    except Exception as e:
      # Readline swallows exceptions!
      print(e)
      raise


# Hm this hook is useful!  I can strip off the common prefix?
# And I can display flag help?
# Everything is a string, but I can look up help with strings.  Hm this is
# good.
#
# Problem: how do I detect where the bottom of the screen is?

class Display(object):
  def __init__(self, comp):
    self.comp = comp
    self.num_lines_last_displayed = 0

  def __call__(self, subst, matches, longest_match_len):
    if 0:
      log('')
      log('subst = %r', subst)
      log('matches = %s', matches)
      log('longest = %s', longest_match_len)
    print('')

    # Have to delete previous completions!
    ClearLines(self.num_lines_last_displayed)

    # Print and go back up.  But we have to ERASE these before hitting enter!
    for m in matches:
      print(m)
    n = len(matches)
    self.num_lines_last_displayed = n

    # Move up.  Hm this works.  But I need to erase the candidates after
    # hitting enter!
    sys.stdout.write('\x1b[%dA' % (n+1))  # UP

    # Also need to move back to the end of line, before readline?

    #sys.stdout.write('\x1b[%dC' % 4)  # RIGHT
    #sys.stdout.write('\x1b[%dD' % 1)  # RIGHT by prompt

    # PROMPT again
    sys.stdout.write('$ ')
    sys.stdout.write(self.comp['ORIG'])

    # Features here:
    # - TODO: query terminal width
    # - strip common prefixes?  It has to be a whole line?
    #   - maybe you need a hack to associate the unique whole line with
    #     some kind of initial position?
    # - limit the number of matches to 10 or so?
    #   - so then do you need an option to set this limit?  COMPLIMIT?
    #   - what does readline do?


def ClearLines(n):
  if n == 0:
    return

  for i in xrange(n):
    sys.stdout.write('\x1b[0K')  # clear the line
    sys.stdout.write('\x1b[%dB' % 1)  # go down one line

  # Now go back up
  sys.stdout.write('\x1b[%dA' % (n))


# What bash and OSH use.  Should OSH use something else?
READLINE_DELIMS = ' \t\n"\'><=;|&(:'

def main(argv):
  # Unit test

  comp = {}
  readline.set_completer(Callback(comp))

  # OK, if we do this, then we get the whole damn line!!!
  # Then we just return the whole damn line completed?
  # Problem : the displayed completions.  Is there an option to strip
  # common prefix?
  if USE_DELIMS:
    readline.set_completer_delims(READLINE_DELIMS)
  else:
    readline.set_completer_delims('')

  hook = Display(comp)
  readline.set_completion_display_matches_hook(hook)

  readline.parse_and_bind('tab: complete')
  while True:
    try:
      x = raw_input('$ ')
    except EOFError:
      print()
      break
    # Clear lines before printing
    ClearLines(hook.num_lines_last_displayed)
    print(x)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)

