"""
resolve.py

TODO: Instead of pickling everything separately, copy sys.modules
into a dict of dicts.

{ 'osh.cmd_parse': { ... },  # dict instead of a module
  'osh.bool_parse': { ... },
}
Then I think the sharing will work.

- Hook this up to oheap2.py?
  - Instead of only pickling code objects (with string/tuple/int), you can
    pickle a graph of user-defined classes after running?  Just like pickle.py
    does it.
  - Well I was thinking of doing that INSIDE OVM2, rather than in CPython.  But
    either way would work.

- Combine callgraph.py and this module?
  - resolve.py find all functions/classes/globals via sys.modules
  - callgraph.py finds all of them via use in the bytecode

- We should produce a unified report and double check.
- Might also need to combine them with build/cpython-defs.py.
  - We also need the mapping from filenames to modules, which is really in the
    build system.  _build/oil/module_init.c has the names and extern
    declarations.  We could manually make a list.
"""
from __future__ import print_function

import sys
import pickle
import copy_reg  # dependency of pickle, exclude it
import types

from core.util import log
from pylib import unpickle

import __builtin__  # this is not __builtins__


def banner(msg):
  log('')
  log(msg)
  log('')


def PrintVars(global_vars):
  banner('VARIABLES')
  global_vars.sort()  # sort by module name

  import collections
  type_hist = collections.Counter()

  # 316 globals / constants (513 before deduping)
  for (mod_name, name, obj) in global_vars:
    log('%-15s %-15s %r', mod_name, name, obj)
    type_hist[str(type(obj))] += 1

  # ID_SPEC is in core/meta and frontend/lex
  for (mod_name, name, obj) in global_vars:
    if 'IdSpec' in str(type(obj)):
      log('%-20s %-15s %r', mod_name, name, obj)
  log('')

  return type_hist


def PrintFuncs(funcs):
  banner('FUNCTIONS')
  funcs.sort()  # sort by module name

  import collections
  type_hist = collections.Counter()

  # 316 globals / constants (513 before deduping)
  for (mod_name, name, obj) in funcs:
    log('%-20s %-15s %r', mod_name, name, obj)


OMITTED = (
    '__class__', '__dict__', '__doc__', '__getattribute__', '__module__',
    '__reduce__', '__slots__', '__subclasshook__')

def PrintClasses(classes):
  banner('CLASSES')

  classes.sort()  # sort by module name

  import collections
  type_hist = collections.Counter()

  num_methods = 0

  # Keep ALL unbound methods, so that we force them to have different IDs!
  # https://stackoverflow.com/questions/13348031/ids-of-bound-and-unbound-method-objects-sometimes-the-same-for-different-o
  # If we remove this, then the de-duping doesn't work properly.  unbound
  # methods use the silly descriptor protocol.

  all_unbound = []
  seen_ids = set()

  # 316 globals / constants (513 before deduping)
  for (mod_name, name, obj) in classes:
    log('%-20s %-15s %r', mod_name, name, obj)
    names = []
    for name in dir(obj):
      if name in OMITTED:
        continue

      f = getattr(obj, name)
      all_unbound.append(f)

      id_ = id(f)
      if id_ in seen_ids and not isinstance(f, (bool, int, types.NoneType)):
        #log('skipping %s = %s with id %d', name, f, id_)
        continue
        #pass
      seen_ids.add(id_)

      type_hist[str(type(f))] += 1

      #log('%s %s' , f, type(f))
      # There are A LOT of other types.  Classes are complicated.
      if isinstance(f, types.MethodType):
        names.append(name)

      # user-defined class attributes shouldn't be used
      # None is the tag for SimpleObj.
      if isinstance(f, (bool, int, long, tuple, list, dict, set, str, type, types.NoneType)):
        log('  (C) %s %s', name, f)

    names.sort()
    for n in names:
      log('  %s', n)
      num_methods += 1

  return num_methods, type_hist


def Walk(mod_dict):
  """
  Test if the objects in Oil can be pickled.
  """
  #print(sys.modules)
  #d = dict(sys.modules)  # prevent copies

  # vars that aren't not classes or functions, which are presumed to be
  # constant
  global_vars = []
  classes = []  # user-defined classes
  funcs = []  # functions

  seen_ids = set()  # id

  num_objects = 0
  num_modules = 0
  n = 0
  for mod_name, mod in mod_dict.iteritems():
    if mod is pickle:
      continue
    if mod is copy_reg:
      continue
    if mod is unpickle:
      continue
    if mod is sys:  # get rid of it
      continue
    if mod is types:  # lots of stuff here no
      continue

    names = dir(mod)
    log('mod %s', mod)
    for name in names:
      if not name.startswith('__'):
        obj = getattr(mod, name)

        id_ = id(obj)
        if id_ in seen_ids:
          continue
        seen_ids.add(id_)

        log('%r = %r', name, obj)
        if isinstance(obj, types.ModuleType):  # e.g. ASDL modules
          continue
        if isinstance(obj, types.FileType):  # types_asdl.pickle is opened
          continue
        if name == 'Struct':  # struct module
          continue
        if name in ('InputType', 'OutputType', 'cStringIO_CAPI'):  # cStringIO
          continue
        if name in ('_pattern_type',):  # re
          continue
        if obj is __builtin__.Ellipsis:
          continue
        if obj is __builtin__.NotImplemented:
          continue
        if obj is types.BuiltinFunctionType:
          continue
        if obj is types.ClassType:
          continue
        if obj is mod_dict:  # circular!
          continue

        s = pickle.dumps(obj)

        # NOTE: this could be inefficient because it's a graph, not a tree.
        n += len(s)
        log('%d bytes', n)
        num_objects += 1

        if name == 'print_function':
          continue
        # sys.modules gets polluted because of pickle, etc.
        # get rid of _sre, _warnings, etc.
        # still might want _struct
        if (mod_name.startswith('_') and not mod_name.startswith('_devbuild')
            or mod_name in ('codecs', 'encodings', 'encodings.aliases', 're',
              'sre_constants', 'sre_compile', 'sre_parse')):
          continue

        # user-defined types, not types.ClassType which is old-style 
        # builtin functions can't be compiled.
        #types_to_compile = (types.FunctionType, types.BuiltinFunctionType, type)
        if isinstance(obj, types.BuiltinFunctionType):
          continue  # cannot be compiled, not a constant

        if isinstance(obj, types.FunctionType):
          funcs.append((mod_name, name, obj))
          continue
        if isinstance(obj, type):
          classes.append((mod_name, name, obj))
          continue

        global_vars.append((mod_name, name, obj))

    num_modules += 1

  log('Pickled %d objects in %d modules', num_objects, num_modules)
  log('')

  if 0:
    var_type_hist = PrintVars(global_vars)
    log('')

  num_methods, attr_type_hist = PrintClasses(classes)
  log('')

  if 0:
    PrintFuncs(funcs)
    log('')

  if 0:
    log('Global variable types:')
    for type_str, count in var_type_hist.most_common():
      log('%10d %s', count, type_str)
    log('')

  log('Class attribute types:')
  for type_str, count in attr_type_hist.most_common():
    log('%10d %s', count, type_str)
  log('')

  # Audit what's at the top level.  int, dict, str, list are most common, then
  # BuiltinFlags.
  log('%d global vars', len(global_vars))
  log('%d user-defined classes, with %d total methods on them', len(classes),
      num_methods)
  log('%d user-defined functions', len(funcs))


