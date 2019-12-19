#!/usr/bin/env python2
"""
parse_cpython.py
"""
from __future__ import print_function

import errno
import os
import re
import sys

from core.util import log
# TODO: Could move these to a place where they don't depend on Oil
from frontend.lex import C, R


C_DEF = [
  R(r'#.*', 'Comment'),
  R(r'[ \t\n]+', 'Whitespace'),

  # This could be more space-insensitive.
  R(r'static.*PyMethodDef (.*)\[\]\s*=\s*', 'BeginDef'),
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
        yield id_, s[start:end], pos
    yield 'EOF', '', -1


class Parser(object):
  """Parser for C PyMethodDef initializer lists."""

  def __init__(self, tokens):
    self.tokens = tokens
    self.Next()  # initialize

  def Next(self):
    while True:
      self.tok_id, self.tok_val, self.pos = self.tokens.next()
      if self.tok_id not in ('Comment', 'Whitespace'):
        break
    if 0:
      log('%s %r', self.tok_id, self.tok_val)

  def Eat(self, tok_id):
    if self.tok_id != tok_id:
      raise RuntimeError(
          'Expected %r, got %r %r (byte offset %d)' %
          (tok_id, self.tok_id, self.tok_val, self.pos))

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


def PrettyPrint(rel_path, def_name, entries, predicate, f, stats):
  def out(msg, *args):
    if args:
      msg = msg % args
    print(msg, file=f, end='')

  out('static PyMethodDef %s[] = {\n', def_name)
  for entry_name, vals in entries:
    if entry_name is None:
      out('  {0},\n')  # null initializer
      continue
    stats['num_methods'] += 1

    if not predicate(rel_path, def_name, entry_name):
      stats['num_filtered'] += 1
      continue

    # Reprint the definition, but omit the docstring.
    out('  {"%s", ', entry_name)
    out(vals[0])  # The C function
    out(', ')
    out(vals[1])  # The flags
    out('},\n')
  out('};\n')


MODULES_TO_FILTER = [
    # My Own
    'libc.c',
    'fastlex.c',
    'line_input.c',

    'import.c',
    'marshal.c',  # additional filters below
    #'zipimport.c',  # Cannot filter this because find_module called from C!

    # Types for Builtins
    'enumobject.c',
    'rangeobject.c',

    # Interpreter types
    'descrobject.c',
    'exceptions.c',
    'structseq.c',
    '_warnings.c',

    # Control flow
    'frameobject.c',
    'genobject.c',
    'iterobject.c',

    # GC
    '_weakref.c',
    'weakrefobject.c',
    'gcmodule.c',

    # "Data types"
    #'boolobject.c',  # No defs
    'cStringIO.c',
    'dictobject.c',
    'fileobject.c',
    'floatobject.c',
    'intobject.c',
    'listobject.c',
    'longobject.c',
    #'moduleobject.c',  # No defs
    'setobject.c',
    'stringobject.c',
    'tupleobject.c',
    'sliceobject.c',
    'typeobject.c',

    # Builtins
    'bltinmodule.c',  # additional filters below
    #'sysmodule.c',  # Filtered below

    # Libraries
    'errnomodule.c',  # has no methods, but include it for completeness
    'fcntlmodule.c',
    'posixmodule.c',
    'pwdmodule.c',
    'readline.c',
    'resource.c',
    'signalmodule.c',
    'timemodule.c',
    'termios.c',
]


class OilMethodFilter(object):

  def __init__(self, py_names):
    self.py_names = py_names

  def __call__(self, rel_path, def_name, method_name):
    basename = os.path.basename(rel_path) 

    if method_name == 'count':  # False positive for {str,list,tuple}.count()
      return False

    # enter/exit needed for 'with open'.  __length_hint__ is an optimization.
    if method_name in ('__enter__', '__exit__', '__length_hint__'):
      return True
    # Notes:
    # - __reduce__ and __setstate__ are for pickle.  And I think
    #   __getnewargs__.
    # - Do we need __sizeof__?  Is that for sys.getsizeof()?

    # NOTE: LoadOilGrammar needs marshal.loads().
    # False positive for yajl.dumps() and load()
    if basename == 'marshal.c' and method_name in ('dump', 'dumps', 'load'):
      return False

    # Auto-filtering gave false-positives here.
    # We don't need top-level next().  The method should be good enough.
    # iter is a field name
    if (basename == 'bltinmodule.c' and
        method_name in ('compile', 'format', 'next', 'vars', 'iter')):
      return False
    if basename == 'bltinmodule.c':
      # Get "bootstrapping error" without this.
      if method_name == '__import__':
        return True

    if basename == '_warnings.c' and method_name == 'warn':
      return False

    if basename == 'tupleobject.c' and method_name == 'index':
      return False

    if basename == 'setobject.c' and method_name == 'pop':
      return False

    if basename == 'sliceobject.c' and method_name == 'indices':
      return False

    if basename == 'genobject.c' and method_name == 'close':  # Shadowed
      return False

    # We're using list.remove()
    if basename == 'posixmodule.c' and method_name == 'remove':  # Shadowed
      return False

    # We're using dict.clear() and list.remove()
    if basename == 'setobject.c' and method_name in ('clear', 'remove'):
      return False

    # Do custom filtering here.
    if (basename == 'sysmodule.c' and method_name not in self.py_names):
      # These can't be removed or they cause assertions!
      if method_name not in ('displayhook', 'excepthook'):
        return False

    # This one is called from C.
    if basename == 'signalmodule.c' and method_name == 'default_int_handler':
      return True

    # segfault without this
    if basename == 'typeobject.c' and method_name == '__new__':
      return True

    if basename == 'descrobject.c':
      # Apparently used for dir() on class namespace, as in dir(Id).
      if method_name == 'keys':
        return True
      return False

    # Try just filtering {time,pwd,posix}module.c, etc.
    if basename in MODULES_TO_FILTER and method_name not in self.py_names:
      return False

    #log('= %s %s', def_name, method_name)

    # If it doesn't appear in the .py source, it can't be used.  (Execption: it
    # coudl be used in C source with dynamic lookup?  But I don't think CPython
    # does that.)
    #if method_name not in self.py_names:
    if 0:
      log('Omitting %r', method_name)
      return False

    return True


def main(argv):
  action = argv[1]

  try:
    py_names_path = argv[2]
  except IndexError:
    method_filter = None
  else:
    py_names = set()
    with open(py_names_path) as f:
      for line in f:
        py_names.add(line.strip())
    method_filter = OilMethodFilter(py_names)

  if action == 'filtered':
    tokens = None
  else:
    tokens = Lexer(C_DEF).Tokens(sys.stdin.read())

  if action == 'lex':  # for debugging
    while True:
      id_, value, pos = tokens.next()
      print('%s\t%r' % (id_, value))
      if id_ == 'EOF':
        break

  elif action == 'audit':  # show after filtering, for debugging
    p = Parser(tokens)
    files = p.ParseStream()
    for rel_path, defs in files:
      basename = os.path.basename(rel_path)

      print(rel_path)
      for def_name, entries in defs:
        print('\t' + def_name)
        for method_name, vals in entries:
          if method_name is None:
            continue
          if not method_filter(rel_path, def_name, method_name):
            continue
          print('\t\t%s %s' % (method_name, vals))

  elif action == 'filter':  # for slimming the build down
    out_dir = argv[3]

    p = Parser(tokens)
    files = p.ParseStream()

    # Print to files.

    stats = {'num_methods': 0, 'num_defs': 0, 'num_filtered': 0}
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
          PrettyPrint(rel_path, def_name, entries, method_filter, f, stats)

        stats['num_defs'] += 1
        log('Wrote %s', out_path)

    stats['num_left'] = stats['num_methods'] - stats['num_filtered']
    log('cpython_defs.py: Filtered %(num_filtered)d of %(num_methods)d methods, '
        'leaving %(num_left)d (from %(num_defs)d definitions)' % stats)

  elif action == 'tsv':
    p = Parser(tokens)
    files = p.ParseStream()
    header = [
        'file', 'def_name', 'py_method_name', 'c_symbol_name', 'flags',
        'used'
    ]
    print('\t'.join(header))
    for rel_path, defs in files:
      for def_name, entries in defs:
        for method_name, vals in entries:
          if method_name is None:
            continue
          b = method_filter(rel_path, def_name, method_name)
          used = 'T' if b else 'F'

          # TODO: The c_symbol_name could be parsed better.  It sometimes has
          # "(PyCFunction)" on the front of it.

          row = [rel_path, def_name, method_name, vals[0], vals[1], used]
          print('\t'.join(row))

  elif action == 'filtered':
    for name in MODULES_TO_FILTER:
      print(name)

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
