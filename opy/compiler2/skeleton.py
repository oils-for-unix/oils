#!/usr/bin/python
"""
skeleton.py: The compiler pipeline.
"""

import types

from ..pgen2 import tokenize
from ..pgen2 import driver
from ..pgen2 import parse

from . import future
from . import pyassem
from . import pycodegen
from . import syntax
from . import symbols
from . import transformer


class _ModuleContext(object):
  """Module-level data for the CodeGenerator tree."""

  def __init__(self, filename, scopes, futures=()):
    self.filename = filename
    self.scopes = scopes
    self.futures = futures


# Emulating parser.st structures from parsermodule.c.
# They have a totuple() method, which outputs tuples like this.
def py2st(unused_gr, raw_node):
  typ, value, context, children = raw_node
  # See pytree.Leaf
  if context:
    _, (lineno, column) = context
  else:
    lineno = 0  # default in Leaf
    column = 0

  if children:
    return (typ,) + tuple(children)
  else:
    return (typ, value, lineno, column)


def MakeCodeObject(frame, graph):
    """Order blocks, encode instructions, and create types.CodeType().

    Called by RunCompiler below, and also recursively by ArgEncoder.
    """
    # Compute stack depth per basic block.
    depths = {}
    b = pyassem.BlockStackDepth()
    for block in graph.blocks:
        depths[block] = b.Sum(block.getInstructions())

    # Compute maximum stack depth for any path through the CFG.
    g = pyassem.GraphStackDepth(depths, graph.exit)
    stacksize = g.Max(graph.entry, 0)

    # Order blocks so jump offsets can be encoded.
    blocks = pyassem.OrderBlocks(graph.entry, graph.exit)
    insts = pyassem.FlattenGraph(blocks)

    cellvars = pyassem.ReorderCellVars(frame)
    consts = [frame.docstring]
    names = []
    # The closure list is used to track the order of cell variables and
    # free variables in the resulting code object.  The offsets used by
    # LOAD_CLOSURE/LOAD_DEREF refer to both kinds of variables.
    closure = cellvars + frame.freevars

    # Convert arguments from symbolic to concrete form.
    enc = pyassem.ArgEncoder(frame.klass, consts, names, frame.varnames,
                             closure)
    # Mutates not only insts, but also consts, names, etc.
    enc.Run(insts)

    a = pyassem.Assembler()
    bytecode, firstline, lnotab = a.Run(insts)

    return types.CodeType(
        frame.ArgCount(), frame.NumLocals(), stacksize, frame.flags,
        bytecode,
        tuple(consts),
        tuple(names),
        tuple(frame.varnames),
        frame.filename, frame.name, firstline,
        lnotab,
        tuple(frame.freevars),
        tuple(cellvars))


def RunCompiler(f, filename, gr, start_symbol, mode):
  """Run the full compiler pipeline.

  TODO: Expose this as a library?
  """
  tokens = tokenize.generate_tokens(f.readline)

  p = parse.Parser(gr, convert=py2st)
  parse_tree = driver.PushTokens(p, tokens, gr.symbol2number[start_symbol])

  tr = transformer.Transformer()
  as_tree = tr.transform(parse_tree)

  # NOTE: This currently does nothing!
  v = syntax.SyntaxErrorChecker()
  v.Dispatch(as_tree)

  s = symbols.SymbolVisitor()
  s.Dispatch(as_tree)

  graph = pyassem.FlowGraph()  # Mutated by code generator
  if mode == "single":
      ctx = _ModuleContext(filename, s.scopes)
      # NOTE: the name of the Frame is a comment, not exposed to users.
      frame = pyassem.Frame("<interactive>", filename)  # mutated
      gen = pycodegen.InteractiveCodeGenerator(ctx, frame, graph)
      gen.set_lineno(as_tree)

  elif mode == "exec":
      # TODO: Does this need to be made more efficient?
      p1 = future.FutureParser()
      p2 = future.BadFutureParser()
      p1.Dispatch(as_tree)
      p2.Dispatch(as_tree)

      ctx = _ModuleContext(filename, s.scopes, futures=p1.get_features())
      frame = pyassem.Frame("<module>", filename)  # mutated

      gen = pycodegen.TopLevelCodeGenerator(ctx, frame, graph)

  elif mode == "eval":
      ctx = _ModuleContext(filename, s.scopes)
      frame = pyassem.Frame("<expression>", filename)  # mutated
      gen = pycodegen.TopLevelCodeGenerator(ctx, frame, graph)

  else:
      raise ValueError("compile() 3rd arg must be 'exec' or "
                       "'eval' or 'single'")

  # NOTE: There is no Start() or FindLocals() at the top level.
  gen.Dispatch(as_tree)  # mutates graph
  gen.Finish()

  # NOTE: This method has a pretty long pipeline too.
  co = MakeCodeObject(frame, graph)
  return co
