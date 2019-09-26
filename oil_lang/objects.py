#!/usr/bin/env python2
"""
objects.py

Python types under value.Obj.  See the invariant in osh/runtime.asdl.
"""
from __future__ import print_function

from core.util import log
from oil_lang import regex_translate

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import regex_t

_ = log


# These are for data frames?

class BoolArray(list):
  """
  var b = @[true false false]
  var b = @[T F F]
  """
  pass

class IntArray(list):
  """
  var b = @[1 2 3 -42]
  """
  pass


class FloatArray(list):
  """
  var b = @[1.1 2.2 3.9]
  """
  pass


class StrArray(list):
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


class Table(dict):
  """
  This is a data frame, which is a dict of arrays.

  NOTE that we don't need ellipsis because we only have two dimensions.

  print(b[...,1]) #Equivalent to b[: ,: ,1 ] 
  """
  def __init__(self):
    pass

  def __getitem__(self, index):
    """
    TODO: Accept slices here.
    """
    # Shows the slice objects
    #log('index %s', index)

    return 'TODO: Table Slicing'



class Func(object):
  """An Oil function declared with 'func'."""
  def __init__(self, node, default_vals, ex):
    self.node = node
    self.default_vals = default_vals
    self.ex = ex

  def __call__(self, *args, **kwargs):
    return self.ex.RunOilFunc(self.node, self.default_vals, args, kwargs)


class Proc(object):
  """An Oil proc declared with 'proc'.

  Unlike a shell proc, it has a signature, so we need to bind names to params.
  """
  def __init__(self, node):
    self.docstring = ''
    self.node = node


class Module(object):
  """An Oil module.

  The 'use' keyword creates an object of this type in the current namespace.

  It holds both variables and functions.

  But it doesn't have "$@" or anything else that Mem has?
  Mem also has introspection.  For function calls and such.
  Maybe that only applies to 'proc' and not 'func'.
  """
  def __init__(self, name):
    self.name = name
    self.docstring = ''
    # items
    self.attrs = {}


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
    # type: (regex_t) -> None
    self.regex = regex
    self.as_ere = None  # Cache the evaluation

  def __repr__(self):
    # The default because x ~ obj accepts an ERE string?
    # And because grep $/d+/ does.
    #
    # $ var x = /d+/
    # $ echo $x
    # [0-9]+
    return self.AsPosixEre()

  def AsPosixEre(self):
    if self.as_ere is None:
      parts = []
      regex_translate.AsPosixEre(self.regex, parts)
      self.as_ere = ''.join(parts)
    return self.as_ere

  def AsPcre(self):
    pass

  def AsPythonRe(self):
    """Very similar to PCRE, except a few constructs aren't allowed."""
    pass

