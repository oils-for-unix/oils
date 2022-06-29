#!/usr/bin/env python3
"""
pea_main.py

A potential rewrite of mycpp.
"""
import ast
from ast import AST, stmt, Module, ClassDef, FunctionDef, Assign
import collections

from typing import Optional, List

import optparse
import os
import sys


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


def DoBlock(stmts: List[stmt], stats: dict[str, int], indent: int=0) -> None:
  """e.g. body of function, method, etc."""

  #print('STMTS %s' % stmts)

  ind_str = '  ' * indent

  for stmt in stmts:
    match stmt:
      case Assign():
        print('%s* Assign' % ind_str)
        print(ast.dump(stmt, indent='  '))

        if stmt.type_comment:
          # This parses with the func_type production in the grammar
          try:
            typ = ast.parse(stmt.type_comment)
          except SyntaxError as e:
            # New syntax error
            raise TypeSyntaxError(stmt.lineno, stmt.type_comment)

          print('%s  TYPE: Assign' % ind_str)
          print(ast.dump(typ, indent='  '))

        stats['num_assign'] += 1

      case _:
        pass


def DoClass(cls: ClassDef, stats: dict[str, int]) -> None:
  # TODO:
  # - Parse type comments out of __init__() like self.field = field
  print('* class %s(...)' % cls.name)
  print()
  for stmt in cls.body:
    match stmt:
      case FunctionDef():
        print('  * method %s(...)' % stmt.name)
        print('    ARGS')
        print(ast.dump(stmt.args, indent='  '))
        if stmt.type_comment:
          sig = ParseFuncType(stmt)
          print('    TYPE: method')
          print(ast.dump(sig, indent='  '))
        print()
        stats['num_methods'] += 1

        DoBlock(stmt.body, stats, indent=1)

      case _:
        # Import, Assign, etc.
        # print(stmt)
        pass


def DoModule(module: Module, stats: dict[str, int]) -> None:
  for stmt in module.body:
    match stmt:
      case FunctionDef():
        print('* func %s(...)' % stmt.name)
        print('  ARGS')
        print(ast.dump(stmt.args, indent='  '))
        if stmt.type_comment:
          sig = ParseFuncType(stmt)
          print('  TYPE: func')
          print(ast.dump(sig, indent='  '))
        print()
        stats['num_funcs'] += 1

        DoBlock(stmt.body, stats, indent=0)

      case ClassDef():
        DoClass(stmt, stats)
        stats['num_classes'] += 1

      case _:
        # Import, Assign, etc.
        #print(stmt)
        # if __name__ == '__main__'
        pass

  ast_dump = os.getenv('AST_DUMP')
  if ast_dump:
    print()
    print(ast.dump(module))


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


def main(argv: list[str]) -> int:

  action = argv[1]

  if action == 'parse':

    files = argv[2:]
    stats: dict[str, int] = {
        'num_files': len(files),
        'num_funcs': 0,
        'num_classes': 0,
        'num_methods': 0,
        'num_assign': 0,
    }

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
        return 1

      print('Parsed %s: %s' % (filename, module))
      print()

      try:
        DoModule(module, stats)
      except TypeSyntaxError as e:
        print('Type comment syntax error on line %d of %s: %r' %
              (e.lineno, filename, e.code_str))
        return 1

    print(stats)

  elif action == 'cpp':
    files = argv[2:]

    def ParseAll(files: list[str]) -> list[AST]:
      pass

    # Parse them all up front?
    prog = ParseAll(files)

    #ConstPass(prog)
    #ForwardDeclPass(prog)
    #PrototypesPass(prog)
    #ImplPass(prog)

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
