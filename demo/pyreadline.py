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


def Words(prefix):
  #log('Words')
  words = ['foo', 'bar', 'baz', 'spam', 'eggs']
  first = 'echo '
  words = [first + w for w in words]
  #log('words = %s', words)
  for w in words:
    if w.startswith(prefix):
      yield w + ' '


class Callback(object):
  def __init__(self):
    self.iter = None

  # Another idea:
  # Take word_prefix and then slice the whole line?
  # Then parse it?

  # First, Rest, VarName
  # Tilde Sub too

  def Call(self, word_prefix, state):
    #log('Called with %r %r', word_prefix, state)

    if state == 0:
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

def Display(subst, matches, longest_match_len):
  log('subst = %s', subst)
  log('matches = %s', matches)
  log('longest = %s', longest_match_len)


def main(argv):
  # Unit test

  readline.set_completer(Callback())
  #readline.set_completer_delims(' ')

  # OK, if we do this, then we get the whole damn line!!!
  # Then we just return the whole damn line completed?
  # Problem : the displayed completions.  Is there an option to strip
  # common prefix?
  readline.set_completer_delims('')

  readline.set_completion_display_matches_hook(Display)


  readline.parse_and_bind('tab: complete')
  while True:
    try:
      x = raw_input('$ ')
    except EOFError:
      print()
      break
    print(x)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)

