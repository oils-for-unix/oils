#!/usr/bin/python
"""
legacy.py

Nice blog post on the complexity/corner cases/difering intuition of splitting
strings:

https://chriszetter.com/blog/2017/10/29/splitting-strings/

python-dev doesn't want to touch it anymore!

Other notes:
- How does this compare to awk -F?
- re.split() ?  This appears not to work.
"""

import re

from core import runtime
from core import util

value_e = runtime.value_e
span_e = runtime.span_e
log = util.log


DEFAULT_IFS = ' \t\n'


class CompletionSplitter:
  def __init__(self):
    pass
  
  def SplitForWordEval(self, s):
    # Return a span that is the whole thing?
    # Honestly do I even need this?
    return (False, len(s))

  # NOTE: Doesn't need to implement SplitForRead


# TODO:
#
# Do we have different splitters?  Awk splitter might be useful.  Regex
# splitter later.  CSV splitter?  TSV?  the TSV one transforms?  Beacuse of
# \u0065 in JSON.  I guess you can have another kind of slice -- a
# LiteralSlice.
#
#
# with SPLIT_REGEX = / digit+ / {
#   echo $#  
#   echo $len(argv)
#   echo $1 $2
#   echo @argv
# }
#
# Yes this is nice.  How does perl do it?


def _SpansToParts(s, spans):
  """Helper for SplitForWordEval."""
  parts = []
  start_index = 0

  # If the last span was black, and we get a backslash, set join_next to merge
  # two black spans.
  join_next = False
  last_span_was_black = False

  for span_type, end_index in spans:
    if span_type == span_e.Black:
      if parts and join_next:
        parts[-1] += s[start_index:end_index]
        join_next = False
      else:
        parts.append(s[start_index:end_index])
      last_span_was_black = True

    elif span_type == span_e.Backslash:
      if last_span_was_black:
        join_next = True
      last_span_was_black = False

    else:
      last_span_was_black = False

    start_index = end_index

  return parts


class RootSplitter(object):
  """ A polymorphic interface to field splitting.
  
  It respects a STACK of IFS values, for example:

  echo $x  # uses default shell IFS
  IFS=':' myfunc  # new splitter
  echo $x  # uses default shell IFS again.
  """

  def __init__(self, mem):
    self.mem = mem
    # Split into (ifs_whitespace, ifs_other)
    self.splitters = {}  # IFS value -> splitter instance

  def _GetSplitter(self):
    """Based on the current stack frame, get the splitter."""
    val = self.mem.GetVar('IFS')
    if val.tag == value_e.Undef:
      ifs = ''
    elif val.tag == value_e.Str:
      ifs = val.s
    else:
      # TODO: Raise proper error
      raise AssertionError("IFS shouldn't be an array")

    try:
      sp = self.splitters[ifs]
    except KeyError:
      # Figure out what kind of splitter we should instantiate.

      ifs_whitespace = ''
      ifs_other = ''
      for c in ifs:
        if c in ' \t\n':  # Happens to be the same as DEFAULT_IFS
          ifs_whitespace += c
        else:
          ifs_other += c

      sp = IfsSplitter(ifs_whitespace, ifs_other)

      # NOTE: Technically, we could make the key more precise.  IFS=$' \t' is
      # the same as IFS=$'\t '.  But most programs probably don't do that, and
      # everything should work in any case.
      self.splitters[ifs] = sp

    return sp

  def Escape(self, s):
    """Escape IFS chars."""
    sp = self._GetSplitter()
    return sp.Escape(s)

  def SplitForWordEval(self, s):
    """Split the string into slices, some of which are marked ignored.

    IGNORED can be used for two reasons:
    1. The slice is a delimiter.
    2. The slice is a a backslash escape.
    
    Example: If you have one\:two, then there are four slices.  Only the
    backslash one is ignored.  In 'one:two', then you have three slices.  The
    colon is ignored.

    Args:
      allow_escape, whether \ can escape IFS characters and newlines.

    Returns:
      Array of (ignored Bool, start_index Int) tuples.
    """
    sp = self._GetSplitter()
    spans = sp.Split(s, True)
    return _SpansToParts(s, spans)

  def SplitForRead(self, line, allow_escape):
    sp = self._GetSplitter()
    return sp.Split(line, allow_escape)


class _BaseSplitter(object):
  def __init__(self, escape_chars):
    # Backslash is always escaped
    self.escape_chars = escape_chars + '\\'

  # NOTE: This is pretty much the same as GlobEscape.
  def Escape(self, s):
    escaped = ''
    for c in s:
      if c in self.escape_chars:
        escaped += '\\'
      escaped += c
    return escaped


# TODO: Used this when IFS='' or IFS isn't set?  This is the fast path for Oil!

class NullSplitter(_BaseSplitter):

  def __init__(self, ifs_whitespace):
    _BaseSplitter.__init__(self, ifs_whitespace)
    self.ifs_whitespace = ifs_whitespace

  def Split(self, s, allow_escape):
    raise NotImplementedError


# IFS splitting is complicated in general.  We handle it with three concepts:
#
# - CH_* - Kinds of characters (edge labels)
# - ST_* - States (node labels)
# - Actions: EMIT, etc.
#
# The Split() loop below classifies characters, follows state transitions, and
# emits spans.  A span is a (ignored Bool, end_index Int) pair.

# As an example, consider this string:
# 'a _ b'
#
# The character classes are:
#
# a      ' '        _        ' '        b
# BLACK  DE_WHITE   DE_GRAY  DE_WHITE   BLACK
#
# The states are:
#
# a      ' '        _        ' '        b
# BLACK  DE_WHITE1  DE_GRAY  DE_WHITE2  BLACK
#
# DE_WHITE2 is whitespace that follows a "gray" non-whitespace IFS character.
#
# The spans emitted are:
#
# (part 'a', ignored ' _ ', part 'b')

# SplitForRead() will check if the last two spans are a \ and \\n.  Easy.

# Edges are characters.  CH_DE_ is the delimiter prefix.  WHITE is for
# whitespace; GRAY is for other IFS chars; BLACK is for significant
# characters.
CH_DE_WHITE, CH_DE_GRAY, CH_BLACK, CH_BACKSLASH = range(4)

# Nodes are states
ST_START, ST_DE_WHITE1, ST_DE_GRAY, ST_DE_WHITE2, ST_BLACK, ST_BACKSLASH = range(6)

# Actions control what spans to emit.
EMIT_PART, EMIT_DE, EMIT_EMPTY, EMIT_ESCAPE, NO_EMIT = range(5)

TRANSITIONS = {
    (ST_START, CH_DE_WHITE):  (ST_DE_WHITE1, NO_EMIT),    # ' '
    (ST_START, CH_DE_GRAY):   (ST_DE_GRAY,   EMIT_EMPTY), # '_'
    (ST_START, CH_BLACK):     (ST_BLACK,     NO_EMIT),    # 'a'
    (ST_START, CH_BACKSLASH): (ST_BACKSLASH, NO_EMIT),    # '\'

    (ST_DE_WHITE1, CH_DE_WHITE):  (ST_DE_WHITE1, NO_EMIT),  # '  '
    (ST_DE_WHITE1, CH_DE_GRAY):   (ST_DE_GRAY,   NO_EMIT),  # ' _'
    (ST_DE_WHITE1, CH_BLACK):     (ST_BLACK,     EMIT_DE),  # ' a'
    (ST_DE_WHITE1, CH_BACKSLASH): (ST_BACKSLASH, EMIT_DE),  # ' \'

    (ST_DE_GRAY, CH_DE_WHITE):  (ST_DE_WHITE2, NO_EMIT),    # '_ '
    (ST_DE_GRAY, CH_DE_GRAY):   (ST_DE_GRAY,   EMIT_EMPTY), # '__'
    (ST_DE_GRAY, CH_BLACK):     (ST_BLACK,     EMIT_DE),    # '_a'
    (ST_DE_GRAY, CH_BACKSLASH): (ST_BLACK,     EMIT_DE),    # '_\'

    (ST_DE_WHITE2, CH_DE_WHITE):  (ST_DE_WHITE2, NO_EMIT),    # '_  '
    (ST_DE_WHITE2, CH_DE_GRAY):   (ST_DE_GRAY,   EMIT_EMPTY), # '_ _'
    (ST_DE_WHITE2, CH_BLACK):     (ST_BLACK,     EMIT_DE),    # '_ a'
    (ST_DE_WHITE2, CH_BACKSLASH): (ST_BACKSLASH, EMIT_DE),    # '_ \'

    (ST_BLACK, CH_DE_WHITE):  (ST_DE_WHITE1, EMIT_PART),  # 'a '
    (ST_BLACK, CH_DE_GRAY):   (ST_DE_GRAY,   EMIT_PART),  # 'a_'
    (ST_BLACK, CH_BLACK):     (ST_BLACK,     NO_EMIT),    # 'aa'
    (ST_BLACK, CH_BACKSLASH): (ST_BACKSLASH, EMIT_PART),  # 'a\'

    # Here we emit an ignored \ and the second character as well.
    # We're emitting TWO spans here; we don't wait until the subsequent
    # character.  That is OK.
    #
    # Problem: if '\ ' is the last one, we don't want to emit a trailing span?
    # In all other cases we do.

    (ST_BACKSLASH, CH_DE_WHITE):  (ST_BLACK,     EMIT_ESCAPE),  # '\ '
    (ST_BACKSLASH, CH_DE_GRAY):   (ST_BLACK,     EMIT_ESCAPE),  # '\_'
    (ST_BACKSLASH, CH_BLACK):     (ST_BLACK,     EMIT_ESCAPE),  # '\a'
    # NOTE: second character is a backslash, but new state is ST_BLACK!
    (ST_BACKSLASH, CH_BACKSLASH): (ST_BLACK,     EMIT_ESCAPE),  # '\\'
}


class IfsSplitter(_BaseSplitter):
  """Split a string when IFS has non-whitespace characters."""

  def __init__(self, ifs_whitespace, ifs_other):
    _BaseSplitter.__init__(self, ifs_whitespace + ifs_other)
    self.ifs_whitespace = ifs_whitespace
    self.ifs_other = ifs_other

  def Split(self, s, allow_escape):
    ws_chars = self.ifs_whitespace
    other_chars = self.ifs_other

    n = len(s)
    spans = []  # NOTE: in C, could reserve() this to len(s)

    if n == 0:
      return spans  # empty

    # Ad hoc rule from POSIX: ignore leading whitespace.
    # "IFS white space shall be ignored at the beginning and end of the input"
    # This can't really be handled by the state machine.

    i = 0
    while i < n and s[i] in self.ifs_whitespace:
      i += 1

    # Append an ignored span.
    if i != 0:
      spans.append((span_e.Delim, i))

    # String is ONLY whitespace.  We want to skip the last span after the
    # while loop.
    if i == n:
      return spans

    state = ST_START
    while i < n:
      c = s[i]
      if c in ws_chars:
        ch = CH_DE_WHITE
      elif c in other_chars:
        ch = CH_DE_GRAY
      elif allow_escape and c == '\\':
        ch = CH_BACKSLASH
      else:
        ch = CH_BLACK

      new_state, action = TRANSITIONS[state, ch]

      #from core.util  import log
      #log('i %d c %r ch %s state %s new_state %s action %s', i, c, ch, state, new_state, action)

      if action == EMIT_PART:
        spans.append((span_e.Black, i))

      elif action == EMIT_DE:
        spans.append((span_e.Delim, i))  # ignored delimiter

      elif action == EMIT_EMPTY:
        spans.append((span_e.Delim, i))  # ignored delimiter
        spans.append((span_e.Black, i))  # EMPTY part that is NOT ignored

      elif action == EMIT_ESCAPE:
        spans.append((span_e.Backslash, i))  # \

      else:
        pass  # Emit nothing 

      state = new_state
      i += 1

    # Last span.  TODO: Put this in the state machine as the \0 char?
    if state == ST_BLACK:
      span_type = span_e.Black
    elif state == ST_BACKSLASH:
      span_type = span_e.Backslash
    elif state in (ST_DE_WHITE1, ST_DE_GRAY, ST_DE_WHITE2):
      span_type = span_e.Delim 
    else:
      raise AssertionError(state)  # shouldn't be in START state
    spans.append((span_type, n))

    return spans


# self.splitter = RootSplitter()
# SplitManager
#   Has the cache from IFS -> splitter
#   Split(s, allow_escape)
#
# _DefaultIfsSplitter -- \t\n\n
# _WhitespaceIfsSplitter
# _OtherIfsSplitter
# _MixedIfsSplitter -- ifs and other
#   Split(s, allow_escape)
#
# RegexSplitter
# CsvSplitter (TSV2Splitter maybe)
# AwkSplitter
#
# Any other kind of tokenizing?  This is based on lines.  So TSV2 does fit in.
