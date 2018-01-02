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

value_e = runtime.value_e


DEFAULT_IFS = ' \t\n'


class CompletionSplitter:
  def __init__(self):
    pass
  
  def SplitForWordEval(self, s):
    # Return a span that is the whole thing?
    # Honestly do I even need this?
    return (False, len(s))

  # NOTE: Doesn't need to implement SplitForRead


def _Split(s, ifs):
  """Helper function for IFS split."""
  parts = ['']
  for c in s:
    if c in ifs:
      parts.append('')
    else:
      parts[-1] += c
  return parts


def IfsSplit(s, ifs):
  """
  http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_06_05
  https://www.gnu.org/software/bash/manual/bashref.html#Word-Splitting

  Summary:
  1. ' \t\n' is special.  Whitespace is trimmed off the front and back.
  2. if IFS is '', no field splitting is performed.
  3. Otherwise, suppose IFS = ' ,\t'.  Then IFS whitespace is space or comma.
    a.  IFS whitespace isgnored at beginning and end.
    b. any other IFS char delimits the field, along with adjacent IFS
       whitespace.
    c. IFS whitespace shall delimit a field.

  # Can we do this be regex or something?  Use regex match?
  """
  assert isinstance(ifs, str), ifs
  if not ifs:
    return [s]  # no splitting

  # print("IFS SPLIT %r %r" % (s, ifs))
  # TODO: This detect if it's ALL whitespace?  If ifs_other is empty?
  if ifs == ' \t\n':
    return _Split(s, ifs)

  # Detect IFS whitespace
  # TODO: This should be cached.  In Mem?  Or Splitter?
  ifs_whitespace = ''
  ifs_other = ''
  for c in ifs:
    if c in ' \t\n':
      ifs_whitespace += c
    else:
      ifs_other += c

  # TODO: Rule 3a. Ignore leading and trailing IFS whitespace?

  # hack to make an RE

  # Hm this escapes \t as \\\t?  I guess that works.
  ws_re = re.escape(ifs_whitespace)

  other_re = re.escape(ifs_other)
  #print('chars', repr(ifs_whitespace), repr(ifs_other))
  #print('RE', repr(ws_re), repr(other_re))

  # BUG: re.split() is the wrong model.  It works with the 'delimiting' model.
  # Forward iteration.  TODO: grep for IFS in dash/mksh/bash/ash.

  # ifs_ws | ifs_ws* non_ws_ifs ifs_ws*
  if ifs_whitespace and ifs_other:
    # first alternative is rule 3c.
    # BUG: It matches the whitespace first?
    pat = '[%s]+|[%s]*[%s][%s]*' % (ws_re, ws_re, other_re, ws_re)
  elif ifs_whitespace:
    pat = '[%s]+' % ws_re
  elif ifs_other:
    pat = '[%s]' % other_re
  else:
    raise AssertionError

  #print('PAT', repr(pat))
  regex = re.compile(pat)
  frags = regex.split(s)
  #log('split %r by %r -> frags %s', s, pat, frags)
  return frags


# Split operation:
#
# Max to allocate: the length of the string?  That's the worst case.  Every
# character is a different split.
#
# or use end_index?
#
# word_eval: Makes runtime.fragment out of it.  Only takes the parts that are
# not delimiters.
#
# read: assigns it to variables, except for the trailing ones.  Don't need
# to split them.


# TODO:
# - Executor holds a splitter.  Passes it to word_eval and to the read
# builtin.
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

      if ifs_other:
        sp = MixedSplitter(ifs_whitespace, ifs_other)
      else:
        sp = WhitespaceSplitter(ifs_whitespace)

      # NOTE: Technically, we could make the key more precise.  IFS=$' \t' is
      # the same as IFS=$'\t '.  But most programs probably don't do that, and
      # everything should work in any case.
      self.splitters[ifs] = sp

    return sp

  def ShouldElide(self):
    # HACK for now
    sp = self._GetSplitter()
    return isinstance(sp, WhitespaceSplitter)

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
    spans = sp.Split(s, False)
    parts = []
    start_index = 0
    for ignored, end_index in spans:
      if not ignored:
        parts.append(s[start_index:end_index])
      start_index = end_index
    return parts

  def SplitForRead(self, s, allow_escape):
    # Does this give you back the exact number you need?
    # Removes ignored ones

    sp = WhitespaceSplitter(DEFAULT_IFS)
    spans = sp.Split(s, allow_escape)
    parts = ['TODO']
    return parts


# We detect state changes.  WHITE is for whitespace, BLACK is for significant
# chars.
STATE_WHITE, STATE_BLACK = 0, 2

class WhitespaceSplitter(object):

  def __init__(self, ifs_whitespace):
    self.ifs_whitespace = ifs_whitespace

  def Split(self, s, allow_escape):
    ws_chars = self.ifs_whitespace

    n = len(s)
    spans = []  # NOTE: in C, could reserve() this to len(s)

    if n == 0:
      return spans  # empty

    state = STATE_WHITE if s[0] in ws_chars else STATE_BLACK
    prev_state = state

    i = 1
    while i < n:
      state = STATE_WHITE if s[i] in ws_chars else STATE_BLACK

      if state != prev_state:
        spans.append((prev_state == STATE_WHITE, i))
        prev_state = state

      i += 1

    spans.append((prev_state == STATE_WHITE, i))

    return spans


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
    (ST_BACKSLASH, CH_BACKSLASH): (ST_BACKSLASH, EMIT_ESCAPE),  # '\\'
}


class MixedSplitter(object):
  """Split a string when IFS has non-whitespace characters."""

  def __init__(self, ifs_whitespace, ifs_other):
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
      spans.append((True, i))

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
      else:
        ch = CH_BLACK

      new_state, action = TRANSITIONS[state, ch]

      #from core.util  import log
      #log('i %d c %r ch %s state %s new_state %s action %s', i, c, ch, state, new_state, action)

      if action == EMIT_PART:
        spans.append((False, i))
      elif action == EMIT_DE:
        spans.append((True, i))  # ignored delimiter
      elif action == EMIT_EMPTY:
        spans.append((True, i))  # ignored delimiter
        spans.append((False, i))  # EMPTY part that is NOT ignored
      else:
        pass  # Emit nothing 

      state = new_state
      i += 1

    # Last span
    ignored = state in (ST_DE_WHITE1, ST_DE_GRAY, ST_DE_WHITE2)
    spans.append((ignored, n))

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
