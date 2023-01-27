#!/usr/bin/env python2
"""
regex_translate.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    char_class_term_e, char_class_term_t,
    char_class_term__Range,
    posix_class, perl_class, CharCode,

    re_e, re__CharClass, re__Primitive, re__LiteralChars, re__Seq, re__Alt,
    re__Repeat, re__Group, re_repeat_e, re_repeat__Op, re_repeat__Num,
    re_repeat__Range,
    loc,
)
from _devbuild.gen.id_kind_asdl import Id

from core.pyerror import log, e_die
from mycpp.mylib import tagswitch
from osh import glob_  # for ExtendedRegexEscape

from typing import List, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import re_t

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

CH_RBRACKET = 0x5d
CH_BACKSLASH = 0x5c
CH_CARET = 0x5e
CH_HYPHEN = 0x2d

FLAG_RBRACKET  = 0b0001
FLAG_BACKSLASH = 0b0010
FLAG_CARET     = 0b0100
FLAG_HYPHEN    = 0b1000

def _CharCodeToEre(term, parts, special_char_flags):
  # type: (CharCode, List[str], List[int]) -> None
  """
  special_char_flags: list of single int that is mutated
  """

  char_int = term.i
  if char_int >= 128 and term.u_braced:
    # \u{ff} can't be represented in ERE because we don't know the encoding
    # \xff can be represented
    e_die("ERE can't express char code %d" % char_int, loc.Span(term.spid))

  # note: mycpp doesn't handle
  # special_char_flags[0] |= FLAG_HYPHEN
  mask = special_char_flags[0]

  if char_int == CH_HYPHEN:
    mask |= FLAG_HYPHEN
  elif char_int == CH_CARET:
    mask |= FLAG_CARET
  elif char_int == CH_RBRACKET:
    mask |= FLAG_RBRACKET
  elif char_int == CH_BACKSLASH:
    mask |= FLAG_BACKSLASH
  else:
    parts.append(chr(char_int))

  special_char_flags[0] = mask


def _CharClassTermToEre(term, parts, special_char_flags):
  # type: (char_class_term_t, List[str], List[int]) -> None
  """
  special_char_flags: list of single int that is mutated
  """

  UP_term = term
  tag = term.tag_()

  with tagswitch(term) as case:
    if case(char_class_term_e.Range):
      term = cast(char_class_term__Range, UP_term)

      # Create our own flags
      range_no_special = [0]

      _CharCodeToEre(term.start, parts, range_no_special)
      if range_no_special[0] !=0:
        e_die("Can't use char %d as start of range in ERE syntax" % term.start.i,
              loc.Span(term.start.spid))

      parts.append('-')  # a-b

      _CharCodeToEre(term.end, parts, range_no_special)
      if range_no_special[0] != 0:
        e_die("Can't use char %d as end of range in ERE syntax" % term.end.i,
              loc.Span(term.end.spid))

    elif case(char_class_term_e.CharCode):
      term = cast(CharCode, UP_term)

      _CharCodeToEre(term, parts, special_char_flags)

    elif case(char_class_term_e.PerlClass):
      term = cast(perl_class, UP_term)
      n = term.name
      chars = PERL_CLASS[term.name]  # looks like '[:digit:]'
      if term.negated:
        e_die("Perl classes can't be negated in ERE", term.negated)
      else:
        pat = '%s' % chars
      parts.append(pat)

    elif case(char_class_term_e.PosixClass):
      term = cast(posix_class, UP_term)
      n = term.name  # looks like 'digit'
      if term.negated:
        e_die("POSIX classes can't be negated in ERE", term.negated)
      else:
        pat = '[:%s:]' % n
      parts.append(pat)

    else:
      raise AssertionError(term)


def AsPosixEre(node, parts):
  # type: (re_t, List[str]) -> None
  """Translate an Oil regex to a POSIX ERE.

  Appends to a list of parts that you have to join.
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
              "needs () around it.", loc.Span(child.spid))

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

  if tag == re_e.CharClass:
    node = cast(re__CharClass, UP_node)

    # HYPHEN CARET RBRACKET BACKSLASH
    special_char_flags = [0]
    non_special_parts = []  # type: List[str]

    for term in node.terms:
      _CharClassTermToEre(term, non_special_parts, special_char_flags)

    parts.append('[')
    if node.negated:
      parts.append('^')

    # Help the user with some of terrible corner cases

    # - move literal - to end        [ab-] not [a-b]
    # - move literal ^ to end        [x^-] not [^x-]
    # - move literal ] to beginning: []x] not [x]]
    # - double up \\ because of Gawk extension [\\]

    if special_char_flags[0] & FLAG_RBRACKET:
      parts.append(']')

    parts.extend(non_special_parts)

    if special_char_flags[0] & FLAG_BACKSLASH:
      parts.append('\\\\')  # TWO backslashes

    if special_char_flags[0] & FLAG_CARET:
      parts.append('^')

    if special_char_flags[0] & FLAG_HYPHEN:
      parts.append('-')

    parts.append(']')
    return

  raise NotImplementedError(tag)

