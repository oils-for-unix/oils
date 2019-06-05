"""
old.py

Saving some old code.  mypy --strict doesn't like it!
"""
from __future__ import print_function

import sys


class DynamicTdopParser(TdopParser):
  def __init__(self, *args):
    TdopParser.__init__(self, *args)

    # for precedence tweakins
    # TODO: Don't peek inside the member?  How to represent this in C++?
    self.dynamic_led = dict(self.spec.led_lookup)
    self.stack = []  # saved dynamic_led entries

  def Push(self, token, v):
    """
    Temporarily adjust precedence of a token, or insert a new token.

    In Python, this is used for commas, because sometimes it has greater
    precedence than =, and sometimes less.  For example:

    x, y = x, y
    (x, y) = (x, y)

    vs.

    f(x = 1, y = 1)

    This is NOT:
    f(x = (1, y )= 1)

    So inside f(x,y), (t1, t2), [i, j], {i:1, i:2} we tweak it.

    Why is it used for "in"?

    for x in y: pass
    # NOT VALID
    for (x in y) in y:

    [ x for x+1 in y ]
    [ x for x in y ]

    I think INSTEAD of tweak, we need something that's not an expression?  Do
    this later.
    """
    self.stack.append((token, self.dynamic_led[token]))  # save old value
    if v:
      self.dynamic_led[token] = self.spec.LookupLed(token)
    else:
      self.dynamic_led[token] = LeftInfo()

  def Pop(self):
    """ Restore dynamic_led after p.Push(). """
    k, v = self.stack.pop()
    self.dynamic_led[k] = v

  def _Led(self, token):
    return self.dynamic_led[token]


#
# From osh/braces.py
#


# Possible optmization for later:
def _TreeCount(tree_word):
  """Count output size for allocation purposes.

  We can count the number of words expanded into, and the max number of parts
  in a word.

  Every word can have a differnt number of parts, e.g. -{'a'b,c}- expands into
  words of 4 parts, then 3 parts.
  """
  # TODO: Copy the structure of _BraceExpand and _BraceExpandOne.
  for part in tree_word.parts:
    if isinstance(part, word_part__BracedTuple):
      for word in part.words:
        pass
  num_results = 2
  max_parts = 5
  return num_results, max_parts


def _Cartesian(tuples):
  if len(tuples) == 1:
    for x in tuples[0]:
      yield (x,)
  else:
    for x in tuples[0]:
      for y in _Cartesian(tuples[1:]):
        yield (x,) + y  # join tuples


def main(argv):
  for t in _Cartesian([('a', 'b')]):
    print(t)
  print('--')
  for t in _Cartesian([('a', 'b'), ('c', 'd', 'e'), ('f', 'g')]):
    print(t)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
