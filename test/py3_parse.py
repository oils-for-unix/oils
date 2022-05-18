#!/usr/bin/env python3
"""
py3_parse.py

Quick test for a potential rewrite of mycpp.
"""
import ast
from ast import Module, ClassDef, FunctionDef
import collections

import os
import sys


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
          # This parses with the func_type production in the grammar
          sig = ast.parse(stmt.type_comment, mode='func_type')
          print('    TYPE')
          print(ast.dump(sig, indent='  '))
        print()
        stats['num_methods'] += 1

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
          # This parses with the func_type production in the grammar
          sig = ast.parse(stmt.type_comment, mode='func_type')
          print('  TYPE')
          print(ast.dump(sig, indent='  '))
        print()
        stats['num_funcs'] += 1

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
  }

  for filename in argv[1:]:
    with open(filename) as f:
      contents = f.read()

    try:
      # Python 3.8+ supports type_comments=True
      module = ast.parse(contents, type_comments=True)
    except SyntaxError as e:
      print('Error parsing %s: %s' % (filename, e))
      return 1

    print('Parsed %s: %s' % (filename, module))
    print()

    DoModule(module, stats)

  print(stats)
  return 0


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
