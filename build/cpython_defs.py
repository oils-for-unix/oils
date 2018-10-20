#!/usr/bin/env python
"""
parse_cpython.py
"""
from __future__ import print_function

import errno
import os
import re
import sys

from core.lexer import C, R
from core.util import log


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
  C(r'FILE', 'FILE'),
  C(r'PyDoc_STR(', 'LDocStr'),
  C(r')', 'RDocStr'),
  R(r'[^,}\n]+', 'Opaque'),
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
      log('%s %r', self.tok_id, self.tok_val)

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
    Val = Str
        | Opaque
        | LDocStr Str+ RDocStr   # string concatenation happens
    """
    if self.tok_id == 'LDocStr':
      self.Next()

      val = self.tok_val
      self.Eat('Str')
      while self.tok_id == 'Str':
        val += self.tok_val
        self.Next()

      self.Eat('RDocStr')

    elif self.tok_id in ('Opaque', 'Str'):
      val = self.tok_val
      self.Next()

    else:
      raise RuntimeError('Unexpected token %r' % self.tok_id)

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

  def ParseHeader(self):
    self.Eat('FILE')
    path = self.tok_val
    self.Eat('Opaque')
    return path 

  def ParseFile(self):
    """
    File = Header Def*
    """
    path = self.ParseHeader()
    defs = []
    while self.tok_id not in ('FILE', 'EOF'):
      defs.append(self.ParseDef())

    return path, defs

  def ParseStream(self):
    """
    Stream = File*
    """
    files = []
    while self.tok_id != 'EOF':
      files.append(self.ParseFile())

    return files


def PrettyPrint(def_name, entries, predicate, f, stats):
  def out(msg, *args):
    if args:
      msg = msg % args
    print(msg, file=f, end='')

  out('static PyMethodDef %s[] = {\n', def_name)
  for entry_name, vals in entries:
    if not predicate(def_name, entry_name):
      continue

    if entry_name is None:
      out('  {0},\n')  # null initializer
      continue
    out('  {"%s", ', entry_name)
    # Strip off the docstring.
    out(', '.join(vals[:-1]))
    out('},\n')
    stats['num_methods'] += 1
  out('};\n')


def OilMethodFilter(def_name, method_name):
  # NOTE: asdl/unpickle.py needs marshal.loads
  if def_name == 'marshal_methods' and method_name in ('dump', 'dumps'):
    return False
  #log('= %s %s', def_name, method_name)

  return True


def main(argv):
  action = argv[1]

  tokens = Lexer(C_DEF).Tokens(sys.stdin.read())

  if action == 'lex':  # for debugging
    while True:
      id_, value = tokens.next()
      print('%s\t%r' % (id_, value))
      if id_ == 'EOF':
        break

  elif action == 'parse':  # for debugging
    p = Parser(tokens)
    files = p.ParseStream()
    for path, defs in files:
      for def_name, entries in defs:
        if def_name == 'proxy_methods':
        #if def_name == 'object_methods':
          for method_name, vals in entries:
            print(method_name, vals)

  elif action == 'filter':  # for slimming the build down
    out_dir = argv[2]

    p = Parser(tokens)
    files = p.ParseStream()

    # Print to files.

    stats = {'num_methods': 0, 'num_defs': 0}
    for rel_path, defs in files:
      # Make a directory for each .c file!  Each file is a def.
      c_dir = os.path.join(out_dir, rel_path)
      try:
        os.makedirs(c_dir)
      except OSError as e:
        if e.errno != errno.EEXIST:
          raise

      for def_name, entries in defs:
        out_path = os.path.join(c_dir, '%s.def' % def_name)

        # TODO: Write a separate file here for each one.  We have to include a
        # different file at each definition.

        with open(out_path, 'w') as f:
          print('// %s' % rel_path, file=f)
          print('', file=f)
          PrettyPrint(def_name, entries, OilMethodFilter, f, stats)

        stats['num_defs'] += 1
        log('Wrote %s', out_path)

    log('cpython_defs.py: Printed %(num_methods)d methods in %(num_defs)d '
        'definitions' % stats)

  elif action == 'tsv':
    p = Parser(tokens)
    files = p.ParseStream()
    header = ['file', 'def_name', 'py_method_name', 'c_symbol_name', 'flags']
    print('\t'.join(header))
    for rel_path, defs in files:
      for def_name, entries in defs:
        for method_name, vals in entries:
          if method_name is None:
            continue
          # TODO: The c_symbol_name could be parsed better.  It sometimes has
          # "(PyCFunction)" on the front of it.

          row = [rel_path, def_name, method_name, vals[0], vals[1]]
          print('\t'.join(row))

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
