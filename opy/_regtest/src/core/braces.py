#!/usr/bin/env python
from __future__ import print_function
"""
braces.py

NOTE: bash implements brace expansion in the braces.c file (835 lines).  It
uses goto!

Possible optimization flags for CompoundWord:
- has Lit_LBrace, LitRBrace -- set during word_parse phase
  - it if has both, then do _BraceDetect
- has BracedAltPart -- set during _BraceDetect
  - if it does, then do the expansion
- has Lit_Star, ?, [ ] -- globbing?
  - but after expansion do you still have those flags?
"""

import sys

from osh.meta import Id
from osh.meta import ast

word_part_e = ast.word_part_e
word_e = ast.word_e


class _StackFrame(object):
  def __init__(self, cur_parts):
    self.cur_parts = cur_parts
    self.alt_part = ast.BracedAltPart()
    self.saw_comma = False


def _BraceDetect(w):
  """
  Args:
    CompoundWord

  Returns:
    CompoundWord or None?

  Another option:

  Grammar:

    # an alternative is a literal, possibly empty, or another brace_expr

    part = <any part except LiteralPart>

    alt = part* | brace_expr

    # a brace_expr is group of at least 2 braced and comma-separated
    # alternatives, with optional prefix and suffix.
    brace_expr = part* '{' alt ',' alt (',' alt)* '}' part*

  Problem this grammar: it's not LL(1) 
  Is it indirect left-recursive?
  What's the best way to handle it?  LR(1) parser?

  Iterative algorithm:

  Parse it with a stack?
    It's a stack that asserts there is at least one , in between {}

  Yeah just go through and when you see {, push another list.
  When you get ,  append to list
  When you get } and at least one ',', append o list
  When you get } without, then pop

  If there is no matching }, then abort with error

  if not balanced, return error too?
  """
  # Errors:
  # }a{    - stack depth dips below 0
  # {a,b}{ - Stack depth doesn't end at 0
  # {a}    - no comma, and also not an numeric range

  cur_parts = []
  stack = []

  found = False

  for i, part in enumerate(w.parts):
    append = True
    if part.tag == word_part_e.LiteralPart:
      id_ = part.token.id
      if id_ == Id.Lit_LBrace:
        # Save prefix parts.  Start new parts list.
        new_frame = _StackFrame(cur_parts)
        stack.append(new_frame)
        cur_parts = []
        append = False
        found = True  # assume found, but can early exit with None later

      elif id_ == Id.Lit_Comma:
        # Append a new alternative.
        #print('*** Appending after COMMA', cur_parts)

        # NOTE: Should we allow this:
        # ,{a,b}
        # or force this:
        # \,{a,b}
        # ?  We're forcing braces right now but not commas.
        if stack:
          stack[-1].saw_comma = True

          stack[-1].alt_part.words.append(ast.CompoundWord(cur_parts))
          cur_parts = []  # clear
          append = False

      elif id_ == Id.Lit_RBrace:
        # TODO:
        # - Detect lack of , -- abort the whole thing
        # - Detect {1..10} and {1..10..2}
        #   - bash and zsh only -- this is NOT implemented by mksh
        #   - Use a regex on the middle part:
        #     - digit+ '..' digit+  ( '..' digit+ )?
        # - Char ranges are bash only!
        #
        # ast.BracedIntRangePart()
        # ast.CharRangePart()

        if not stack:  # e.g. echo }  -- unbalancd {
          return None
        if not stack[-1].saw_comma:  # {foo} is not a real alternative
          return None
        stack[-1].alt_part.words.append(ast.CompoundWord(cur_parts))

        frame = stack.pop()
        cur_parts = frame.cur_parts
        cur_parts.append(frame.alt_part)
        append = False

    if append:
      cur_parts.append(part)

  if len(stack) != 0:
    return None

  if found:
    return ast.BracedWordTree(cur_parts)
  else:
    return None


def BraceDetectAll(words):
  out = []
  for w in words:
    #print(w)
    brace_tree = _BraceDetect(w)
    if brace_tree:
      out.append(brace_tree)
    else:
      out.append(w)
  return out


# Possible optimization for later:
def _TreeCount(tree_word):
  """Count output size for allocation purposes.

  We can count the number of words expanded into, and the max number of parts
  in a word.

  Every word can have a different number of parts, e.g. -{'a'b,c}- expands into
  words of 4 parts, then 3 parts.
  """
  # TODO: Copy the structure of _BraceExpand and _BraceExpandOne.
  for part in tree_word.parts:
    if part.tag == word_part_e.BracedAltPart:
      for word in part.words:
        pass
  num_results = 2
  max_parts = 5
  return num_results, max_parts


def _BraceExpandOne(parts, first_alt_index, suffixes):
  """Helper for _BraceExpand.

  Args:
    parts: input parts
    first_alt_index: index of the first BracedAltPart
    suffixes: List of suffixes to append.
  """
  out = []

  # Need to call _BraceExpand on each of the inner words too!
  first_alt = parts[first_alt_index]
  expanded_alts = []
  for w in first_alt.words:
    expanded_alts.extend(_BraceExpand(w.parts))

  prefix = parts[ : first_alt_index]
  for alt_parts in expanded_alts:
    for suffix in suffixes:
      out_parts = []
      out_parts.extend(prefix)
      out_parts.extend(alt_parts)
      out_parts.extend(suffix)
      # TODO: Do we need to preserve flags?
      out.append(out_parts)
  return out


def _BraceExpand(parts):
  num_alts = 0
  first_alt_index = -1
  for i, part in enumerate(parts):
    if part.tag == word_part_e.BracedAltPart:
      num_alts += 1
      if num_alts == 1:
        first_alt_index = i
      elif num_alts == 2:
        break  # don't need to count anymore

  # NOTE: There are TWO recursive calls here, not just one -- one for
  # nested {}, and one for adjacent {}.  Thus it's hard to do iteratively.
  if num_alts == 0:
    return [parts]

  elif num_alts == 1:
    suffix = parts[first_alt_index+1 : ]
    return _BraceExpandOne(parts, first_alt_index, [suffix])

  else:
    # Now call it on the tail
    tail_parts = parts[first_alt_index+1 : ]
    suffixes = _BraceExpand(tail_parts)  # recursive call
    return _BraceExpandOne(parts, first_alt_index, suffixes)


def BraceExpandWords(words):
  out = []
  for w in words:
    if w.tag == word_e.BracedWordTree:
      parts_list = _BraceExpand(w.parts)
      out.extend(ast.CompoundWord(p) for p in parts_list)
    else:
      out.append(w)
  return out


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
