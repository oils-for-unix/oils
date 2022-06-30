#!/usr/bin/env python3
"""
pea_main.py

A potential rewrite of mycpp.
"""
import ast
from ast import AST, stmt, Module, ClassDef, FunctionDef, Assign
import collections
import optparse
import os
from pprint import pprint
import sys
import time

from typing import Optional, Any


START_TIME = time.time()

def log(msg: str, *args: Any) -> None:
  if args:
    msg = msg % args
  print('%.2f %s' % (time.time() - START_TIME, msg), file=sys.stderr)


class Program:
  """The whole program."""

  def __init__(self) -> None:
    self.modules: list[AST] = []

    # As we parse, we add modules, and fill in the dictionaries with parsed
    # types.  Then other passes can retrieve the types with the same
    # dictionaries.

    # right now types are modules?  Could change that
    self.func_types: dict[FunctionDef, AST] = {}  
    self.method_types : dict[FunctionDef, AST] = {}  
    self.class_types : dict[ClassDef, Module] = {}  
    self.assign_types : dict[Assign, Module] = {}  

    self.stats: dict[str, int] = {
        # parsing stats
        'num_files': 0,
        'num_funcs': 0,
        'num_classes': 0,
        'num_methods': 0,
        'num_assign': 0,

        # ConstPass stats
        'num_strings': 0,
    }

  def PrintStats(self) -> None:
    pprint(self.stats)


class TypeSyntaxError(Exception):

  def __init__(self, lineno: int, code_str: str):
    self.lineno = lineno
    self.code_str = code_str


def ParseFuncType(st: stmt) -> AST:
  assert st.type_comment  # caller checks this
  try:
    # This parses with the func_type production in the grammar
    return ast.parse(st.type_comment, mode='func_type')
  except SyntaxError:
    raise TypeSyntaxError(st.lineno, st.type_comment)


def ParseBlock(stmts: list[stmt], prog: Program, indent: int=0) -> None:
  """e.g. body of function, method, etc."""

  #print('STMTS %s' % stmts)

  ind_str = '  ' * indent

  # TODO: Change to a visitor?  So you get all assignments recursively.

  for stmt in stmts:
    match stmt:
      case Assign():
        #print('%s* Assign' % ind_str)
        #print(ast.dump(stmt, indent='  '))

        if stmt.type_comment:
          # This parses with the func_type production in the grammar
          try:
            typ = ast.parse(stmt.type_comment)
          except SyntaxError as e:
            # New syntax error
            raise TypeSyntaxError(stmt.lineno, stmt.type_comment)

          prog.assign_types[stmt] = typ

          #print('%s  TYPE: Assign' % ind_str)
          #print(ast.dump(typ, indent='  '))

        prog.stats['num_assign'] += 1

      case _:
        pass


def ParseClass(cls: ClassDef, prog: Program) -> None:
  #print('* class %s(...)' % cls.name)
  #print()
  for stmt in cls.body:
    match stmt:
      case FunctionDef():
        #print('  * method %s(...)' % stmt.name)
        #print('    ARGS')
        #print(ast.dump(stmt.args, indent='  '))
        if stmt.type_comment:
          sig = ParseFuncType(stmt)
          prog.method_types[stmt] = sig
          #print('    TYPE: method')
          #print(ast.dump(sig, indent='  '))
        #print()
        prog.stats['num_methods'] += 1

        ParseBlock(stmt.body, prog, indent=1)

      case _:
        # Import, Assign, etc.
        # print(stmt)
        pass


def ParseModule(module: Module, prog: Program) -> None:
  for stmt in module.body:
    match stmt:
      case FunctionDef():
        #print('* func %s(...)' % stmt.name)
        #print('  ARGS')
        #print(ast.dump(stmt.args, indent='  '))
        if stmt.type_comment:
          sig = ParseFuncType(stmt)
          prog.func_types[stmt] = sig

          #print('  TYPE: func')
          #print(ast.dump(sig, indent='  '))
        #print()
        prog.stats['num_funcs'] += 1

        ParseBlock(stmt.body, prog, indent=0)

      case ClassDef():
        ParseClass(stmt, prog)
        prog.stats['num_classes'] += 1

      case _:
        # Import, Assign, etc.
        #print(stmt)
        # if __name__ == '__main__'
        pass


def Options() -> optparse.OptionParser:
  """Returns an option parser instance."""

  p = optparse.OptionParser()
  p.add_option(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Show details about translation')

  # Control which modules are exported to the header.
  # - It's used for asdl/runtime.h, which is useful for tests ONLY
  # - TODO: Should we get rid of _build/cpp/osh_eval.h?  Not sure it's used
  p.add_option(
      '--to-header', dest='to_header', action='append', default=[],
      help='Export this module to a header, e.g. frontend.args')

  p.add_option(
      '--header-out', dest='header_out', default=None,
      help='Write this header')

  return p


class ConstVisitor(ast.NodeVisitor):

  def __init__(self, const_lookup: dict[str, int]):
    ast.NodeVisitor.__init__(self)
    self.const_lookup = const_lookup
    self.str_id = 0

  def visit_Constant(self, o: ast.Constant) -> None:
    if isinstance(o.value, str):
      self.const_lookup[o.value] = self.str_id
      self.str_id += 1


def ParseFiles(files: list[str], prog: Program) -> bool:

  for filename in files:
    with open(filename) as f:
      contents = f.read()

    try:
      # Python 3.8+ supports type_comments=True
      module = ast.parse(contents, filename=filename, type_comments=True)
    except SyntaxError as e:
      # This raises an exception for some reason
      #e.print_file_and_line()
      print('Error parsing %s: %s' % (filename, e))
      return False

    prog.modules.append(module)

    #print('Parsed %s: %s' % (filename, module))
    #print()

    try:
      ParseModule(module, prog)
    except TypeSyntaxError as e:
      print('Type comment syntax error on line %d of %s: %r' %
            (e.lineno, filename, e.code_str))
      return False

    prog.stats['num_files'] += 1

  #prog.PrintStats()
  if 0:
    print(prog.func_types)
    print(prog.method_types)

  return True


def main(argv: list[str]) -> int:

  action = argv[1]

  if action == 'parse':

    files = argv[2:]

    prog = Program()

    # module -> class/method, func; and recursive visitor for Assign
    log('Pea begin')
    if not ParseFiles(files, prog):
      return 1
    log('Parsed %d files and their type comments', len(files))
    prog.PrintStats()

    const_lookup: dict[str, int] = {}  

    v = ConstVisitor(const_lookup)
    for module in prog.modules:
      v.visit(module)

    log('Collected %d constants', len(const_lookup))

    # TODO: respect header_out for these two passes

    # module -> class
    log('Forward Declarations') 

    # module -> class/method, func
    log('Prototypes') 

    # module -> class/method, func; then probably a fully recursive thing
    log('Implementation') 

    #prog.PrintStats()

    log('Done')


  elif action == 'cpp':
    files = argv[2:]
    print('// PEA C++')

  else:
    raise RuntimeError('Invalid action %r' % action)

  return 0


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
