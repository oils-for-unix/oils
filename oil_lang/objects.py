#!/usr/bin/env python2
"""
objects.py

Python types under value.Obj.  See the invariant in osh/runtime.asdl.
"""
from __future__ import print_function


from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import re_repeat_e
from _devbuild.gen.runtime_asdl import regex_e

from core.util import log

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

def _PosixEre(node, parts):
  tag = node.tag
  if tag == regex_e.Dot:
    parts.append('.')
    return

  if tag == regex_e.Start:
    parts.append('^')
    return

  if tag == regex_e.End:
    parts.append('$')
    return

  if tag == regex_e.Seq:
    for c in node.children:
      _PosixEre(c, parts)
    return

  if tag == regex_e.Alt:
    for i, c in enumerate(node.children):
      if i != 0:
        parts.append('|')
      _PosixEre(c, parts)
    return

  if tag == regex_e.Repeat:
    _PosixEre(node.child, parts)
    op_tag = node.op.tag

    if op_tag == re_repeat_e.Op:
      op_id = node.op.op.id
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
      pass

    if op_tag == re_repeat_e.Range:
      pass

    raise NotImplementedError(node.op)

  if tag == regex_e.PerlClass:
    n = node.name
    chars = PERL_CLASS[node.name]
    if node.negated:
      pat = '[^%s]' % chars
    else:
      pat = '[%s]' % chars
    parts.append(pat)
    return

  if tag == regex_e.PosixClass:
    n = node.name
    if node.negated:
      pat = '[^[:%s:]]' % n
    else:
      pat = '[[:%s:]]' % n
    parts.append(pat)
    return

  raise NotImplementedError(node.__class__.__name__)


class Regex(object):
  """
  TODO: This should resolve all references into a different type of tree?

  var D = / d+ /
  var pat2 = / D '.' D '.' D $suffix /

  Instead of expr.RegexLiteral runtime.Regex?  And objects.Regex wraps it?
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
