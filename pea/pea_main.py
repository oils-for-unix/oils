#!/usr/bin/env python3
"""
pea_main.py

A potential rewrite of mycpp.
"""
import ast
from ast import stmt, Module, ClassDef, FunctionDef, Assign
import collections

from typing import List

import os
import sys


class TypeSyntaxError(Exception):

  def __init__(self, lineno, code_str):
    self.lineno = lineno
    self.code_str = code_str


def ParseFuncType(stmt):
  try:
    # This parses with the func_type production in the grammar
    return ast.parse(stmt.type_comment, mode='func_type')
  except SyntaxError:
    raise TypeSyntaxError(stmt.lineno, stmt.type_comment)


def DoBlock(stmts: List[stmt], stats: dict[str, int], indent=0) -> None:
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


def main(argv: list[str]) -> int:

  stats: dict[str, int] = {
      'num_funcs': 0,
      'num_classes': 0,
      'num_methods': 0,
      'num_assign': 0,
  }

  for filename in argv[1:]:
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
  return 0


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
