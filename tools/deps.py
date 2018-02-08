#!/usr/bin/python
"""
deps.py
"""

import sys

from asdl import asdl_ as asdl
from asdl import py_meta
from core import builtin
from core import util
from core import word
from osh.meta import ast, runtime
from osh import ast_lib

command_e = ast.command_e
builtin_e = runtime.builtin_e
log = util.log

# TODO: Move to asdl/visitor.py?
class Visitor(object):
  # In Python, they do introspection on method names.
  # method = 'visit_' + node.__class__.__name__
  # I'm not going to bother, because I have ASDL!  I want the generic visitor.

  def Visit(self, node):
    raise NotImplementedError

  # Like ast.NodeVisitor().generic_visit!
  def VisitChildren(self, node):
    """
    Args:
      node: an ASDL node.
    """
    #print 'CHILD', node.ASDL_TYPE

    for name, _ in node.ASDL_TYPE.GetFields():
      child = getattr(node, name)
      #log('Considering child %s', name)

      if isinstance(child, list):
        #log('Visiting child array %s', name)
        for item in child:
          # We have to do this on an INSTANCE basis, not a type basis, because
          # sums can be like:
          # iterable = IterArgv | IterArray(word* words)
          # We visit the latter but not the foramer.
          if isinstance(item, py_meta.CompoundObj):
            self.Visit(item)
        continue

      if isinstance(child, py_meta.CompoundObj):
        #log('Visiting child %s', name)
        self.Visit(child)
        continue


class DepsVisitor(Visitor):
  """
  Output:

  type      name          resolved_name             source_path line_num
  bin       cp            /usr/bin/cp               prog.sh     22
  lib       functions.sh  /home/andy/src/functions  prog.sh     22

  TODO: Make this TSV2

  """
  def __init__(self, f):
    Visitor.__init__(self)
    self.funcs_defined = {}
    self.progs_used = {}
    self.f = f

  def Visit(self, node):
    """
    """
    #log('VISIT %s', node.__class__.__name__)

    # PROBLEM: The tags are not unique!!!  Crap.  This is picking up some other
    # stuff.  Need the isinstance() check.
    if isinstance(node, ast.command) and node.tag == command_e.SimpleCommand:
      #log('SimpleCommand %s', node.words)
      #log('--')
      #ast_lib.PrettyPrint(node)

      # Things to consider:
      # - source and .
      # - builtins: get a list from builtin.py
      # - functions: have to enter function definitions into a dictionary
      # - Commands that call others: sudo, su, find, xargs, etc.

      # TODO: We need two passes!  test/wild.sh make-report, etc.

      if node.words:
        w = node.words[0]
        ok, prog, _ = word.StaticEval(w)
        if ok:
          # TODO: Also consider builtins
          if (prog not in self.funcs_defined and
              builtin.ResolveSpecial(prog) == builtin_e.NONE and
              builtin.Resolve(prog) == builtin_e.NONE):
            self.progs_used[prog] = True
        else:
          log("Couldn't statically evaluate %r", w)

      # There could be command sub, e.g. even in redirect:
      self.VisitChildren(node)

    elif isinstance(node, ast.command) and node.tag == command_e.FuncDef:
      self.funcs_defined[node.name] = True
      self.VisitChildren(node)

    else:
      self.VisitChildren(node)

  def Emit(self, row):
    # TSV-like format
    self.f.write('\t'.join(row))
    self.f.write('\n')

  def Done(self):
    for name in self.progs_used:
      print name


def Deps(node):
  v = DepsVisitor(sys.stdout)
  v.Visit(node)
  v.Done()

  #print(node)
