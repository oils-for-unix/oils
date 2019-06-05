from __future__ import print_function
"""
callgraph.py
"""

import collections
import os
import sys

import __builtin__  # For looking up names
import types

from .lib import dis
from .lib import inspect

from core.util import log


def Disassemble(co):
  """Given a code object, yield instructions of interest.

  Args:
    co: __code__ attribute

  Structure copied from opy/compiler2/dis_tool.py, which was copied from
  dis.disassemble().
  """
  code = co.co_code
  extended_arg = 0  # Not used

  i = 0
  n = len(code)
  #log('\tLENGTH OF CODE %s: %d', co.co_name, n)

  while i < n:
    #log('\ti = %d, n = %d', i, n)
    op = ord(code[i])
    i += 1

    op_name = dis.opname[op]

    # operation is 1 byte, argument is 2 bytes.
    if op >= dis.HAVE_ARGUMENT:
      oparg = ord(code[i]) + ord(code[i+1])*256 + extended_arg
      extended_arg = 0

      if op == dis.EXTENDED_ARG:
        # Hm not used?
        raise AssertionError
        extended_arg = oparg*65536L

      i += 2

      const_name = None
      var_name = None

      if op in dis.hasconst:
        const_name = co.co_consts[oparg]

      elif op in dis.hasname:
        try:
          var_name = co.co_names[oparg]
        except IndexError:
          log('Error: %r cannot index %s with %d', op_name, co.co_names,
              oparg)
          raise

      elif op in dis.hasjrel:
        #raise AssertionError(op_name)
        pass

      elif op in dis.haslocal:
        #raise AssertionError(op_name)
        pass

      elif op in dis.hascompare:
        #raise AssertionError(op_name)
        pass

      elif op in dis.hasfree:
        #raise AssertionError(op_name)
        pass

    yield op_name, const_name, var_name
    #log('\t==> i = %d, n = %d', i, n)


import sre_compile

def _GetAttr(module, name):
  # Hack for bug in _fixup_range() !  (No longer in Python 3.6 head.)
  if module is sre_compile and name == 'l':
    return None
  # traceback.py has a hasattr() test
  if module is sys and name == 'tracebacklimit':
    return None

  try:
    val = getattr(module, name)
  except AttributeError:
    #log('%r not on %r', name, module)
    # This could raise too
    val = getattr(__builtin__, name)
  return val


def _Walk(obj, cls, ref, syms):
  """
  Discover statically what (globally-accessible) functions and classes are
  used.

  Args:
    obj: a callable object
    cls: an optional class that it was attached to, could be None
    ref: the way the object was referenced from another place in the code
    syms: output Symbols()

  Something like this is OK:
  # def Adder(x):
  #   def f(y):
  #     return x + y
  #   return f

  Because we'll still have access to the inner code object.  We probably won't
  compile it though.
  """
  if syms.Seen(obj):
    return

  module_name = getattr(obj, '__module__', None)
  # NOTE: We get duplicate objects like this, due to bound methods on different
  # objects.  Not sure how to fix it.
  #
  # OBJ <function Parse at 0x7fcd270b4de8>
  # OBJ <function Parse at 0x7fcd2709e500>
  # OBJ <built-in method get of dict object at 0x7fcd28c53280>
  # OBJ <built-in method get of dict object at 0x7fcd28c53398>

  #if obj.__name__ in ('write', 'get', 'Parse'):
  #  log('OBJ %s %d', obj, id(obj))
  #  pass

  # Oh is the namedtuple_ crap because of the Block class byterun/pyobj?

  if module_name is None or module_name in (
      'namedtuple_Arguments', 'namedtuple_ArgSpec',
      'namedtuple_Block'):
    syms.Add(obj, None, ref, None, None, None)
    return  # Can't walk anything

  #log('OBJ %s %d', obj, id(obj))
  module = sys.modules[obj.__module__]

  co = getattr(obj, '__code__', None)
  # For example, Builtins don't have bytecode.
  if isinstance(co, types.CodeType):
    co = obj.__code__
    #log('CO %s', co)
    #path = co.co_filename

    mod_name = None
    mod_path = co.co_filename

    syms.Add(obj, cls, ref, mod_name, mod_path, co.co_firstlineno)
  else:
    mod_name = module.__name__
    try:
      mod_path = module.__file__
      if mod_path.endswith('.pyc'):
        mod_path = mod_path[:-1]
    except AttributeError:
      mod_path = None

    #if obj.__name__ == 'lex_mode_e':
    #  log('!!! %s name %s path %s', obj, mod.__name__, mod.__file__)

    #mod_name = None
    #mod_path = None

    syms.Add(obj, cls, ref, mod_name, mod_path, None)
    return

  #log('\tNAME %s', val.__code__.co_name)
  #log('\tNAMES %s', val.__code__.co_names)

  # Most functions and classes we call are globals!
  #log('\t_Walk %s %s', obj, module)
  #log('\t%s', sorted(dir(module)))

  # Have to account for foo.Bar(), which gives this sequence:
  # 2           0 LOAD_GLOBAL              0 (foo)
  #             3 LOAD_ATTR                1 (Bar)
  #             6 CALL_FUNCTION            0
  #
  # Also: os.path.join().

  try:
    last_val = None  # value from previous LOAD_GLOBAL or LOAD_ATTR
    ref = []
    g = Disassemble(obj.__code__)

    while True:
      op, const, var = g.next()

      if op == 'LOAD_GLOBAL':
        val = _GetAttr(module, var)
        ref = [var]  # reset it

      elif op == 'LOAD_ATTR':
        #if last_val is not None and isinstance(last_val, types.ModuleType):
        if last_val is not None:
          #log('%s %s', op, var)
          val = _GetAttr(last_val, var)
          ref.append(var)

          # Crawl the methods below.  Otherwise we get duplicate bound/unbound
          # methods, which have unique addresses.
          # Examples: WAIT_SPEC.Parse, sys.stdout.write

          # BUG: os.fork and sys.stdout.write are the same?
          # I thought os.fork is types.BuiltinFunctionType, and
          # sys.stdout.write is types.BuiltinMethodType, but why not?

          if isinstance(val, (types.MethodType, types.BuiltinMethodType)):
            val = None
            ref = []

        else:
          val = None
          ref = []

      else:  # Some other opcode
        val = None
        ref = []

      if callable(val):
        #log('VAL %s module %s', val, val.__module__)
        # Recursive call.

        # Check for old style:
        #if isinstance(val, types.ClassType):
        #  print('OLD %s' % val)
        _Walk(val, None, ref, syms)

      # If the value is a class, walk its methods.  Note that we assume ALL
      # methods are used.  It's possible to narrow this down a bit and detect
      # unused methods.
      if isinstance(val, type):
        cls = val
        #log('type %s', val)
        for name in dir(val):
          # prevent error with __abstractmethods__ attribute
          #if name.startswith('__'):
          if name == '__abstractmethods__':
            continue
          field_val = getattr(val, name)
          #log('field_val %s', field_val)
          if isinstance(field_val, types.MethodType):
            func_obj = field_val.im_func
            _Walk(func_obj, cls, ref, syms)

      last_val = val  # Used on next iteration

  except StopIteration:
    pass

  #log('\tDone _Walk %s %s', obj, module)


def PrintSig(fmt, func):
  if os.getenv('CALLGRAPH_SIG') != '1':
    return
  try:
    argspec = inspect.getargspec(func)
  except TypeError:
    return
  parts = [':%s' % ' '.join(argspec.args)]
  # These are keyword-only args?
  if argspec.varargs:
    parts.append('varargs=%s' % (argspec.varargs,))
  if argspec.keywords:
    parts.append('kw=%s' % (argspec.keywords,))
  # Hm the default of 'None' is bad -- you can't distinguish a default of None,
  # which is very common!
  # It's better to get this by parsing the AST.
  if argspec.defaults and any(d is not None for d in argspec.defaults):
    parts.append('defaults=%s' % (argspec.defaults,))

  print(fmt % ' '.join(parts))


class Class(object):

  def __init__(self, cls, mod_name, mod_path):
    self.cls = cls
    self.mod_name = mod_name
    self.mod_path = mod_path
    self.methods = []

  def Name(self):
    return self.cls.__name__

  def AddMethod(self, m, mod_name, mod_path, line_num):
    # Just assume the method is in the same file as the class itself.
    self.methods.append((m, mod_name, mod_path, line_num))

  def Print(self):
    base_names = ' '.join(c.__name__ for c in self.cls.__bases__)
    print('  %s(%s)' % (self.cls.__name__, base_names))

    methods = [(m.__name__, m) for (m, _, _, _) in self.methods]
    methods.sort()
    for name, m in methods:
      print('    %s' % name)
      PrintSig('      %s', m)

  def __repr__(self):
    return '<Class %s %s %s %s>' % (
        self.cls, self.mod_name, self.mod_path, self.methods)


class Symbols(object):
  """A sink for discovered symbols."""

  def __init__(self):
    self.seen = set()

    self.classes = {}  # integer id() -> Class
    self.functions = []  # list of callables

    self.paths = {}  # path -> list of functions

  def Seen(self, c):
    """c: a callable."""
    id_ = id(c)
    if id_ in self.seen:
      return True
    self.seen.add(id_)
    return False

  def Add(self, obj, cls, ref, mod_name, mod_path, line_num):
    """Could be a function, class Constructor, or method.
    Can also be native (C) or interpreted (Python with __code__ attribute.)

    Returns:
      True if we haven't yet seen it.
    """
    if mod_path is not None:
      mod_path = os.path.normpath(mod_path)

    if isinstance(obj, type):
      id_ = id(obj)

      # NOTE: Python's classes don't have a __code__ object, which appears to
      # be an irregularity.  So we have to get location information from the
      # METHODS.

      # Exception: this type has a __code__ object that is not types.CodeType
      if obj is not types.FunctionType:
        assert not hasattr(obj, '__code__'), obj
      #assert path is None
      assert line_num is None

      self.classes[id_] = Class(obj, mod_name, mod_path)

    elif cls is not None:
      id_ = id(cls)
      descriptor = self.classes[id_]
      descriptor.AddMethod(obj, mod_name, mod_path, line_num)

    else:
      self.functions.append((obj, ref, mod_name, mod_path, line_num))

    return True

  def Report(self, f=sys.stdout):
    # Now categorize into files.  We couldn't do that earlier because classes
    # don't know where they are located!

    py_srcs = collections.defaultdict(SourceFile)
    c_srcs = collections.defaultdict(SourceFile)

    for func, ref, mod_name, mod_path, line_num in self.functions:
      if mod_path:
        py_srcs[mod_path].functions.append((func, ref, line_num))
      else:
        c_srcs[mod_name].functions.append((func, ref, line_num))

    for cls in self.classes.values():
      #if cls.cls.__name__ == 'lex_mode_e':
      #  log('!!! %s', cls)

      if cls.mod_path:
        py_srcs[cls.mod_path].classes.append(cls)
      else:
        c_srcs[cls.mod_name].classes.append(cls)

    prefix = os.getcwd()
    n = len(prefix) + 1

    #for name in sorted(py_srcs):
    #  print(name)

    #return

    # Still missing: non-enum ASDL types?  Why?  CompoundObj?
    # command_e is there, but command and SimpleCommmand aren't.
    # it's because we do
    # ast.command_e vs. ast.SimpleCommand
    # in both cases ast is a core.meta _AsdlModule?

    print('PYTHON CODE')
    print()

    for path in sorted(py_srcs):
      src = py_srcs[path]

      if path is not None and path.startswith(prefix):
        path = path[n:]

      print('%s' % path)

      for func, ref, _ in src.functions:
        third = func
        #third = ''
        #print('  %s [%s] %s' % (func.__name__, '.'.join(ref), third))
        print('  %s' % func.__name__)
        PrintSig('    %s', func)

      classes = [(c.Name(), c) for c in src.classes]
      classes.sort()
      for c in src.classes:
        c.Print()

      print()

    print('NATIVE CODE')
    print()

    for mod_name in sorted(c_srcs):
      src = c_srcs[mod_name]

      print('%s' % mod_name)

      for func, ref, _ in src.functions:
        #third = func
        third = ''
        #print('  %s [%s] %s' % (func.__name__, '.'.join(ref), third))
        print('  %s' % func.__name__)

      classes = [(c.Name(), c) for c in src.classes]
      classes.sort()
      for c in src.classes:
        c.Print()

      print()


class SourceFile(object):

  def __init__(self):
    self.classes = []
    self.functions = []


def Walk(main, modules):
  """Given a function main, finds all functions it transitively calls.

  Uses heuristic bytecode analysis.  Limitations:

  - functions that are local variables might not work?  But this should work:

  if x > 0:
    f = GlobalFunc
  else:
    f = OtherGlobalFunc
  f()    # The LOAD_GLOBAL will be found.

  Args:
    main: function
    modules: Dict[str, module]
  """
  syms = Symbols()
  _Walk(main, None, ['main'], syms)

  # TODO:
  # - co_consts should be unified?  So we know how big the const pool is.

  syms.Report()

