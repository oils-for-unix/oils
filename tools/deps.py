from __future__ import print_function
"""
deps.py
"""

import sys

from _devbuild.gen.syntax_asdl import command
from asdl import pybase
from core.util import log
from frontend import consts
from osh import word_


# TODO: Move to asdl/visitor.py?
class Visitor(object):
  # Python does introspection on method names:
  # method = 'visit_' + node.__class__.__name__
  # I'm using ASDL metaprogramming instead.

  def Visit(self, node):
    raise NotImplementedError()

  # Like ast.NodeVisitor().generic_visit!
  def VisitChildren(self, node):
    """
    Args:
      node: an ASDL node.
    """
    #print 'CHILD', node.ASDL_TYPE

    for name in node.__slots__:
      child = getattr(node, name)
      #log('Considering child %s', name)

      if isinstance(child, list):
        #log('Visiting child array %s', name)
        for item in child:
          # We have to check for compound objects on an INSTANCE basis, not a
          # type basis, because sums can look liek this:
          # iterable = IterArgv | IterArray(word* words)
          # We visit the latter but not the former.
          if isinstance(item, pybase.CompoundObj):
            self.Visit(item)
        continue

      if isinstance(child, pybase.CompoundObj):
        #log('Visiting child %s', name)
        self.Visit(child)
        continue


class DepsVisitor(Visitor):
  """
  Output:

  type      name          resolved_name             source_path line_num
  bin       cp            /usr/bin/cp               prog.sh     22
  lib       functions.sh  /home/andy/src/functions  prog.sh     22

  TODO:
  - Make this TSV2
  - handle source and .
  - flags like --path and --special exec
  - need some knowledge of function scope.
    f; f() { true; }  -- f is an exeternal binary!
    g() { f; }; f() { true; }   -- f is a function!

  """
  def __init__(self, f):
    Visitor.__init__(self)
    self.funcs_defined = {}
    self.progs_used = {}
    self.f = f

  def _Visit(self, node):
    """
    """
    #log('VISIT %s', node.__class__.__name__)

    # NOTE: The tags are not unique!!!  We would need this:
    # if isinstance(node, ast.command) and node.tag == command_e.Simple:
    # But it's easier to check the __class__ attribute.

    cls = node.__class__
    if cls is command.Simple:
      #log('SimpleCommand %s', node.words)
      #log('--')
      #node.PrettyPrint()

      # Things to consider:
      # - source and .
      # - DONE builtins: get a list from builtin.py
      # - DONE functions: have to enter function definitions into a dictionary
      # - Commands that call others: sudo, su, find, xargs, etc.
      # - builtins that call others: exec, command
      #   - except not command -v!

      if not node.words:
        return

      w = node.words[0]
      ok, argv0, _ = word_.StaticEval(w)
      if not ok:
        log("Couldn't statically evaluate %r", w)
        return

      if (consts.LookupSpecialBuiltin(argv0) == consts.NO_INDEX and
          consts.LookupAssignBuiltin(argv0) == consts.NO_INDEX and
          consts.LookupNormalBuiltin(argv0) == consts.NO_INDEX):
        self.progs_used[argv0] = True

      # NOTE: If argv1 is $0, then we do NOT print a warning!
      if argv0 == 'sudo':
        if len(node.words) < 2:
          return
        w1 = node.words[1]
        ok, argv1, _ = word_.StaticEval(w1)
        if not ok:
          log("Couldn't statically evaluate %r", w)
          return

        # Should we mark them behind 'sudo'?  e.g. "sudo apt install"?
        self.progs_used[argv1] = True

    elif cls is command.ShFunction:
      self.funcs_defined[node.name] = True

  def Visit(self, node):
    self._Visit(node)

    # We always need to visit children, even for SimpleCommand, etc.  There
    # could be command sub, e.g. even in redirect.  echo hi > $(cat out)
    self.VisitChildren(node)

  def Emit(self, row):
    # TSV-like format
    self.f.write('\t'.join(row))
    self.f.write('\n')

  def Done(self):
    """Write a report."""
    # TODO: Use self.Emit(), make it TSV.
    for name in self.progs_used:
      if name not in self.funcs_defined:
        print(name)


def Deps(node):
  v = DepsVisitor(sys.stdout)
  v.Visit(node)
  v.Done()
