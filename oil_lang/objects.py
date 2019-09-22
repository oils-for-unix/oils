#!/usr/bin/env python2
"""
objects.py

Python types under value.Obj.  See the invariant in osh/runtime.asdl.
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import re_e, re_repeat_e, class_literal_term_e

from osh import glob_  # for ExtendedRegexEscape
from core.util import log, e_die

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


PERL_CLASS = {
    'd': '[:digit:]',
    # Python's docs say it's [a-zA-Z0-9_] when NO LOCALE is set.
    'w': '[:alpha:][:digit:]_',
    # Python's doc says \s is [ \t\n\r\f\v] when NO LCOALE
    's': '[:space:]',
}


# ERE's in POSIX:
# https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
# 
# NOTE: They don't support \x00 or \u1234 as in Perl/Python!
#
# It's hard to grep for tabs with BRE or ERE syntax.  You have to use:
#
# (1) a literal tab with Ctrl-V, or
# (2) bash syntax:  grep $'\t' foo.txt
# (3) POSIX shell syntax:  grep "$(echo -e '\t')" foo.txt.
#
# I ran into this in test/lint.sh !!!
#
# https://stackoverflow.com/questions/1825552/grep-a-tab-in-unix

# Algorithm:
# - Unicode escapes in BREs disallowed
# - ASCII codes 1-255 allowed LITERALLY, but NUL \0 disallowed
#
# What about utf-8 encoded characters?  Those work within literals, but are
# problematic within character sets.  There's no way to disallow those in
# general though.

def _ClassLiteralToPosixEre(term, parts):
  tag = term.tag
  if tag == class_literal_term_e.Range:
    # TODO: Proper escaping of chars!!!  \] \- etc.
    parts.append('%s-%s' % (term.start, term.end))
    return

  if tag == class_literal_term_e.CharSet:
    # TODO: Proper escaping of chars!!!  \] \- etc.

    # ExtendedRegexEscape is different!
    parts.append(glob_.EreCharClassEscape(term.chars))
    return

  raise NotImplementedError(term) 

def _PosixEre(node, parts):
  tag = node.tag
  if tag == re_e.Primitive:
    if node.id == Id.Re_Dot:
      parts.append('.')
    elif node.id == Id.Re_Start:
      parts.append('^')
    elif node.id == Id.Re_End:
      parts.append('$')
    else:
      raise AssertionError(node)
    return

  if tag == re_e.LiteralChars:
    # The bash [[ x =~ "." ]] construct also has to do this

    # TODO: What about \0 and unicode escapes?
    # Those won't be as LiteralChars I don't think?
    # Unless you put them there through \0
    # Maybe DISALLOW those.
    # "Unprintable chars should be written as \0 or \x00 or \u0000"

    parts.append(glob_.ExtendedRegexEscape(node.s))
    return

  if tag == re_e.Seq:
    for c in node.children:
      _PosixEre(c, parts)
    return

  if tag == re_e.Alt:
    for i, c in enumerate(node.children):
      if i != 0:
        parts.append('|')
      _PosixEre(c, parts)
    return

  if tag == re_e.Repeat:
    # 'foo' or "foo" or $x or ${x} evaluated to too many chars
    if node.child.tag == re_e.LiteralChars:
      if len(node.child.s) > 1:
        # Note: Other regex dialects have non-capturing groups since we don't
        # need this.
        e_die("POSIX EREs don't have groups without capture, so this node "
              "needs () around it.", span_id=node.child.spid)

    _PosixEre(node.child, parts)
    op = node.op
    op_tag = op.tag

    if op_tag == re_repeat_e.Op:
      op_id = op.op.id
      if op_id == Id.Arith_Plus:
        parts.append('+')
      elif op_id == Id.Arith_Star:
        parts.append('*')
      elif op_id == Id.Arith_QMark:
        parts.append('?')
      else:
        raise AssertionError(op_id)
      return

    if op_tag == re_repeat_e.Num:
      parts.append('{%s}' % op.times.val)
      return

    if op_tag == re_repeat_e.Range:
      lower = op.lower.val if op.lower else ''
      upper = op.upper.val if op.upper else ''
      parts.append('{%s,%s}' % (lower, upper))
      return

    raise NotImplementedError(node.op)

  if tag == re_e.Group:
    parts.append('(')
    _PosixEre(node.child, parts)
    parts.append(')')
    return

  if tag == re_e.PerlClass:
    n = node.name
    chars = PERL_CLASS[node.name]
    if node.negated:
      pat = '[^%s]' % chars
    else:
      pat = '[%s]' % chars
    parts.append(pat)
    return

  if tag == re_e.PosixClass:
    n = node.name
    if node.negated:
      pat = '[^[:%s:]]' % n
    else:
      pat = '[[:%s:]]' % n
    parts.append(pat)
    return

  if tag == re_e.ClassLiteral:
    parts.append('[')
    for term in node.terms:
      _ClassLiteralToPosixEre(term, parts)
    parts.append(']')
    return

  raise NotImplementedError(node.__class__.__name__)


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
      _PosixEre(self.regex, parts)
      self.as_ere = ''.join(parts)
    return self.as_ere

  def AsPcre(self):
    pass

  def AsPythonRe(self):
    """Very similar to PCRE, except a few constructs aren't allowed."""
    pass
