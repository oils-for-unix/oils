#!/usr/bin/env python2
"""
objects.py

Python types under value.Obj.  See the invariant in osh/runtime.asdl.
"""
from __future__ import print_function

from core.pyerror import log
from oil_lang import regex_translate

from typing import TYPE_CHECKING, List, Dict, Any, Optional
if TYPE_CHECKING:
  StrList = List[str]
  from _devbuild.gen.syntax_asdl import re_t, command__Func, expr__Lambda
  from osh.cmd_eval import CommandEvaluator
else:
  StrList = list

_ = log


# TODO: Consolidate with value_t
# Use value.Obj for now
class StrArray(StrList):
  """
  local oldarray=(a b c)  # only strings, but deprecated

  var array = @(a b c)  # only strings, PARSED like shell
  var oilarray = @[a b c]  # can be integers

  TODO: value.MaybeStrArray should be renamed LooseArray?
    Because it can have holes!
    StrNoneArray?  MaybeMaybeStrArray?

  In C, do both of them have the same physical representation?
  """
  pass


class Regex(object):
  """
  How to use Regex objects:
  
  Match:
    if (x ~ /d+/) {    # Compare with Perl's noisy $x =~ m/\d+/
    }

  Iterative Match:
    while (x ~ /d+ ; g/) {  # Do we want this global flag?
      echo $x
    }

    # maybe this should be the ~~ operator.
    # Honestly you don't need another operator?  If should always clear 
    # MATCH_STATE the first time?
    # What if you break though?

    while (x ~~ /d+/) {
      # this is the state you have?
      echo $_POS

      M.pos
    }

    # This might be better for initializing state
    for (/d+/ in x) {

    }

  Slurp All Matches:
    set m = matchall(s, /d+/)
    pass s => matchall( /(d+ as month) '/' (d+ as day)/ ) => var m

    Idea: if (s @~ m)  -- match all?

    # Doesn't work
    set matches = @[x ~ /d+/]

  Split:
    set parts = split(s, /d+/)
    set parts = split(s, ' ')   # Split by character
    set parts = split(s)        # IFS split algorithm
    set parts = split(s, %awk)  # Awk's algorithm

    pass x => split(/d+/) => var parts

  Subst
    Perl:
      $text =~ s/regex/replacement/modifiers

    Python:
      text = pat.sub(replace, string, n)
      replace can be a function

    Oil:
      # Winner: First argument is text.
      pass text => subst(/d+/, 'replace') => var new
      var text = subst(text, /d+/, 'replace', n)

      Discarded:
        var text = sub /d+/ in text with 'replace'
        var text = text.subst(/d+/, 'replace', n)

      pass text => subst(/d+/, func(M) {
        return "${M.name} ${M.ratio %.3f}"
      }) => var new

      %%% pass text
       => subst(/d+/, fn(M) "${M.name} --- ${M.ratio %.3f}")
       => var new
 
  """
  def __init__(self, regex):
    # type: (re_t) -> None
    self.regex = regex
    self.as_ere = None # type: Optional[str] # Cache the evaluation

  def __repr__(self):
    # type: () -> str
    # The default because x ~ obj accepts an ERE string?
    # And because grep $/d+/ does.
    #
    # $ var x = /d+/
    # $ echo $x
    # [0-9]+
    return self.AsPosixEre()

  def AsPosixEre(self):
    # type: () -> str
    if self.as_ere is None:
      parts = [] # type: List[str]
      regex_translate.AsPosixEre(self.regex, parts)
      self.as_ere = ''.join(parts)
    return self.as_ere

  def AsPcre(self):
    # type: () -> None
    pass

  def AsPythonRe(self):
    # type: () -> None
    """Very similar to PCRE, except a few constructs aren't allowed."""
    pass

