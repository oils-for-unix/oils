#!/usr/bin/python
"""
skeleton.py: The compiler pipeline.
"""

from .pgen2 import tokenize
from .pgen2 import driver
from .pgen2 import parse

from .compiler2 import future
from .compiler2 import pyassem
from .compiler2 import pycodegen
from .compiler2 import syntax
from .compiler2 import symbols
from .compiler2 import transformer


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


def Compile(f, filename, gr, start_symbol, mode):
  """Run the full compiler pipeline.

  Args:
    f: file handle with input source code
    filename: filename for debugging
    gr: Grammar
    start_symbol: name of the grammar start symbol
    mode: 'exec', 'eval', or 'single', like Python's builtin compile()
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
      raise AssertionError('Invalid mode %r' % mode)

  # NOTE: There is no Start() or FindLocals() at the top level.
  gen.Dispatch(as_tree)  # mutates graph
  gen.Finish()

  co = pyassem.MakeCodeObject(frame, graph)

  # TODO: Could call marshal.dump here?
  return co
