#!/usr/bin/python
"""
skeleton.py: The compiler pipeline.
"""

from ..pgen2 import tokenize
from ..pgen2 import driver
from ..pgen2 import parse

from . import future
from . import pyassem
from . import pycodegen
from . import syntax
from . import symbols
from . import transformer


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


class _ModuleContext(object):
  """Module-level data for the CodeGenerator tree."""

  def __init__(self, filename, scopes, futures=()):
    self.filename = filename
    self.scopes = scopes
    self.futures = futures


def RunCompiler(f, filename, gr, start_symbol, mode):
  """Run the full compiler pipeline.

  TODO: Expose this as a library?
  """
  tokens = tokenize.generate_tokens(f.readline)

  p = parse.Parser(gr, convert=py2st)
  parse_tree = driver.PushTokens(p, tokens, gr.symbol2number[start_symbol])

  tr = transformer.Transformer()
  as_tree = tr.transform(parse_tree)

  #log('AST: %s', as_tree)

  # NOTE: This currently does nothing!
  v = syntax.SyntaxErrorChecker()
  v.Dispatch(as_tree)

  s = symbols.SymbolVisitor()
  s.Dispatch(as_tree)

  graph = pyassem.FlowGraph()
  if mode == "single":
      # NOTE: the name of the flow graph is a comment, not exposed to users.
      frame = pyassem.Frame("<interactive>", filename)
      ctx = _ModuleContext(filename, s.scopes)
      gen = pycodegen.InteractiveCodeGenerator(frame, graph, ctx)
      gen.set_lineno(as_tree)

  elif mode == "exec":
      frame = pyassem.Frame("<module>", filename)

      # TODO: Does this need to be made more efficient?
      p1 = future.FutureParser()
      p2 = future.BadFutureParser()
      p1.Dispatch(as_tree)
      p2.Dispatch(as_tree)

      ctx = _ModuleContext(filename, s.scopes, futures=p1.get_features())
      gen = pycodegen.TopLevelCodeGenerator(frame, graph, ctx)

  elif mode == "eval":
      frame = pyassem.Frame("<expression>", filename)
      ctx = _ModuleContext(filename, s.scopes)
      gen = pycodegen.TopLevelCodeGenerator(frame, graph, ctx)

  else:
      raise ValueError("compile() 3rd arg must be 'exec' or "
                       "'eval' or 'single'")

  # NOTE: There is no Start() or FindLocals() at the top level.
  gen.Dispatch(as_tree)  # mutates graph
  gen.Finish()

  # NOTE: This method has a pretty long pipeline too.
  co = pyassem.MakeCodeObject(gen.frame, gen.graph)
  return co


