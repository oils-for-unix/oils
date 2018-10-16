#!/usr/bin/python
"""
parse_cpython.py
"""
from __future__ import print_function

import re
import sys

from core.lexer import C, R


C_DEF = [
  R(r'#.*', 'Comment'),
  R(r'[ \t\n]+', 'Whitespace'),

  # This could be more space-insensitive.
  R(r'static PyMethodDef[ \n]+(.*)\[\] = ', 'BeginDef'),
  C(r'{', 'LBrace'),
  C(r'}', 'RBrace'),
  C(r',', 'Comma'),
  C(r';', 'Semi'),
  R(r'"([^"]*)"', 'Str'),
  R(r'[^,}]+', 'Opaque'),
]


# NOTE: This is copied from osh/match.py because we don't have 're' there.
def _CompileAll(pat_list):
  result = []
  for is_regex, pat, token_id in pat_list:
    if not is_regex:
      pat = re.escape(pat)  # turn $ into \$
    result.append((re.compile(pat), token_id))
  return result


class Lexer(object):
  def __init__(self, pat_list):
    self.pat_list = _CompileAll(pat_list)

  def Tokens(self, s):
    pos = 0
    n = len(s)
    while pos < n:
      for pat, id_ in self.pat_list:
        # FIRST MATCH
        m = pat.match(s, pos)
        if m:
          if m.groups():
            start, end = m.start(1), m.end(1)
          else:
            start, end = m.start(0), m.end(0)
          pos = m.end()
          break  # found a match
      else:
        raise AssertionError(
            'no token matched at position %r: %r' % ( pos, s[pos]))

      if id_ != 'Whitespace':
        yield id_, s[start:end]
    yield 'EOF', ''


class Parser(object):
  """Parser for C PyMethodDef initializer lists."""

  def __init__(self, tokens):
    self.tokens = tokens
    self.Next()  # initialize

  def Next(self):
    while True:
      self.tok_id, self.tok_val = self.tokens.next()
      if self.tok_id not in ('Comment', 'Whitespace'):
        break
    if 0:
      print('%s %r' % (self.tok_id, self.tok_val))

  def Eat(self, tok_id):
    if self.tok_id != tok_id:
      raise RuntimeError('Expected %r, got %r' % (tok_id, self.tok_id))
    self.Next()

  def ParseName(self):
    """
    Name = Str | Opaque('NULL') | Opaque('0')
    """
    if self.tok_id == 'Str':
      name = self.tok_val
    elif self.tok_id == 'Opaque':
      assert self.tok_val in ('NULL', '0')
      name = None
    else:
      raise RuntimeError('Unexpected token %r' % self.tok_id)
    self.Next()
    return name

  def ParseVal(self):
    """
    Val = Str | Opaque 
    """
    if self.tok_id not in ('Opaque', 'Str'):
      raise RuntimeError('Unexpected token %r' % self.tok_id)
    val = self.tok_val
    self.Next()
    return val

  def ParseItem(self):
    """
    Item = '{' Name (',' Val)+ '}' ','?
    """
    self.Eat('LBrace')
    name = self.ParseName()

    vals = []
    while self.tok_id == 'Comma':
      self.Next()
      vals.append(self.ParseVal())

    self.Eat('RBrace')

    if self.tok_id == 'Comma':  # Optional
      self.Next()

    return name, vals

  def ParseDef(self):
    """
    Def = BeginDef '{' Item+ '}' ';'
    """
    def_name = self.tok_val
    self.Eat('BeginDef')
    self.Eat('LBrace')

    items = []
    while self.tok_id != 'RBrace':
      items.append(self.ParseItem())

    self.Next()
    self.Eat('Semi')

    return (def_name, items)

  def ParseFile(self):
    """
    File = Def*
    """
    defs = []
    while self.tok_id != 'EOF':
      defs.append(self.ParseDef())

    return defs


def main(argv):
  tokens = Lexer(C_DEF).Tokens(sys.stdin.read())
  if 1:
    p = Parser(tokens)
    defs = p.ParseFile()
    for d in defs:
      name, entries = d
      print()
      print('-- %s' % name)
      for e in entries:
        print(e)
  else:
    # Print all tokens.
    while True:
      id_, value = tokens.next()
      print('%s\t%r' % (id_, value))
      if id_ == 'EOF':
        break


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
