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
      # TODO: we need Python 3.8 or 3.10 because they support type_comments=True
      try:
        n = ast.parse(f.read())
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
