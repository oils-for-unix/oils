#!/usr/bin/env python
"""
opy_main.py
"""
from __future__ import print_function

import cStringIO
import hashlib
import optparse
import os
import sys
import marshal
#import logging

# Like oil.py, set PYTHONPATH internally?  So symlinks work?
# Actually '.' is implicitly in PYTHONPATH, so we don't need it.
# If we were in bin/oil.py, then we would need this.
#this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
#sys.path.append(os.path.join(this_dir))

from .pgen2 import driver, parse, pgen, grammar
from .pgen2 import token
from .pgen2 import tokenize
from . import pytree

from .compiler2 import dis_tool
from .compiler2 import future
from .compiler2 import misc
from .compiler2 import pyassem
from .compiler2 import pycodegen
from .compiler2 import syntax
from .compiler2 import symbols
from .compiler2 import transformer

# Disabled for now because byterun imports 'six', and that breaks the build.
#from .byterun import execfile

from core import args
from core import util
log = util.log


# From lib2to3/pygram.py.  This takes the place of the 'symbol' module.
# compiler/transformer module needs this.

class Symbols(object):

    def __init__(self, gr):
        """Initializer.

        Creates an attribute for each grammar symbol (nonterminal),
        whose value is the symbol's type (an int >= 256).
        """
        for name, symbol in gr.symbol2number.items():
            setattr(self, name, symbol)
            #log('%s -> %d' % (name, symbol))
        # For transformer to use
        self.number2symbol = gr.number2symbol
        #assert 0


def HostStdlibNames():
  import symbol
  import token
  names = {}
  for k, v in symbol.sym_name.items():
    names[k] = v
  for k, v in token.tok_name.items():
    names[k] = v
  return names


def WriteGrammar(grammar_path, pickle_path):
  log("Generating grammar tables from %s", grammar_path)
  g = pgen.generate_grammar(grammar_path)
  log("Writing grammar tables to %s", pickle_path)
  try:
    # calls pickle.dump on self.__dict__ after making it deterministic
    g.dump(pickle_path)
  except OSError as e:
    log("Writing failed: %s", e)


def CountTupleTree(tu):
  """Count the nodes in a tuple parse tree."""
  if isinstance(tu, tuple):
    s = 0
    for entry in tu:
      s += CountTupleTree(entry)
    return s
  elif isinstance(tu, int):
    return 1
  elif isinstance(tu, str):
    return 1
  else:
    raise AssertionError(tu)


class TupleTreePrinter(object):
  def __init__(self, names):
    self._names = names

  def Print(self, tu, f=sys.stdout, indent=0):
    ind = '  ' * indent
    f.write(ind)
    if isinstance(tu, tuple):
      f.write(self._names[tu[0]])
      f.write('\n')
      for entry in tu[1:]:
        self.Print(entry, f, indent=indent+1)
    elif isinstance(tu, int):
      f.write(str(tu))
      f.write('\n')
    elif isinstance(tu, str):
      f.write(str(tu))
      f.write('\n')
    else:
      raise AssertionError(tu)


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser()

  # NOTE: default command is None because empty string is valid.
  p.add_option(
      '-c', dest='command', default=None,
      help='Python command to run')
  return p


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

  if mode == "single":
      # NOTE: the name of the flow graph is a comment, not exposed to users.
      graph = pyassem.PyFlowGraph("<interactive>", filename)
      ctx = _ModuleContext(filename, s.scopes)
      gen = pycodegen.InteractiveCodeGenerator(graph, ctx)
      gen.set_lineno(as_tree)

  elif mode == "exec":
      graph = pyassem.PyFlowGraph("<module>", filename)

      # TODO: Does this need to be made more efficient?
      p1 = future.FutureParser()
      p2 = future.BadFutureParser()
      p1.Dispatch(as_tree)
      p2.Dispatch(as_tree)

      ctx = _ModuleContext(filename, s.scopes, futures=p1.get_features())
      gen = pycodegen.TopLevelCodeGenerator(graph, ctx)

  elif mode == "eval":
      graph = pyassem.PyFlowGraph("<expression>", filename)
      ctx = _ModuleContext(filename, s.scopes)
      gen = pycodegen.TopLevelCodeGenerator(graph, ctx)

  else:
      raise ValueError("compile() 3rd arg must be 'exec' or "
                       "'eval' or 'single'")

  # NOTE: There is no Start() or FindLocals() at the top level.
  gen.Dispatch(as_tree)  # mutates graph
  gen.Finish()

  # NOTE: This method has a pretty long pipeline too.
  co = graph.MakeCodeObject()
  return co


# TODO: more actions:
# - lex, parse, ast, cfg, compile/eval/repl

# Made by the Makefile.
PICKLE_REL_PATH = '_build/opy/py27.grammar.pickle'

def OpyCommandMain(argv):
  """Dispatch to the right action."""

  # TODO: Use core/args.
  opts, argv = Options().parse_args(argv)

  try:
    action = argv[0]
  except IndexError:
    raise args.UsageError('opy: Missing required subcommand.')

  if action in ('parse', 'compile', 'eval', 'repl'):
    loader = util.GetResourceLoader()
    f = loader.open(PICKLE_REL_PATH)
    gr = grammar.Grammar()
    gr.load(f)
    f.close()

    # In Python 2 code, always use from __future__ import print_function.
    try:
      del gr.keywords["print"]
    except KeyError:
      pass

    symbols = Symbols(gr)
    pytree.Init(symbols)  # for type_repr() pretty printing
    transformer.Init(symbols)  # for _names and other dicts
    tr = transformer.Transformer()
  else:
    # e.g. pgen2 doesn't use any of these.  Maybe we should make a different
    # tool.
    gr = None
    symbols = None
    tr = None


  if action == 'pgen2':
    grammar_path = argv[1]
    pickle_path = argv[2]
    WriteGrammar(grammar_path, pickle_path)

  elif action == 'stdlib-parse':
    # This is what the compiler/ package was written against.
    import parser

    py_path = argv[1]
    with open(py_path) as f:
      st = parser.suite(f.read())

    tree = st.totuple()

    n = CountTupleTree(tree)
    log('COUNT %d', n)
    printer = TupleTreePrinter(HostStdlibNames())
    printer.Print(tree)

  elif action == 'lex':
    py_path = argv[1]
    with open(py_path) as f:
      tokens = tokenize.generate_tokens(f.readline)
      for typ, val, start, end, unused_line in tokens:
        print('%10s %10s %-10s %r' % (start, end, token.tok_name[typ], val))

  elif action == 'parse':
    py_path = argv[1]
    with open(py_path) as f:
      tokens = tokenize.generate_tokens(f.readline)
      p = parse.Parser(gr, convert=py2st)
      parse_tree = driver.PushTokens(p, tokens, gr.symbol2number['file_input'])

    if isinstance(parse_tree, tuple):
      n = CountTupleTree(parse_tree)
      log('COUNT %d', n)

      printer = TupleTreePrinter(transformer._names)
      printer.Print(parse_tree)
    else:
      tree.PrettyPrint(sys.stdout)
      log('\tChildren: %d' % len(tree.children), file=sys.stderr)

  elif action == 'compile':  # 'opyc compile' is pgen2 + compiler2
    py_path = argv[1]
    out_path = argv[2]

    with open(py_path) as f:
      co = RunCompiler(f, py_path, gr, 'file_input', 'exec')

    log("Compiled to %d bytes of bytecode", len(co.co_code))

    # Write the .pyc file
    with open(out_path, 'wb') as out_f:
      h = misc.getPycHeader(py_path)
      out_f.write(h)
      marshal.dump(co, out_f)

  elif action == 'eval':  # Like compile, but parses to a code object and prints it
    py_expr = argv[1]
    f = cStringIO.StringIO(py_expr)
    co = RunCompiler(f, '<eval input>', gr, 'eval_input', 'eval')

    v = dis_tool.Visitor()
    v.show_code(co)
    print()
    print('RESULT:')
    print(eval(co))

  elif action == 'repl':  # Like eval in a loop
    while True:
      py_expr = raw_input('opy> ')
      f = cStringIO.StringIO(py_expr)

      # TODO: change this to 'single input'?  Why doesn't this work?
      co = RunCompiler(f, '<REPL input>', gr, 'eval_input', 'eval')

      v = dis_tool.Visitor()
      v.show_code(co)
      print(eval(co))

  elif action == 'dis':
    pyc_path = argv[1]
    try:
      report_path = argv[2]
      report_f = open(report_path, 'w')
    except IndexError:
      report_f = sys.stdout

    with open(pyc_path, 'rb') as f:
      # TODO: Make this a flag.
      #v = inspect_pyc.Visitor(dis_bytecode=False)
      v = dis_tool.Visitor()
      v.Visit(f)

    v.Report(report_f)

  elif action == 'dis-md5':
    pyc_paths = argv[1:]
    if not pyc_paths:
      raise args.UsageError('dis-md5: At least one .pyc path is required.')

    for path in pyc_paths:
      h = hashlib.md5()
      with open(path) as f:
        magic = f.read(4)
        h.update(magic)
        ignored_timestamp = f.read(4)
        while True:
          b = f.read(64 * 1024)
          if not b:
            break
          h.update(b)
      print('%6d %s %s' % (os.path.getsize(path), h.hexdigest(), path))

  # TODO: Not used
  elif action == 'compile2':
    in_path = argv[1]
    out_path = argv[2]

    from compiler2 import pycodegen as pycodegen2
    from misc import stdlib_compile

    stdlib_compile.compileAndWrite(in_path, out_path, pycodegen2.compile)

  elif action == 'run':
    # TODO: Add an option like -v in __main__

    #level = logging.DEBUG if args.verbose else logging.WARNING
    #logging.basicConfig(level=level)
    #logging.basicConfig(level=logging.DEBUG)

    # Compile and run, without writing pyc file
    py_path = argv[1]
    opy_argv = argv[1:]

    if py_path.endswith('.py'):
      #py_parser = Pgen2PythonParser(dr, FILE_INPUT)
      #printer = TupleTreePrinter(transformer._names)
      #tr = transformer.Pgen2Transformer(py_parser, printer)
      #with open(py_path) as f:
      #  contents = f.read()
      #co = pycodegen.compile(contents, py_path, 'exec', transformer=tr)
      #execfile.run_code_object(co, opy_argv)
      pass

    elif py_path.endswith('.pyc') or py_path.endswith('.opyc'):
      with open(py_path) as f:
        f.seek(8)  # past header.  TODO: validate it!
        co = marshal.load(f)
      #execfile.run_code_object(co, opy_argv)

    else:
      raise args.UsageError('Invalid path %r' % py_path)

  else:
    raise args.UsageError('Invalid action %r' % action)

  # Examples of nodes Leaf(type, value):
  #   Leaf(1, 'def')
  #   Leaf(4, '\n')
  #   Leaf(8, ')')
  # Oh are these just tokens?
  # yes.

  # Node(prefix, children)
