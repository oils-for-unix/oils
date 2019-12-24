#!/usr/bin/env python2
"""
regex_translate.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    class_literal_term_e,
    class_literal_term__Range,
    class_literal_term__ByteSet,
    class_literal_term__CodePoint,
    class_literal_term__CharLiteral,
    posix_class,
    perl_class,
    re_e,
    re__ClassLiteral,
    re__Primitive,
    re__LiteralChars,
    re__Seq,
    re__Alt,
    re__Repeat,
    re__Group,
    re_repeat_e,
    re_repeat__Op,
    re_repeat__Num,
    re_repeat__Range,
)
from _devbuild.gen.id_kind_asdl import Id

from core.util import log, e_die
from osh import glob_  # for ExtendedRegexEscape

from typing import List, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import class_literal_term_t, re_t

_ = log

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
  # type: (class_literal_term_t, List[str]) -> None

  UP_term = term
  tag = term.tag_()

  if tag == class_literal_term_e.Range:
    term = cast(class_literal_term__Range, UP_term)
    # \\ \^ \- can be used in ranges?
    start = glob_.EreCharClassEscape(term.start)
    end = glob_.EreCharClassEscape(term.end)
    parts.append('%s-%s' % (start, end))
    return

  if tag == class_literal_term_e.ByteSet:
    term = cast(class_literal_term__ByteSet, UP_term)
    # This escaping is different than ExtendedRegexEscape.
    parts.append(glob_.EreCharClassEscape(term.bytes))
    return

  if tag == class_literal_term_e.CodePoint:
    term = cast(class_literal_term__CodePoint, UP_term)
    code_point = term.i
    if code_point < 128:
      parts.append(chr(code_point))
    else:
      e_die("ERE can't express code point %d", code_point, span_id=term.spid)
    return

  if tag == class_literal_term_e.PerlClass:
    term = cast(perl_class, UP_term)
    n = term.name
    chars = PERL_CLASS[term.name]  # looks like '[:digit:]'
    if term.negated:
      e_die("Perl classes can't be negated in ERE",
            span_id=term.negated.span_id)
    else:
      pat = '%s' % chars
    parts.append(pat)
    return

  if tag == class_literal_term_e.PosixClass:
    term = cast(posix_class, UP_term)
    n = term.name  # looks like 'digit'
    if term.negated:
      e_die("POSIX classes can't be negated in ERE",
            span_id=term.negated.span_id)
    else:
      pat = '[:%s:]' % n
    parts.append(pat)
    return

  if tag == class_literal_term_e.CharLiteral:
    term = cast(class_literal_term__CharLiteral, UP_term)
    parts.append(term.tok.val)
    return

  raise NotImplementedError(tag)


def AsPosixEre(node, parts):
  # type: (re_t, List[str]) -> None
  """Translate an Oil regex to a POSIX ERE.

  Appends to a list of parts that you hvae to join.
  """
  UP_node = node
  tag = node.tag_()

  if tag == re_e.Primitive:
    node = cast(re__Primitive, UP_node)
    if node.id == Id.Re_Dot:
      parts.append('.')
    elif node.id == Id.Re_Start:
      parts.append('^')
    elif node.id == Id.Re_End:
      parts.append('$')
    else:
      raise AssertionError(node.id)
    return

  if tag == re_e.LiteralChars:
    node = cast(re__LiteralChars, UP_node)
    # The bash [[ x =~ "." ]] construct also has to do this

    # TODO: What about \0 and unicode escapes?
    # Those won't be as LiteralChars I don't think?
    # Unless you put them there through \0
    # Maybe DISALLOW those.
    # "Unprintable chars should be written as \0 or \x00 or \u0000"

    parts.append(glob_.ExtendedRegexEscape(node.s))
    return

  if tag == re_e.Seq:
    node = cast(re__Seq, UP_node)
    for c in node.children:
      AsPosixEre(c, parts)
    return

  if tag == re_e.Alt:
    node = cast(re__Alt, UP_node)
    for i, c in enumerate(node.children):
      if i != 0:
        parts.append('|')
      AsPosixEre(c, parts)
    return

  if tag == re_e.Repeat:
    node = cast(re__Repeat, UP_node)
    # 'foo' or "foo" or $x or ${x} evaluated to too many chars
    if node.child.tag_() == re_e.LiteralChars:
      child = cast(re__LiteralChars, node.child)
      if len(child.s) > 1:
        # Note: Other regex dialects have non-capturing groups since we don't
        # need this.
        e_die("POSIX EREs don't have groups without capture, so this node "
              "needs () around it.", span_id=child.spid)

    AsPosixEre(node.child, parts)
    op = node.op
    op_tag = op.tag_()
    UP_op = op

    if op_tag == re_repeat_e.Op:
      op = cast(re_repeat__Op, UP_op)
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
      op = cast(re_repeat__Num, UP_op)
      parts.append('{%s}' % op.times.val)
      return

    if op_tag == re_repeat_e.Range:
      op = cast(re_repeat__Range, UP_op)
      lower = op.lower.val if op.lower else ''
      upper = op.upper.val if op.upper else ''
      parts.append('{%s,%s}' % (lower, upper))
      return

    raise NotImplementedError(op_tag)

  # Special case for familiarity: () is acceptable as a group in ERE
  if tag in (re_e.Group, re_e.Capture):
    node = cast(re__Group, UP_node)
    parts.append('(')
    AsPosixEre(node.child, parts)
    parts.append(')')
    return

  if tag == re_e.PerlClass:
    node = cast(perl_class, UP_node)
    n = node.name
    chars = PERL_CLASS[node.name]  # looks like [:digit:]
    if node.negated:
      pat = '[^%s]' % chars
    else:
      pat = '[%s]' % chars
    parts.append(pat)
    return

  if tag == re_e.PosixClass:
    node = cast(posix_class, UP_node)
    n = node.name  # looks like 'digit'
    if node.negated:
      pat = '[^[:%s:]]' % n
    else:
      pat = '[[:%s:]]' % n
    parts.append(pat)
    return

  if tag == re_e.ClassLiteral:
    node = cast(re__ClassLiteral, UP_node)
    parts.append('[')
    if node.negated:
      parts.append('^')
    for term in node.terms:
      _ClassLiteralToPosixEre(term, parts)
    parts.append(']')
    return

  raise NotImplementedError(tag)
