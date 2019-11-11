"""
skeleton.py: The compiler pipeline.
"""
from __future__ import print_function

import cStringIO

from .compiler2 import future
from .compiler2 import pyassem
from .compiler2 import pycodegen
from .compiler2 import syntax
from .compiler2 import symbols
from .compiler2 import transformer

from pgen2 import tokenize
from pgen2 import driver
from pgen2 import parse


def _PrintScopes(scopes):
  # This is already flattened out.
  for node, scope in scopes.iteritems():
    scope.PrettyPrint()
    print()
    #for c in scope.children:
    #  print(c)


class _ModuleContext(object):
  """Module-level data for the CodeGenerator tree."""

  def __init__(self, filename, comp_opt, scopes, futures=()):
    self.filename = filename
    self.comp_opt = comp_opt  # copmilation options
    self.scopes = scopes
    self.futures = futures


def _ParseTreeToTuples(pnode):
  """
  parser.st objects from parsermodule.c have a totuple() method, which outputs
  tuples like this.  The original "compiler2" module expected this format, but
  the original pgen2 produced a different format.
  """
  if pnode.tok:
    value, _, (lineno, column) = pnode.tok  # opaque
  else:
    value = None
    lineno = 0
    column = 0

  if pnode.children:
    return (pnode.typ,) + tuple(_ParseTreeToTuples(p) for p in pnode.children)
  else:
    return (pnode.typ, value, lineno, column)


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


def Compile(f, opt, gr, mode, print_action=None):
  """Run the full compiler pipeline.

  Args:
    f: file handle with input source code
    opt: Parsed command line flags
    gr: Grammar
    start_symbol: name of the grammar start symbol
    mode: 'exec', 'eval', or 'single', like Python's builtin compile()
    print_action: 'ast' or 'cfg'.  Print an intermediate representation.
    opt: Command line flags
  """
  filename = f.name

  tokens = tokenize.generate_tokens(f.readline)

  p = parse.Parser(gr)
  if mode == 'single':
    start_symbol = 'single_input'
  elif mode == 'exec':
    start_symbol = 'file_input'
  elif mode == 'eval':
    start_symbol = 'eval_input'

  parse_tree = driver.PushTokens(p, tokens, gr, start_symbol)

  parse_tuples = _ParseTreeToTuples(parse_tree)

  tr = transformer.Transformer()
  as_tree = tr.transform(parse_tuples)

  if print_action == 'ast':
      print(as_tree)
      return

  # NOTE: This currently does nothing!
  v = syntax.SyntaxErrorChecker()
  v.Dispatch(as_tree)

  s = symbols.SymbolVisitor()
  s.Dispatch(as_tree)

  if print_action == 'symbols':
      _PrintScopes(s.scopes)
      return

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

  else:
      raise AssertionError('Invalid mode %r' % mode)

  # NOTE: There is no Start() or FindLocals() at the top level.
  gen.Dispatch(as_tree)  # mutates graph
  gen.Finish()

  if print_action == 'cfg':
      print(graph)
      return

  co = pyassem.MakeCodeObject(frame, graph, opt)

  # NOTE: Could call marshal.dump here?
  return co
