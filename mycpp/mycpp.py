#!/usr/bin/env python3
"""
mycpp.py - Translate a subset of Python to C++, using MyPy's typed AST.
"""
from __future__ import print_function

import os
import sys

from typing import List, Optional, Tuple

from mypy.build import build as mypy_build
from mypy.build import BuildSource
from mypy.main import process_options
from mypy.options import Options

import const_pass
import cppgen_pass
import debug_pass

from util import log


# Copied from mypyc/build.py
def get_mypy_config(paths: List[str],
                    mypy_options: Optional[List[str]]) -> Tuple[List[BuildSource], Options]:
    """Construct mypy BuildSources and Options from file and options lists"""
    # It is kind of silly to do this but oh well
    mypy_options = mypy_options or []
    mypy_options.append('--')
    mypy_options.extend(paths)

    sources, options = process_options(mypy_options)

    # OSH PATCH
    #if options.python_version[0] == 2:
    if 0:
        fail('Python 2 not supported')

    # OSH Patch!
    #if not options.strict_optional:
    if 0:
        fail('Disabling strict optional checking not supported')

    options.show_traceback = True
    # Needed to get types for all AST nodes
    options.export_types = True
    # TODO: Support incremental checking
    options.incremental = False

    for source in sources:
        options.per_module_options.setdefault(source.module, {})['mypyc'] = True

    return sources, options


def main(argv):
  # TODO: Put these in the shell script
  mypy_options = [
      '--py2', '--strict', '--no-implicit-optional', '--no-strict-optional'
  ]
     
  paths = argv[1:]  # e.g. asdl/typed_arith_parse.py

  # convert to 'typed_arith_parse'
  mod_names = [os.path.basename(p) for p in paths]
  mod_names = [os.path.splitext(name)[0] for name in mod_names]

  sources, options = get_mypy_config(paths, mypy_options)
  log('sources %s', sources)
  log('options %s', sources)

  #result = emitmodule.parse_and_typecheck(sources, options)
  import time
  start_time = time.time()
  result = mypy_build(sources=sources, options=options)
  log('elapsed 1: %f', time.time() - start_time)

  if result.errors:
    log('')
    log('-'* 80)
    for e in result.errors:
      log(e)
    log('-'* 80)
    log('')

  # Important functions in mypyc/build.py:
  #
  # generate_c (251 lines)
  #   parse_and_typecheck
  #   compile_modules_to_c

  # mypyc/emitmodule.py (487 lines)
  # def compile_modules_to_c(result: BuildResult, module_names: List[str],
  # class ModuleGenerator:
  #   # This generates a whole bunch of textual code!

  # literals, modules, errors = genops.build_ir(file_nodes, result.graph,
  # result.types)

  # no-op
  for name in result.graph:
    state = result.graph[name]

  # Print the tree for debugging
  if 1:
    for name, module in result.files.items():
      #print(name)

      builder = debug_pass.Print(result.types)
      builder.visit_mypy_file(module)

  # GLOBAL Constant pass over all modules.  We want to collect duplicate
  # strings together.  And have globally unique IDs str0, str1, ... strN.
  const_lookup = {}
  const_code = []
  p1 = const_pass.Collect(result.types, const_lookup, const_code)

  for name, module in result.files.items():
    # Only translate files that were mentioned on the command line
    suffix = name.split('.')[-1]
    if suffix not in mod_names:
      continue
    p1.visit_mypy_file(module)

  # Collect constants and then emit code.
  f = sys.stdout

  # Instead of top-level code, should we generate a function and call it
  # from main?
  for line in const_code:
    f.write('%s\n' % line)
  f.write('\n')

  for name, module in result.files.items():
    # Only translate files that were mentioned on the command line
    suffix = name.split('.')[-1]
    if suffix not in mod_names:
      continue

    #print(name)
    p2 = cppgen_pass.Generate(result.types, const_lookup, f)
    p2.visit_mypy_file(module)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
