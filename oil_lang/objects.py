#!/usr/bin/env python2
"""
objects.py

Python types under value.Obj.  See the invariant in osh/runtime.asdl.
"""
from __future__ import print_function

from core.util import log
from oil_lang import regex_translate

from typing import Union, TYPE_CHECKING, List, Dict, Any, Optional
if TYPE_CHECKING:
  from typing import Type
  BoolList = List[bool]
  IntList = List[int]
  FloatList = List[float]
  StrList = List[str]
  TableDict = Dict[Any, List[Any]]
  AssocArrayDict = Dict[Any, Any]
  from _devbuild.gen.syntax_asdl import re_t, command__Proc, command__Func, expr__Lambda
  from osh.cmd_exec import Executor
else:
  BoolList = IntList = FloatList = StrList = list
  AssocArrayDict = TableDict = dict

_ = log


class ParameterizedArray(object):
  """
  Parameterized
  For Array[Bool]
  """
  def __getitem__(self, typ):
    # type: (type) -> Union[Type[BoolArray], Type[IntArray], Type[FloatArray], Type[StrArray]]
    if typ is bool:
      return BoolArray
    if typ is int:
      return IntArray
    if typ is float:
      return FloatArray
    if typ is str:
      return StrArray
    raise AssertionError('typ: %s' % typ)

  def __call__(self):
    # type: () -> None
    # Array(1 2 3)
    raise AssertionError("Arrays need a parameterized type")


# These are for data frames?

class BoolArray(BoolList):
  """
  var b = @[true false false]
  var b = @[T F F]
  """
  pass

class IntArray(IntList):
  """
  var b = @[1 2 3 -42]
  """
  pass


class FloatArray(FloatList):
  """
  var b = @[1.1 2.2 3.9]
  """
  pass


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


# TODO: Maybe use this so that 'pp my_assoc_array' works?  Or does it even
# matter how it was defined?
class AssocArray(AssocArrayDict):
  pass


class Table(TableDict):
  """A table is our name for a data frame. 
  
  It's represented by a dict of arrays.

  Notes:

  - Can we do table[rowexpr, columnexpr] slicing?

    t[name == 'bob',]              # A 1-tuple isn't good?
    t[name == 'bob', :]            # This is better
    t[name == 'bob', @(name age)]  # Select columns

  Problem: it would require lazy evaluation.

  - We don't need Ellipsis because we only have two dimensions.

  print(b[...,1]) #Equivalent to b[: ,: ,1 ] 
  """
  def __init__(self):
    # type: () -> None
    pass

  def __getitem__(self, index):
    # type: (Any) -> Any
    """
    TODO: Accept slices here.

    d['mycol']  # returns a vector
    d->mycol

    d[rowexpr, colexpr]  # how to implement this?
    """
    # Shows the slice objects
    #log('index %s', index)

    return 'TODO: Table Slicing'


class Proc(object):
  """An Oil proc declared with 'proc'.

  Unlike a shell proc, it has a signature, so we need to bind names to params.
  """
  def __init__(self, node, defaults):
    # type: (command__Proc, Optional[List[Any]]) -> None
    self.docstring = ''
    self.node = node
    self.defaults = defaults


class Func(object):
  """An Oil function declared with 'func'."""
  def __init__(self, node, pos_defaults, named_defaults, ex):
    # type: (command__Func, List[Any], Dict[str, Any], Executor) -> None
    self.node = node
    self.pos_defaults = pos_defaults
    self.named_defaults = named_defaults
    self.ex = ex

  def __call__(self, *args, **kwargs):
    # type: (*Any, **Any) -> Any
    return self.ex.RunOilFunc(self, args, kwargs)


class Lambda(object):
  """An Oil function like |x| x+1 """
  def __init__(self, node, ex):
    # type: (expr__Lambda, Executor) -> None
    self.node = node
    self.ex = ex

  def __call__(self, *args, **kwargs):
    # type: (*Any, **Any) -> Any
    return self.ex.RunLambda(self.node, args, kwargs)


class Module(object):
  """An Oil module.

  The 'use' keyword creates an object of this type in the current namespace.

  It holds both variables and functions.

  But it doesn't have "$@" or anything else that Mem has?
  Mem also has introspection.  For function calls and such.
  Maybe that only applies to 'proc' and not 'func'.
  """
  def __init__(self, name):
    # type: (str) -> None
    self.name = name
    self.docstring = ''
    # items
    self.attrs = {} # type: Dict[str, Any]


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

