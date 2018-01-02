#!/usr/bin/python
"""
legacy.py
"""

import re

from core import runtime

value_e = runtime.value_e


def GetIfs(mem):
  """
  Used for splitting words in Splitter.
  """
  val = mem.GetVar('IFS')
  if val.tag == value_e.Undef:
    return ''
  elif val.tag == value_e.Str:
    return val.s
  else:
    # TODO: Raise proper error
    raise AssertionError("IFS shouldn't be an array")


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
