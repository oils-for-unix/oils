#!/usr/bin/env python3
"""
pea_main.py

A potential rewrite of mycpp.
"""
import ast
from ast import AST, stmt, Module, ClassDef, FunctionDef, Assign
import collections
from dataclasses import dataclass
import optparse
import os
from pprint import pprint
import sys
import time

import typing
from typing import Optional, Any

from mycpp import pass_state


START_TIME = time.time()

def log(msg: str, *args: Any) -> None:
  if args:
    msg = msg % args
  print('%.2f %s' % (time.time() - START_TIME, msg), file=sys.stderr)


@dataclass
class PyFile:
  filename: str
  namespace: str  # C++ namespace
  module: ast.Module  # parsed representation


class Program:
  """A program is a collection of PyFiles."""

  def __init__(self) -> None:
    self.py_files : list[PyFile] = []

    # As we parse, we add modules, and fill in the dictionaries with parsed
    # types.  Then other passes can retrieve the types with the same
    # dictionaries.

    # right now types are modules?  Could change that
    self.func_types: dict[FunctionDef, AST] = {}  
    self.method_types : dict[FunctionDef, AST] = {}  
    self.class_types : dict[ClassDef, Module] = {}  
    self.assign_types : dict[Assign, Module] = {}  

    # like mycpp: type and variable string.  TODO: We shouldn't flatten it to a
    # C type until later.
    #
    # Note: ImplPass parses the types.  So I guess this could be limited to
    # that?
    # DoFunctionMethod() could make two passes?
    # 1. collect vars
    # 2. print code

    self.local_vars : dict[FunctionDef, list[tuple[str, str]]] = {}

    # ForwardDeclPass:
    #   OnMethod()
    #   OnSubclass()

    # Then
    # Calculate()
    #
    # PrototypesPass: # IsVirtual
    self.virtual = pass_state.Virtual()

    self.stats: dict[str, int] = {
        # parsing stats
        'num_files': 0,
        'num_funcs': 0,
        'num_classes': 0,
        'num_methods': 0,
        'num_assign': 0,

        # ConstPass stats
        'num_strings': 0,
    }

  def PrintStats(self) -> None:
    pprint(self.stats, stream=sys.stderr)


class TypeSyntaxError(Exception):

  def __init__(self, lineno: int, code_str: str):
    self.lineno = lineno
    self.code_str = code_str


def ParseFiles(files: list[str], prog: Program) -> bool:

  for filename in files:
    with open(filename) as f:
      contents = f.read()

    try:
      # Python 3.8+ supports type_comments=True
      module = ast.parse(contents, filename=filename, type_comments=True)
    except SyntaxError as e:
      # This raises an exception for some reason
      #e.print_file_and_line()
      print('Error parsing %s: %s' % (filename, e))
      return False

    tmp = os.path.basename(filename)
    namespace, _ = os.path.splitext(tmp)

    prog.py_files.append(PyFile(filename, namespace, module))

    prog.stats['num_files'] += 1

  return True


class ConstVisitor(ast.NodeVisitor):

  def __init__(self, const_lookup: dict[str, int]):
    ast.NodeVisitor.__init__(self)
    self.const_lookup = const_lookup
    self.str_id = 0

  def visit_Constant(self, o: ast.Constant) -> None:
    if isinstance(o.value, str):
      self.const_lookup[o.value] = self.str_id
      self.str_id += 1


class ForwardDeclPass:
  """Emit forward declarations."""
  # TODO: Move this to ParsePass after comparing with mycpp.

  def __init__(self, f: typing.IO[str]) -> None:
    self.f = f

  def DoPyFile(self, py_file: PyFile) -> None:

    # TODO: could omit empty namespaces
    namespace = py_file.namespace
    self.f.write(f'namespace {namespace} {{  // forward declare\n')

    for stmt in py_file.module.body:
      match stmt:
        case ClassDef():
          class_name = stmt.name
          self.f.write(f'  class {class_name};\n')

    self.f.write(f'}}  // forward declare {namespace}\n')
    self.f.write('\n')


def _ParseFuncType(st: stmt) -> AST:
  assert st.type_comment  # caller checks this
  try:
    # This parses with the func_type production in the grammar
    return ast.parse(st.type_comment, mode='func_type')
  except SyntaxError:
    raise TypeSyntaxError(st.lineno, st.type_comment)


class PrototypesPass:
  """Parse signatures and Emit function prototypes."""

  def __init__(self, opts: Any, prog: Program, f: typing.IO[str]) -> None:
    self.opts = opts
    self.prog = prog
    self.f = f

  def DoClass(self, cls: ClassDef) -> None:
    for stmt in cls.body:
      match stmt:
        case FunctionDef():
          if stmt.type_comment:
            sig = _ParseFuncType(stmt)  # may raise

            if self.opts.verbose:
              print('METHOD')
              print(ast.dump(sig, indent='  '))
              # TODO: We need to print virtual here

            self.prog.method_types[stmt] = sig  # save for ImplPass
          self.prog.stats['num_methods'] += 1

        # TODO: assert that there aren't top-level statements?
        case _:
          pass

  def DoPyFile(self, py_file: PyFile) -> None:
    for stmt in py_file.module.body:
      match stmt:
        case FunctionDef():
          if stmt.type_comment:
            sig = _ParseFuncType(stmt)  # may raise

            if self.opts.verbose:
              print('FUNC')
              print(ast.dump(sig, indent='  '))

            self.prog.func_types[stmt] = sig  # save for ImplPass

          self.prog.stats['num_funcs'] += 1

        case ClassDef():
          self.DoClass(stmt)
          self.prog.stats['num_classes'] += 1

        case _:
          # Import, Assign, etc.
          #print(stmt)

          # TODO: omit __name__ == '__main__' etc.
          # if __name__ == '__main__'
          pass


class ImplPass:
  """Emit function and method bodies.

  Algorithm:
    collect local variables first
  """

  def __init__(self, prog: Program, f: typing.IO[str]) -> None:
    self.prog = prog
    self.f = f

  # TODO: needs to be fully recursive, so you get bodies of loops, etc.
  def DoBlock(self, stmts: list[stmt], indent: int=0) -> None:
    """e.g. body of function, method, etc."""


    #print('STMTS %s' % stmts)

    ind_str = '  ' * indent

    for stmt in stmts:
      match stmt:
        case Assign():
          #print('%s* Assign' % ind_str)
          #print(ast.dump(stmt, indent='  '))

          if stmt.type_comment:
            # This parses with the func_type production in the grammar
            try:
              typ = ast.parse(stmt.type_comment)
            except SyntaxError as e:
              # New syntax error
              raise TypeSyntaxError(stmt.lineno, stmt.type_comment)

            self.prog.assign_types[stmt] = typ

            #print('%s  TYPE: Assign' % ind_str)
            #print(ast.dump(typ, indent='  '))

          self.prog.stats['num_assign'] += 1

        case _:
          pass

  def DoClass(self, cls: ClassDef) -> None:
    for stmt in cls.body:
      match stmt:
        case FunctionDef():
          self.DoBlock(stmt.body, indent=1)

        case _:
          pass

  def DoPyFile(self, py_file: PyFile) -> None:
    for stmt in py_file.module.body:
      match stmt:
        case ClassDef():
          self.DoClass(stmt)

        case FunctionDef():
          self.DoBlock(stmt.body, indent=1)


def Options() -> optparse.OptionParser:
  """Returns an option parser instance."""

  p = optparse.OptionParser()
  p.add_option(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Show details about translation')

  # Control which modules are exported to the header.  Used by
  # build/translate.sh.
  p.add_option(
      '--to-header', dest='to_header', action='append', default=[],
      help='Export this module to a header, e.g. frontend.args')

  p.add_option(
      '--header-out', dest='header_out', default=None,
      help='Write this header')

  return p


def main(argv: list[str]) -> int:

  o = Options()
  opts, argv = o.parse_args(argv)

  action = argv[1]

  if action == 'parse':
    files = argv[2:]

    # TODO:
    # pass_state.Virtual
    #   this loops over functions and methods.  But it has to be done BEFORE
    #   the PrototypesPass, or we need two passes.  Gah!
    #   Could it be done in ConstVisitor?  ConstVirtualVisitor?

    # local_vars 

    prog = Program()
    log('Pea begin')

    if not ParseFiles(files, prog):
      return 1
    log('Parsed %d files and their type comments', len(files))
    prog.PrintStats()
    print()

    # This is the first pass

    const_lookup: dict[str, int] = {}  

    v = ConstVisitor(const_lookup)
    for py_file in prog.py_files:
      v.visit(py_file.module)

    log('Collected %d constants', len(const_lookup))

    # TODO: respect header_out for these two passes
    out_f = sys.stdout

    # ForwardDeclPass: module -> class
    # TODO: Move trivial ForwardDeclPass into ParsePass, BEFORE constants,
    # after comparing output with mycpp. 
    pass2 = ForwardDeclPass(out_f)
    for py_file in prog.py_files:
      namespace = py_file.namespace
      pass2.DoPyFile(py_file)

    log('Wrote forward declarations') 
    prog.PrintStats()
    print()

    try:
      # PrototypesPass: module -> class/method, func

      pass3 = PrototypesPass(opts, prog, out_f)
      for py_file in prog.py_files:
        pass3.DoPyFile(py_file)  # parses type comments in signatures

      log('Wrote prototypes') 
      prog.PrintStats()
      print()

      # ImplPass: module -> class/method, func; then probably a fully recursive thing

      pass4 = ImplPass(prog, out_f)
      for py_file in prog.py_files:
        pass4.DoPyFile(py_file)  # parses type comments in assignments

      log('Wrote implementation') 
      prog.PrintStats()
      print()

    except TypeSyntaxError as e:
      log('Type comment syntax error on line %d of %s: %r',
          e.lineno, py_file.filename, e.code_str)
      return 1

    log('Done')

  elif action == 'cpp':
    files = argv[2:]
    print('// PEA C++')

  else:
    raise RuntimeError('Invalid action %r' % action)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
