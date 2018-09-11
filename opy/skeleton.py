#!/usr/bin/python
"""
skeleton.py: The compiler pipeline.
"""

import cStringIO

from .pgen2 import tokenize
from .pgen2 import driver
from .pgen2 import parse

from .compiler2 import future
from .compiler2 import pyassem
from .compiler2 import pycodegen
from .compiler2 import ovm_codegen
from .compiler2 import syntax
from .compiler2 import symbols
from .compiler2 import transformer


class _ModuleContext(object):
  """Module-level data for the CodeGenerator tree."""

  def __init__(self, filename, comp_opt, scopes, futures=()):
    self.filename = filename
    self.comp_opt = comp_opt  # copmilation options
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


class StringInput(object):
  """A wrapper for a StringIO object .

  It follows Python's convention of having an f.name attribute.
  """
  def __init__(self, s, name):
    self.f = cStringIO.StringIO(s)
    self.name = name

  def read(self, *args):
    return self.f.read(*args)

  def readline(self, *args):
    return self.f.readline(*args)

  def close(self):
    return self.f.close()
    


class ParseMode(object):
  """A shortcut."""
  def __init__(self, gr, start_symbol):
    self.gr = gr
    self.start_symbol = start_symbol


class Compiler(object):
  def __init__(self, gr):
    self.gr = gr
    
  def Compile(self, f, opt, *args, **kwargs):
    # TODO: inline this call
    return Compile(f, opt, self.gr, *args, **kwargs)


def Compile(f, opt, gr, mode, return_cfg=False):
  """Run the full compiler pipeline.

  Args:
    f: file handle with input source code
    opt: Parsed command line flags
    gr: Grammar
    start_symbol: name of the grammar start symbol
    mode: 'exec', 'eval', or 'single', like Python's builtin compile()
    return_cfg: A little hack to stop at the CFG stage
    opt: Command lien flags
  """
  filename = f.name

  tokens = tokenize.generate_tokens(f.readline)

  p = parse.Parser(gr, convert=py2st)
  if mode == 'single':
    start_symbol = 'single_input'
  elif mode == 'exec':
    start_symbol = 'file_input'
  elif mode == 'ovm':
    start_symbol = 'file_input'
  elif mode == 'eval':
    start_symbol = 'eval_input'

  parse_tree = driver.PushTokens(p, tokens, gr.symbol2number[start_symbol])

  tr = transformer.Transformer()
  as_tree = tr.transform(parse_tree)

  # NOTE: This currently does nothing!
  v = syntax.SyntaxErrorChecker()
  v.Dispatch(as_tree)

  s = symbols.SymbolVisitor()
  s.Dispatch(as_tree)

  graph = pyassem.FlowGraph()  # Mutated by code generator

  if mode == "single":  # Not used now?
      ctx = _ModuleContext(filename, opt, s.scopes)
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

      ctx = _ModuleContext(filename, opt, s.scopes, futures=p1.get_features())
      frame = pyassem.Frame("<module>", filename)  # mutated

      gen = pycodegen.TopLevelCodeGenerator(ctx, frame, graph)

  elif mode == "eval":
      ctx = _ModuleContext(filename, opt, s.scopes)
      frame = pyassem.Frame("<expression>", filename)  # mutated
      gen = pycodegen.TopLevelCodeGenerator(ctx, frame, graph)

  elif mode == "ovm":
      ctx = _ModuleContext(filename, opt, s.scopes)
      frame = ovm_codegen.Frame("<module>", filename)  # mutated
      gen = ovm_codegen.CodeGenerator(ctx, frame, graph)

  else:
      raise AssertionError('Invalid mode %r' % mode)

  # NOTE: There is no Start() or FindLocals() at the top level.
  gen.Dispatch(as_tree)  # mutates graph
  gen.Finish()

  if return_cfg:
      return graph

  co = pyassem.MakeCodeObject(frame, graph, opt)

  # NOTE: Could call marshal.dump here?
  return co
