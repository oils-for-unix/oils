#!/usr/bin/env python
"""
braces.py - Implementation of {andy,bob}@example.com

NOTE: bash implements brace expansion in the braces.c file (835 lines).  It
uses goto!

Possible optimization flags for CompoundWord:
- has Lit_LBrace, LitRBrace -- set during word_parse phase
  - it if has both, then do _BraceDetect
- has BracedTuple -- set during _BraceDetect
  - if it does, then do the expansion
- has Lit_Star, ?, [ ] -- globbing?
  - but after expansion do you still have those flags?
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import (
    word, word_t, word__CompoundWord, word__BracedWordTree,
    word_part, word_part_t,
    word_part__BracedTuple, word_part__BracedRange,
    word_part__LiteralPart,
    token,
)
from asdl import const
#from core.util import log
from frontend.match import BRACE_RANGE_LEXER

from typing import List, Optional, Iterator, Tuple


class _StackFrame(object):
  def __init__(self, cur_parts):
    # type: (List[word_part_t]) -> None
    self.cur_parts = cur_parts
    self.alt_part = word_part.BracedTuple()
    self.saw_comma = False


# The brace language has no syntax errors!  But we still need to abort the
# parse.
class _NotARange(Exception):
  pass


class _RangeParser(object):
  """Grammar for ranges:

    step = Dots Int
    int_range = Int Dots Int step?
    char_range = Char Dots Char step?
    range = (int_range | char_range) Eof  # ensure no extra tokens!
  """
  def __init__(self, lexer):
    # type: (Iterator[Tuple[Id_t, str]]) -> None
    self.lexer = lexer
    self.token_type = None  # type: Id_t
    self.token_val = ''

  def _Next(self):
    # type: () -> None
    """Move to the next token."""
    try:
      self.token_type, self.token_val = self.lexer.next()
    except StopIteration:
      self.token_type = Id.Range_Eof
      self.token_val = ''

  def _Eat(self, token_type):
    # type: (Id_t) -> str
    if self.token_type != token_type:
      raise _NotARange('Expected %s, got %s' % (token_type, self.token_type))
    val = self.token_val
    self._Next()
    return val

  def _ParseStep(self):
    # type: () -> int
    self._Next()  # past Dots
    return int(self._Eat(Id.Range_Int))

  def _ParseRange(self, range_kind):
    # type: (Id_t) -> word_part__BracedRange
    start = self.token_val
    self._Next()  # past Char

    self._Eat(Id.Range_Dots)
    end = self._Eat(range_kind)

    part = word_part.BracedRange(range_kind, start, end)

    if self.token_type == Id.Range_Dots:
      part.step = self._ParseStep()

    return part

  def Parse(self):
    # type: () -> word_part__BracedRange
    self._Next()

    # TODO:
    # - Check that steps go in the right direction
    # - Check that cases are equal for char range

    if self.token_type in (Id.Range_Int, Id.Range_Char):
      part = self._ParseRange(self.token_type)
    else:
      raise _NotARange()

    # prevent unexpected trailing tokens
    self._Eat(Id.Range_Eof)
    return part


def _RangePartDetect(token):
  # type: (token) -> Optional[word_part_t]
  """Parse the token and return a new word_part if it looks like a range."""
  lexer = BRACE_RANGE_LEXER.Tokens(token.val)
  p = _RangeParser(lexer)
  try:
    part = p.Parse()
  except _NotARange as e:
    return None
  part.spids.append(token.span_id)  # Propagate location info
  return part


def _BraceDetect(w):
  # type: (word__CompoundWord) -> Optional[word__BracedWordTree]
  """Return a new word if the input word looks like a brace expansion.

  e.g. {a,b} or {1..10..2} (TODO)
  Do we want to accept {01..02} ?  zsh does make some attempt to do this too.

  NOTE: This is an iterative algorithm that uses a stack.  The grammar-based
  approach didn't seem natural.

  It's not LL(1) because of 'part*'.  And not LL(k) even?  Maybe it be handled
  with an LR parser?  In any case the imperative algorithm with 'early return'
  for a couple cases is fairly simple.

  Grammar:
    # an alternative is a literal, possibly empty, or another brace_expr

    part = <any part except LiteralPart>
    alt = part* | brace_expr

    # a brace_expr is group of at least 2 braced and comma-separated
    # alternatives, with optional prefix and suffix.
    brace_expr = part* '{' alt ',' alt (',' alt)* '}' part*
  """
  # Errors:
  # }a{    - stack depth dips below 0
  # {a,b}{ - Stack depth doesn't end at 0
  # {a}    - no comma, and also not an numeric range

  cur_parts = []  # type: List[word_part_t]
  stack = []  # type: List[_StackFrame]

  found = False

  for i, part in enumerate(w.parts):
    append = True
    if isinstance(part, word_part__LiteralPart):
      id_ = part.token.id
      if id_ == Id.Lit_LBrace:
        # Save prefix parts.  Start new parts list.
        new_frame = _StackFrame(cur_parts)
        stack.append(new_frame)
        cur_parts = []
        append = False
        found = True  # assume found, but can early exit with None later

      elif id_ == Id.Lit_Comma:  # Append a new alternative.

        # NOTE: Should we allow this:
        # ,{a,b}
        # or force this:
        # \,{a,b}
        # ?  We're forcing braces right now but not commas.
        if stack:
          stack[-1].saw_comma = True

          stack[-1].alt_part.words.append(word.CompoundWord(cur_parts))
          cur_parts = []  # clear
          append = False

      elif id_ == Id.Lit_RBrace:
        # TODO:
        # - Detect {1..10} and {1..10..2}
        #   - bash and zsh only -- this is NOT implemented by mksh
        #   - Use a regex on the middle part:
        #     - digit+ '..' digit+  ( '..' digit+ )?
        #     - This relies on the fact that 0-9 \. and \- are in Lit_Chars,
        #       which I think is OK.
        # - Char ranges are bash only!
        #
        # word_part.BracedIntRangePart()
        # word_part.CharRangePart()

        if not stack:  # e.g. echo {a,b}{  -- unbalanced {
          return None  # early return

        #log('stack[-1]: %s', stack[-1])
        #log('cur_parts: %s', cur_parts)
        range_part = None
        if len(cur_parts) == 1:  # only allow {1..3}, not {a,1..3}
          # It must be ONE part.  For example, -1..-100..-2 is initially
          # lexed as a single Lit_Chars token.
          part = cur_parts[0]
          if (isinstance(part, word_part__LiteralPart) and
              part.token.id == Id.Lit_Chars):
            range_part = _RangePartDetect(part.token)
            if range_part:
              frame = stack.pop()
              cur_parts = frame.cur_parts
              cur_parts.append(range_part)
              append = False

        if not range_part:
          if not stack[-1].saw_comma:  # {foo} is not a real alternative
            return None  # early return

          stack[-1].alt_part.words.append(word.CompoundWord(cur_parts))

          frame = stack.pop()
          cur_parts = frame.cur_parts
          cur_parts.append(frame.alt_part)
          append = False

    if append:
      cur_parts.append(part)

  if len(stack) != 0:
    return None

  if found:
    return word.BracedWordTree(cur_parts)
  else:
    return None


def BraceDetectAll(words):
  # type: (List[word__CompoundWord]) -> List[word_t]
  """Return a new list of words, possibly with BracedWordTree instances."""
  out = []  # type: List[word_t]
  for w in words:
    #print(w)
    brace_tree = _BraceDetect(w)
    if brace_tree:
      out.append(brace_tree)
    else:
      out.append(w)
  return out


def _RangeStrings(part):
  # type: (word_part__BracedRange) -> List[str]
  if part.kind == Id.Range_Int:
    if part.step == const.NO_INTEGER:
      step = 1 if part.start < part.end else -1
    else:
      step = part.step
    nums = []

    n = int(part.start)
    end = int(part.end)
    if step > 0:
      while True:
        nums.append(n)
        n += step
        if n > end:
          break
    else:
      while True:
        nums.append(n)
        n += step
        if n < end:
          break

    return [str(i) for i in nums]

  else:  # Id.Range_Char
    if part.step == const.NO_INTEGER:
      step = 1 if part.start < part.end else -1
    else:
      step = part.step
    chars = []

    n = ord(part.start)
    ord_end = ord(part.end)
    if step > 0:
      while True:
        chars.append(chr(n))
        n += step
        if n > ord_end:
          break
    else:
      while True:
        chars.append(chr(n))
        n += step
        if n < ord_end:
          break

    return chars


def _ExpandPart(parts,  # type: List[word_part_t]
                 first_alt_index,  # type: int
                 suffixes,  # type: List[List[word_part_t]]
                 ):
  # type: (...) -> List[List[word_part_t]]
  """Mutually recursive with _BraceExpand.

  Args:
    parts: input parts
    first_alt_index: index of the first BracedTuple
    suffixes: List of suffixes to append.
  """
  out = []

  prefix = parts[ : first_alt_index]
  expand_part = parts[first_alt_index]

  if isinstance(expand_part, word_part__BracedTuple):
    # Call _BraceExpand on each of the inner words too!
    expanded_alts = []  # type: List[List[word_part_t]]
    for w in expand_part.words:
      assert isinstance(w, word__CompoundWord)  # for MyPy
      expanded_alts.extend(_BraceExpand(w.parts))

    for alt_parts in expanded_alts:
      for suffix in suffixes:
        out_parts = []  # type: List[word_part_t]
        out_parts.extend(prefix)
        out_parts.extend(alt_parts)
        out_parts.extend(suffix)
        out.append(out_parts)

  elif isinstance(expand_part, word_part__BracedRange):
    # Not mutually recursive with _BraceExpand
    strs = _RangeStrings(expand_part)
    for s in strs:
      for suffix in suffixes:
        out_parts_ = []  # type: List[word_part_t]
        out_parts_.extend(prefix)
        # Preserve span_id from the original
        t = token(Id.Lit_Chars, s, expand_part.spids[0])
        out_parts_.append(word_part.LiteralPart(t))
        out_parts_.extend(suffix)
        out.append(out_parts_)

  else:
    raise AssertionError

  return out


def _BraceExpand(parts):
  # type: (List[word_part_t]) -> List[List[word_part_t]]
  """Mutually recursive with _ExpandPart."""
  num_alts = 0
  first_alt_index = -1
  for i, part in enumerate(parts):
    if isinstance(part, (word_part__BracedTuple, word_part__BracedRange)):
      num_alts += 1
      if num_alts == 1:
        first_alt_index = i
      elif num_alts == 2:
        break  # don't need to count anymore

  # NOTE: There are TWO recursive calls here, not just one -- one for
  # nested {}, and one for adjacent {}.  This is hard to do iteratively.
  if num_alts == 0:
    return [parts]

  elif num_alts == 1:
    suffix = parts[first_alt_index+1 : ]
    return _ExpandPart(parts, first_alt_index, [suffix])

  else:
    # Now call it on the tail
    tail_parts = parts[first_alt_index+1 : ]
    suffixes = _BraceExpand(tail_parts)  # recursive call
    return _ExpandPart(parts, first_alt_index, suffixes)


def BraceExpandWords(words):
  # type: (List[word__CompoundWord]) -> List[word__CompoundWord]
  out = []  # type: List[word__CompoundWord]
  for w in words:
    if isinstance(w, word__BracedWordTree):
      parts_list = _BraceExpand(w.parts)
      out.extend(word.CompoundWord(p) for p in parts_list)
    else:
      out.append(w)
  return out
