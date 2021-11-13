#!/usr/bin/env python3
"""
py3_parse.py

Quick test for a potential rewrite of mycpp.
"""
import ast
import sys


def main(argv):
  for filename in argv[1:]:
    with open(filename) as f:
      contents = f.read()
      try:

        try:
          # Python 3.8+ supports type_comments=True
          # TODO: make a custom build of Python 3.10
          n = ast.parse(contents, type_comments=True)
        except TypeError:
          # Fallback
          n = ast.parse(contents)

      except SyntaxError as e:
        print('Error parsing %s: %s' % (filename, e))
        return 1
      else:

        print('Parsed %s: %s' % (filename, n))
      if 0:
        print()
        print(ast.dump(n))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
