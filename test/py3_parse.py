#!/usr/bin/env python3
"""
py3_parse.py

Quick test for a potential rewrite of mycpp.
"""
import ast
import os
import sys


#def main(argv) -> None:
def main(argv):
  ast_dump = os.getenv('AST_DUMP')

  # Python 3.8+ supports type_comments=True
  # TODO: make a custom build of Python 3.10
  try:
    n = ast.parse('', type_comments=True)
  except TypeError:
    type_comments = False
  else:
    type_comments = True

  for filename in argv[1:]:
    with open(filename) as f:
      contents = f.read()

    try:
      if type_comments:
        module = ast.parse(contents, type_comments=True)
      else:
        module = ast.parse(contents)
    except SyntaxError as e:
      print('Error parsing %s: %s' % (filename, e))
      return 1

    print('Parsed %s: %s' % (filename, module))

    # TODO:
    # - Use Python 3.10 and match statements here!
    # - Parse type comments out of __init__() like self.field = field
    if type_comments:
      for stmt in module.body:
        if isinstance(stmt, ast.FunctionDef):
          print()
          print('* %s(...)' % stmt.name)
          if stmt.type_comment:
            # This parses with the func_type production in the grammar
            sig = ast.parse(stmt.type_comment, mode='func_type')
            #print('  %s' % sig)
            print(ast.dump(sig, indent='  '))
      print()

    if ast_dump:
      print()
      print(ast.dump(module))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
