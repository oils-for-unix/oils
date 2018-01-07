#!/usr/bin/python
"""
libstr.py - String library functions that can be exposed with a saner syntax.

Instead of 

local y=${x//a*/b}

var y = x -> sub('a*', 'b', :ALL)

Or maybe:

var y = x -> sub( g/a*/, 'b', :ALL)
"""

from core import glob_
from core.id_kind import Id

# Implementation without Python regex:
#
# (1) PatSub: I think we fill in GlobToExtendedRegex, then use regcomp and
# regexec.  in a loop.  fnmatch() does NOT given positions of matches.
#
# (2) Strip -- % %% # ## - 
#
# a. Fast path for constant strings.
# b. Convert to POSIX extended regex, to see if it matches at ALL.  If it
# doesn't match, short circuit out?  We can't do this with fnmatch.
# c. If it does match, call fnmatch() iteratively over prefixes / suffixes.
#
# - # shortest prefix - [:1], [:2], [:3] until it matches
# - ## longest prefix - [:-1] [:-2], [:3].  Works because fnmatch does not
#                       match prefixes, it matches EXATLY.
# - % shortest suffix - [-1:] [-2:] [-3:] ...
# - %% longest suffix - [1:] [2:] [3:]
#
# See remove_pattern() in subst.c for bash, and trimsub() in eval.c for
# mksh.  Dash doesn't implement it.


# TODO:
# - Unicode support: Convert both pattern, string, and replacement to unicode,
#   then the result back at the end.
# - Add location info to errors.  Maybe pass spid pair all the way down.
#   - Compile time errors for [[:space:]] ?

def DoUnarySuffixOp(s, op, arg):
  """Helper for ${x#prefix} and family."""

  pat_re, err = glob_.GlobToPythonRegex(arg)
  if err:
    e_die("Can't convert glob to regex: %r", arg)

  if pat_re is None:  # simple/fast path for fixed strings
    if op.op_id in (Id.VOp1_Pound, Id.VOp1_DPound):  # const prefix
      if s.startswith(arg):
        return s[len(arg):]
      else:
        return s

    elif op.op_id in (Id.VOp1_Percent, Id.VOp1_DPercent):  # const suffix
      if s.endswith(arg):
        # Mutate it so we preserve the flags.
        return s[:-len(arg)]
      else:
        return s

    else:  # e.g. ^ ^^ , ,,
      raise AssertionError(op.op_id)

  else:  # glob pattern
    # Extract the group from the regex and return it
    if op.op_id == Id.VOp1_Pound:  # shortest prefix
      # Need non-greedy match
      pat_re2, err = glob_.GlobToPythonRegex(arg, greedy=False)
      r = re.compile(pat_re2)
      m = r.match(s)
      if m:
        return s[m.end(0):]
      else:
        return s

    elif op.op_id == Id.VOp1_DPound:  # longest prefix
      r = re.compile(pat_re)
      m = r.match(s)
      if m:
        return s[m.end(0):]
      else:
        return s

    elif op.op_id == Id.VOp1_Percent:  # shortest suffix
      # NOTE: This is different than re.search, which will find the longest
      # suffix.
      r = re.compile('^(.*)' + pat_re + '$')
      m = r.match(s)
      if m:
        return m.group(1)
      else:
        return s
      
    elif op.op_id == Id.VOp1_DPercent:  # longest suffix
      r = re.compile('^(.*?)' + pat_re + '$')  # non-greedy
      m = r.match(s)
      if m:
        return m.group(1)
      else:
        return s

    else:
      raise AssertionError(op.op_id)


def PatSub(s, op, pat, replace_str):
  """Helper for ${x/pat/replace}."""
  #log('PAT %r REPLACE %r', pat, replace_str)
  py_regex, err = glob_.GlobToPythonRegex(pat)
  if err:
    e_die("Can't convert glob to regex: %r", pat)

  if py_regex is None:  # Simple/fast path for fixed strings
    if op.do_all:
      return s.replace(pat, replace_str)
    elif op.do_prefix:
      if s.startswith(pat):
        n = len(pat)
        return replace_str + s[n:]
      else:
        return s
    elif op.do_suffix:
      if s.endswith(pat):
        n = len(pat)
        return s[:-n] + replace_str
      else:
        return s
    else:
      return s.replace(pat, replace_str, 1)  # just the first one

  else:
    count = 1  # replace first occurrence only
    if op.do_all:
      count = 0  # replace all
    elif op.do_prefix:
      py_regex = '^' + py_regex
    elif op.do_suffix:
      py_regex = py_regex + '$'

    pat_re = re.compile(py_regex)
    return pat_re.sub(replace_str, s, count)

