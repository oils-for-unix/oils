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
import types

from . import pytree
from . import skeleton

from .compiler2 import consts
from .compiler2 import dis_tool
from .compiler2 import misc
from .compiler2 import transformer

# Disabled for now because byterun imports 'six', and that breaks the build.
from .byterun import execfile
from .byterun import ovm

from pgen2 import driver, parse, pgen, grammar
from pgen2 import token
from pgen2 import tokenize

from frontend import args
from core.util import log
from core import pyutil

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from typing import Dict
  from pgen2.parse import PNode


# From lib2to3/pygram.py.  This takes the place of the 'symbol' module.
# compiler/transformer module needs this.

class Symbols(object):

  def __init__(self, gr):
    """
    Creates an attribute for each grammar symbol (nonterminal), whose value is
    the symbol's type (an int >= 256).
    """
    for name, symbol in gr.symbol2number.items():
        setattr(self, name, symbol)
        #log('%s -> %d' % (name, symbol))
    # For transformer to use
    self.number2symbol = gr.number2symbol


def HostStdlibNames():
  import symbol
  import token
  names = {}
  for k, v in symbol.sym_name.items():
    names[k] = v
  for k, v in token.tok_name.items():
    names[k] = v
  return names


def WriteGrammar(grammar_path, marshal_path):
  """Used for py27.grammar.
  
  oil_lang/grammar.pgen2 uses oil_lang/grammar_gen.py
  """
  with open(grammar_path) as f:
    gr = pgen.MakeGrammar(f)

  with open(marshal_path, 'wb') as out_f:
    gr.dump(out_f)

  log('Compiled %s -> grammar tables in %s', grammar_path, marshal_path)


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
    # TODO: parameterize by grammar.
    self.max_token_index = max(token.tok_name)

  def Print(self, tu, f=sys.stdout, indent=0):
    ind = '  ' * indent
    f.write(ind)
    if isinstance(tu, tuple):
      num = tu[0]
      if num < self.max_token_index:
        f.write(self._names[num])
        f.write(' %s (%d, %d)\n' % (tu[1], tu[2], tu[3]))
        return
      f.write(self._names[num])
      f.write('\n')
      for entry in tu[1:]:
        self.Print(entry, f, indent=indent+1)
    elif isinstance(tu, int):
      f.write(str(tu))
      f.write('\n')
    elif isinstance(tu, str):
      f.write(tu)
      f.write('\n')
    else:
      raise AssertionError(tu)


class ParseTreePrinter(object):
  """Prints a tree of PNode instances."""
  def __init__(self, names):
    # type: (Dict[int, str]) -> None
    self.names = names
    self.f = sys.stdout

  def Print(self, pnode, f=sys.stdout, indent=0, i=0):
    # type: (PNode, int, int) -> None

    ind = '  ' * indent
    # NOTE:
    # - 'tok' used to be opaque context
    #   - it's None for PRODUCTIONS (nonterminals)
    #   - for terminals, it's (prefix, (lineno, column)), where lineno is
    #     1-based, and 'prefix' is a string of whitespace.
    #     e.g. for 'f(1, 3)', the "3" token has a prefix of ' '.
    if isinstance(pnode.tok, tuple):
      # Used for ParseWith
      v = pnode.tok[0]
    else:
      v = '-'
    self.f.write('%s%d %s %s\n' % (ind, i, self.names[pnode.typ], v))
    if pnode.children:  # could be None
      for i, child in enumerate(pnode.children):
        self.Print(child, indent=indent+1, i=i)


class TableOutput(object):

  def __init__(self, out_dir):
    self.out_dir = out_dir
    self.frames_f = open(os.path.join(out_dir, 'frames.tsv2'), 'w')
    self.names_f = open(os.path.join(out_dir, 'names.tsv2'), 'w')
    self.consts_f = open(os.path.join(out_dir, 'consts.tsv2'), 'w')
    self.flags_f = open(os.path.join(out_dir, 'flags.tsv2'), 'w')
    self.ops_f = open(os.path.join(out_dir, 'ops.tsv2'), 'w')

    # NOTE: The opcode encoding is variable length, so bytecode_bytes is
    # different than the number of instructions.
    print('path\tcode_name\targcount\tnlocals\tstacksize\tbytecode_bytes',
        file=self.frames_f)
    print('path\tcode_name\tkind\tname', file=self.names_f)
    print('path\tcode_name\ttype\tlen_or_val', file=self.consts_f)
    print('path\tcode_name\tflag', file=self.flags_f)
    print('path\tcode_name\top_name\top_arg', file=self.ops_f)

  def WriteFrameRow(self, path, code_name, argcount, nlocals, stacksize,
                    bytecode_bytes):
    row = [path, code_name, str(argcount), str(nlocals), str(stacksize),
           str(bytecode_bytes)]
    print('\t'.join(row), file=self.frames_f)

  def WriteNameRow(self, path, code_name, kind, name):
    row = [path, code_name, kind, name]
    print('\t'.join(row), file=self.names_f)

  def WriteConstRow(self, path, code_name, type_, len_or_val):
    row = [path, code_name, type_, str(len_or_val)]
    print('\t'.join(row), file=self.consts_f)

  def WriteFlagRow(self, path, code_name, flag_name):
    row = [path, code_name, flag_name]
    print('\t'.join(row), file=self.flags_f)

  def WriteOpRow(self, path, code_name, op_name, op_arg):
    row = [path, code_name, op_name, str(op_arg)]
    print('\t'.join(row), file=self.ops_f)

  def Close(self):
    self.frames_f.close()
    self.names_f.close()
    self.consts_f.close()
    self.flags_f.close()
    self.ops_f.close()
    log('Wrote 5 files in %s', self.out_dir)


def WriteDisTables(pyc_path, co, out):
  """Write 3 TSV files."""
  #log('Disassembling %s in %s', co, pyc_path)
  out.WriteFrameRow(pyc_path, co.co_name, co.co_argcount, co.co_nlocals,
                    co.co_stacksize, len(co.co_code))

  # Write a row for every name
  for name in co.co_names:
    out.WriteNameRow(pyc_path, co.co_name, 'name', name)
  for name in co.co_varnames:
    out.WriteNameRow(pyc_path, co.co_name, 'var', name)
  for name in co.co_cellvars:
    out.WriteNameRow(pyc_path, co.co_name, 'cell', name)
  for name in co.co_freevars:
    out.WriteNameRow(pyc_path, co.co_name, 'free', name)

  # Write a row for every op.
  for op_name, op_arg in dis_tool.ParseOps(co.co_code):
    out.WriteOpRow(pyc_path, co.co_name, op_name, op_arg)

  # TODO: Write a row for every flag.  OPy outputs these:
  # CO_VARARGS, CO_VAR_KEYWORDS, CO_GENERATOR, CO_NEWLOCALS (we only support
  # this?)  FUTURE_DIVISION, FUTURE_ABSOLUTE_IMPORT, etc.
  for flag in sorted(consts.VALUE_TO_NAME):
    if co.co_flags & flag:
      flag_name = consts.VALUE_TO_NAME[flag]
      out.WriteFlagRow(pyc_path, co.co_name, flag_name)

  # Write a row for every constant
  for const in co.co_consts:
    if isinstance(const, int):
      len_or_val = const
    elif isinstance(const, (str, tuple)):
      len_or_val = len(const)
    else:
      len_or_val = 'NA'
    out.WriteConstRow(pyc_path, co.co_name, const.__class__.__name__, len_or_val)

    if isinstance(const, types.CodeType):
      WriteDisTables(pyc_path, const, out)


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser()

  # NOTE: default command is None because empty string is valid.

  # NOTE: In 'opy run oil.pyc -c', -c is an arg to opy, and not a flag.

  p.add_option(
      '-c', dest='command', default=None,
      help='Python command to run')
  return p


# Made by the Makefile.
GRAMMAR_REL_PATH = '_build/opy/py27.grammar.marshal'

def OpyCommandMain(argv):
  """Dispatch to the right action."""

  # TODO: Use core/args.
  #opts, argv = Options().parse_args(argv)

  try:
    action = argv[0]
  except IndexError:
    raise args.UsageError('opy: Missing required subcommand.')

  argv = argv[1:]  # TODO: Should I do input.ReadRequiredArg()?
                   # That will shift the input.

  if action in (
      'parse', 'parse-with', 'compile', 'dis', 'ast', 'symbols', 'cfg',
      'compile-ovm', 'eval', 'repl', 'run', 'run-ovm'):
    loader = pyutil.GetResourceLoader()
    f = loader.open(GRAMMAR_REL_PATH)
    contents = f.read()
    f.close()
    gr = grammar.Grammar()
    gr.loads(contents)

    # In Python 2 code, always use from __future__ import print_function.
    try:
      del gr.keywords["print"]
    except KeyError:
      pass

    symbols = Symbols(gr)
    pytree.Init(symbols)  # for type_repr() pretty printing
    transformer.Init(symbols)  # for _names and other dicts

    compiler = skeleton.Compiler(gr)
  else:
    # e.g. pgen2 doesn't use any of these.  Maybe we should make a different
    # tool.
    compiler = None

  # TODO: Also have a run_spec for 'opyc run'.
  compile_spec = args.OilFlags()
  compile_spec.Flag('-emit-docstring', args.Bool, default=True,
                    help='Whether to emit docstrings')
  compile_spec.Flag('-fast-ops', args.Bool, default=True,
                    help='Whether to emit LOAD_FAST, STORE_FAST, etc.')
  compile_spec.Flag('-oil-subset', args.Bool, default=False,
                    help='Only allow the constructs necessary to implement'
                    'Oil. Example: using multiple inheritance will abort '
                    'compilation.')

  #
  # Actions
  #

  if action == 'pgen2':
    grammar_path = argv[0]
    marshal_path = argv[1]
    WriteGrammar(grammar_path, marshal_path)

  elif action == 'stdlib-parse':
    # This is what the compiler/ package was written against.
    import parser

    py_path = argv[1]
    with open(py_path) as f:
      st = parser.suite(f.read())

    tree = st.totuple()

    printer = TupleTreePrinter(HostStdlibNames())
    printer.Print(tree)
    n = CountTupleTree(tree)
    log('COUNT %d', n)

  elif action == 'lex':
    py_path = argv[0]
    with open(py_path) as f:
      tokens = tokenize.generate_tokens(f.readline)
      for typ, val, start, end, unused_line in tokens:
        print('%10s %10s %-10s %r' % (start, end, token.tok_name[typ], val))

  elif action == 'lex-names':  # Print all the NAME tokens.
    for py_path in argv:
      log('Lexing %s', py_path)
      with open(py_path) as f:
        tokens = tokenize.generate_tokens(f.readline)
        for typ, val, start, end, unused_line in tokens:
          if typ == token.NAME:
            print(val)

  elif action == 'parse':
    py_path = argv[0]
    with open(py_path) as f:
      tokens = tokenize.generate_tokens(f.readline)
      p = parse.Parser(gr)
      pnode  = driver.PushTokens(p, tokens, gr, 'file_input')

    printer = ParseTreePrinter(transformer._names)  # print raw nodes
    printer.Print(pnode)

  # Parse with an arbitrary grammar, but the Python lexer.
  elif action == 'parse-with':
    grammar_path = argv[0]
    start_symbol = argv[1]
    code_str = argv[2]

    with open(grammar_path) as f:
      gr = pgen.MakeGrammar(f)

    f = cStringIO.StringIO(code_str)
    tokens = tokenize.generate_tokens(f.readline)
    p = parse.Parser(gr)  # no convert=
    try:
      pnode = driver.PushTokens(p, tokens, gr, start_symbol)
    except parse.ParseError as e:
      # Extract location information and show it.
      _, _, (lineno, offset) = e.opaque
      # extra line needed for '\n' ?
      lines = code_str.splitlines() + ['']

      line = lines[lineno-1]
      log('  %s', line)
      log('  %s^', ' '*offset)
      log('Parse Error: %s', e)
      return 1
    printer = ParseTreePrinter(transformer._names)  # print raw nodes
    printer.Print(pnode)

  elif action == 'ast':  # output AST
    opt, i = compile_spec.ParseArgv(argv)
    py_path = argv[i]
    with open(py_path) as f:
      graph = compiler.Compile(f, opt, 'exec', print_action='ast')

  elif action == 'symbols':  # output symbols
    opt, i = compile_spec.ParseArgv(argv)
    py_path = argv[i]
    with open(py_path) as f:
      graph = compiler.Compile(f, opt, 'exec', print_action='symbols')

  elif action == 'cfg':  # output Control Flow Graph
    opt, i = compile_spec.ParseArgv(argv)
    py_path = argv[i]
    with open(py_path) as f:
      graph = compiler.Compile(f, opt, 'exec', print_action='cfg')

  elif action == 'compile':  # 'opyc compile' is pgen2 + compiler2
    # spec.Arg('action', ['foo', 'bar'])
    # But that leads to some duplication.

    opt, i = compile_spec.ParseArgv(argv)

    py_path = argv[i]
    out_path = argv[i+1]

    with open(py_path) as f:
      co = compiler.Compile(f, opt, 'exec')

    log("Compiled to %d bytes of top-level bytecode", len(co.co_code))

    # Write the .pyc file
    with open(out_path, 'wb') as out_f:
      h = misc.getPycHeader(py_path)
      out_f.write(h)
      marshal.dump(co, out_f)

  elif action == 'compile-ovm':
    # NOTE: obsolete
    from ovm2 import oheap2
    opt, i = compile_spec.ParseArgv(argv)
    py_path = argv[i]
    out_path = argv[i+1]

    # Compile to Python bytecode (TODO: remove ovm_codegen.py)
    mode = 'exec'
    with open(py_path) as f:
      co = compiler.Compile(f, opt, mode)

    if 1:
      with open(out_path, 'wb') as out_f:
        oheap2.Write(co, out_f)
      return 0

    log("Compiled to %d bytes of top-level bytecode", len(co.co_code))
    # Write the .pyc file
    with open(out_path, 'wb') as out_f:
      if 1:
        out_f.write(co.co_code)
      else:
        h = misc.getPycHeader(py_path)
        out_f.write(h)
        marshal.dump(co, out_f)
    log('Wrote only the bytecode to %r', out_path)

  elif action == 'eval':  # Like compile, but parses to a code object and prints it
    opt, i = compile_spec.ParseArgv(argv)
    py_expr = argv[i]
    f = skeleton.StringInput(py_expr, '<eval input>')
    co = compiler.Compile(f, opt, 'eval')

    v = dis_tool.Visitor()
    v.show_code(co)
    print()
    print('RESULT:')
    print(eval(co))

  elif action == 'repl':  # Like eval in a loop
    while True:
      py_expr = raw_input('opy> ')
      f = skeleton.StringInput(py_expr, '<REPL input>')

      # TODO: change this to 'single input'?  Why doesn't this work?
      co = compiler.Compile(f, opt, 'eval')

      v = dis_tool.Visitor()
      v.show_code(co)
      print(eval(co))

  elif action == 'dis-tables':
    out_dir = argv[0]
    pyc_paths = argv[1:]

    out = TableOutput(out_dir)

    for pyc_path in pyc_paths:
      with open(pyc_path) as f:
        magic, unixtime, timestamp, code = dis_tool.unpack_pyc(f)
        WriteDisTables(pyc_path, code, out)

    out.Close()

  elif action == 'dis':
    opt, i = compile_spec.ParseArgv(argv)
    path = argv[i]
    v = dis_tool.Visitor()

    if path.endswith('.py'):
      with open(path) as f:
        co = compiler.Compile(f, opt, 'exec')

      log("Compiled to %d bytes of top-level bytecode", len(co.co_code))
      v.show_code(co)

    else:  # assume pyc_path
      with open(path, 'rb') as f:
        v.Visit(f)

  elif action == 'dis-md5':
    pyc_paths = argv
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

  elif action == 'run':  # Compile and run, without writing pyc file
    # TODO: Add an option like -v in __main__

    #level = logging.DEBUG if args.verbose else logging.WARNING
    #logging.basicConfig(level=level)
    #logging.basicConfig(level=logging.DEBUG)

    opt, i = compile_spec.ParseArgv(argv)

    py_path = argv[i]
    opy_argv = argv[i:]

    if py_path.endswith('.py'):
      with open(py_path) as f:
        co = compiler.Compile(f, opt, 'exec')
      num_ticks = execfile.run_code_object(co, opy_argv)

    elif py_path.endswith('.pyc') or py_path.endswith('.opyc'):
      with open(py_path) as f:
        f.seek(8)  # past header.  TODO: validate it!
        co = marshal.load(f)
      num_ticks = execfile.run_code_object(co, opy_argv)

    else:
      raise args.UsageError('Invalid path %r' % py_path)

  elif action == 'run-ovm':  # Compile and run, without writing pyc file
    opt, i = compile_spec.ParseArgv(argv)
    py_path = argv[i]
    opy_argv = argv[i+1:]

    if py_path.endswith('.py'):
      #mode = 'exec'
      mode = 'ovm'  # OVM bytecode is different!
      with open(py_path) as f:
        co = compiler.Compile(f, opt, mode)
      log('Compiled to %d bytes of OVM code', len(co.co_code))
      num_ticks = ovm.run_code_object(co, opy_argv)

    elif py_path.endswith('.pyc') or py_path.endswith('.opyc'):
      with open(py_path) as f:
        f.seek(8)  # past header.  TODO: validate it!
        co = marshal.load(f)
      num_ticks = ovm.run_code_object(co, opy_argv)

    else:
      raise args.UsageError('Invalid path %r' % py_path)

  else:
    raise args.UsageError('Invalid action %r' % action)
