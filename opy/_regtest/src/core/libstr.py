#!/usr/bin/env python
"""
libstr.py - String library functions that can be exposed with a saner syntax.

Instead of 

local y=${x//a*/b}

var y = x -> sub('a*', 'b', :ALL)

Or maybe:

var y = x -> sub( g/a*/, 'b', :ALL)
"""

import re

import libc

from osh.meta import Id
from core import glob_
from core import util

log = util.log
e_die = util.e_die

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
#                       match prefixes, it matches EXACTLY.
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

  # Fast path for constant strings.
  if not glob_.LooksLikeGlob(arg):
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

  # For patterns, do fnmatch() in a loop.
  #
  # TODO: Check another fast path first?
  #
  # v=aabbccdd
  # echo ${v#*b}  # strip shortest prefix
  #
  # If the whole thing doesn't match '*b*', then no test can succeed.  So we
  # can fail early.  Conversely echo ${v%%c*} and '*c*'.

  n = len(s)
  if op.op_id == Id.VOp1_Pound:  # shortest prefix
    # 'abcd': match 'a', 'ab', 'abc', ...
    for i in xrange(1, n+1):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[:i]):
        return s[i:]
    else:
      return s

  elif op.op_id == Id.VOp1_DPound:  # longest prefix
    # 'abcd': match 'abc', 'ab', 'a'
    for i in xrange(n, 0, -1):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[:i]):
        return s[i:]
    else:
      return s

  elif op.op_id == Id.VOp1_Percent:  # shortest suffix
    # 'abcd': match 'abc', 'ab', 'a'
    for i in xrange(n-1, -1, -1):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[i:]):
        return s[:i]
    else:
      return s
    
  elif op.op_id == Id.VOp1_DPercent:  # longest suffix
    # 'abcd': match 'abc', 'bc', 'c', ...
    for i in xrange(0, n):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[i:]):
        return s[:i]
    else:
      return s


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

