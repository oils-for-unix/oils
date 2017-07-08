#!/usr/bin/env python -S
"""
runpy_deps.py

NOTE: -S above is important.
"""

import sys  # 15 modules
import runpy  # 34 modules


def main(argv):
  path_prefix = argv[1]

  py_out_path = path_prefix + '/runpy-deps-py.txt'
  c_out_path = path_prefix + '/runpy-deps-c.txt'

  runpy_path = runpy.__file__
  i = runpy_path.rfind('/')
  assert i != -1, runpy_path
  stdlib_dir = runpy_path[: i + 1]  # include trailing slash
  stdlib_dir_len = len(stdlib_dir)

  with open(py_out_path, 'w') as py_out, open(c_out_path, 'w') as c_out:
    for name in sorted(sys.modules):
      mod = sys.modules[name]
      if name in ('__builtin__', '__main__'):
        continue

      try:
        full_path = mod.__file__
      except AttributeError:
        full_path = None

      # If it's cached, it will be under .pyc; otherwise under .py.
      if full_path and full_path.endswith('.py'):
        py_path = full_path
        pyc_path = full_path + 'c'
      elif full_path and full_path.endswith('.pyc'):
        pyc_path = full_path
        py_path = full_path[:-1]
      else:
        # Print a different format for C modules.
        print >>c_out, name, full_path

      if py_path:
        if py_path.startswith(stdlib_dir):
          rel_py_path = py_path[stdlib_dir_len:]
        else:
          rel_py_path = py_path

        # .pyc file for execution
        print >>py_out, py_path + 'c', rel_py_path + 'c'
        # .py file for tracebacks
        print >>py_out, py_path, rel_py_path

  print >>sys.stderr, '-- Wrote %s and %s' % (py_out_path, c_out_path)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
