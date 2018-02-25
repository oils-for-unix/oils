#!/usr/bin/python -S
"""
runpy_deps.py

NOTE: -S above is important.
"""

import sys  # 15 modules
import runpy  # 34 modules

PY_MODULE = 0
C_MODULE = 1


def FilterModules(modules, stdlib_dir):
  stdlib_dir_len = len(stdlib_dir)

  for name in sorted(modules):
    mod = modules[name]
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
      yield C_MODULE, name, full_path

    if py_path:
      if py_path.startswith(stdlib_dir):
        rel_py_path = py_path[stdlib_dir_len:]
      else:
        rel_py_path = py_path

      # .pyc file for execution
      yield PY_MODULE, py_path, rel_py_path


def main(argv):
  runpy_path = runpy.__file__
  i = runpy_path.rfind('/')
  assert i != -1, runpy_path
  stdlib_dir = runpy_path[: i + 1]  # include trailing slash

  action = argv[1]

  if action == 'both':
    path_prefix = argv[2]

    py_out_path = path_prefix + '/runpy-deps-cpython.txt'
    c_out_path = path_prefix + '/runpy-deps-c.txt'

    # NOTE: This is very similar to build/app_deps.py.
    with open(py_out_path, 'w') as py_out, open(c_out_path, 'w') as c_out:
      for mod_type, x, y in FilterModules(sys.modules, stdlib_dir):
        if mod_type == PY_MODULE:
          print >>py_out, x, y
          print >>py_out, x + 'c', y + 'c'  # .pyc goes in bytecode.zip too
          pass

        elif mod_type == C_MODULE:
          print >>c_out, x, y  # mod_name, full_path

        else:
          raise AssertionError(mod_type)

    print >>sys.stderr, '-- Wrote %s and %s' % (py_out_path, c_out_path)

  elif action == 'py':
    for mod_type, full_path, rel_path in \
        FilterModules(sys.modules, stdlib_dir):
      if mod_type == PY_MODULE:
        opy_input = full_path
        opy_output = rel_path + 'c'  # output is .pyc
        print opy_input, opy_output

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, '%s: %s' % (sys.argv[0], e.args[0])
    sys.exit(1)
