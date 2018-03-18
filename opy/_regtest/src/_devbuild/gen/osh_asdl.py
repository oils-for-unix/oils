from asdl import const  # For const.NO_INTEGER
from asdl import py_meta
from osh.meta import OSH_TYPE_LOOKUP as TYPE_LOOKUP

class line_span(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('line_span')
  __slots__ = ('line_id', 'col', 'length', 'spids')

  def __init__(self, line_id=None, col=None, length=None, spids=None):
    self.line_id = line_id
    self.col = col
    self.length = length
    self.spids = spids or []

class token(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('token')
  __slots__ = ('id', 'val', 'span_id', 'spids')

  def __init__(self, id=None, val=None, span_id=None, spids=None):
    self.id = id
    self.val = val
    self.span_id = span_id
    self.spids = spids or []

class braced_step(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('braced_step')
  __slots__ = ('val', 'negated', 'spids')

  def __init__(self, val=None, negated=None, spids=None):
    self.val = val
    self.negated = negated
    self.spids = spids or []

class bracket_op_e(object):
  WholeArray = 1
  ArrayIndex = 2

class bracket_op(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('bracket_op')

class WholeArray(bracket_op):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('WholeArray')
  __slots__ = ('op_id', 'spids')

  def __init__(self, op_id=None, spids=None):
    self.op_id = op_id
    self.spids = spids or []

class ArrayIndex(bracket_op):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArrayIndex')
  __slots__ = ('expr', 'spids')

  def __init__(self, expr=None, spids=None):
    self.expr = expr
    self.spids = spids or []

class suffix_op_e(object):
  StringUnary = 1
  PatSub = 2
  Slice = 3

class suffix_op(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('suffix_op')

class StringUnary(suffix_op):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('StringUnary')
  __slots__ = ('op_id', 'arg_word', 'spids')

  def __init__(self, op_id=None, arg_word=None, spids=None):
    self.op_id = op_id
    self.arg_word = arg_word
    self.spids = spids or []

class PatSub(suffix_op):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('PatSub')
  __slots__ = ('pat', 'replace', 'do_all', 'do_prefix', 'do_suffix', 'spids')

  def __init__(self, pat=None, replace=None, do_all=None, do_prefix=None,
               do_suffix=None, spids=None):
    self.pat = pat
    self.replace = replace or None
    self.do_all = do_all
    self.do_prefix = do_prefix
    self.do_suffix = do_suffix
    self.spids = spids or []

class Slice(suffix_op):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Slice')
  __slots__ = ('begin', 'length', 'spids')

  def __init__(self, begin=None, length=None, spids=None):
    self.begin = begin or None
    self.length = length or None
    self.spids = spids or []

class array_item_e(object):
  ArrayWord = 1
  ArrayPair = 2

class array_item(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('array_item')

class ArrayWord(array_item):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArrayWord')
  __slots__ = ('w', 'spids')

  def __init__(self, w=None, spids=None):
    self.w = w
    self.spids = spids or []

class ArrayPair(array_item):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArrayPair')
  __slots__ = ('key', 'value', 'spids')

  def __init__(self, key=None, value=None, spids=None):
    self.key = key
    self.value = value
    self.spids = spids or []

class word_part_e(object):
  ArrayLiteralPart = 1
  LiteralPart = 2
  EscapedLiteralPart = 3
  EmptyPart = 4
  SingleQuotedPart = 5
  DoubleQuotedPart = 6
  SimpleVarSub = 7
  BracedVarSub = 8
  TildeSubPart = 9
  CommandSubPart = 10
  ArithSubPart = 11
  BracedAltPart = 12
  BracedIntRangePart = 13
  BracedCharRangePart = 14
  ExtGlobPart = 15

class word_part(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('word_part')

class ArrayLiteralPart(word_part):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArrayLiteralPart')
  __slots__ = ('words', 'spids')

  def __init__(self, words=None, spids=None):
    self.words = words or []
    self.spids = spids or []

class LiteralPart(word_part):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LiteralPart')
  __slots__ = ('token', 'spids')

  def __init__(self, token=None, spids=None):
    self.token = token
    self.spids = spids or []

class EscapedLiteralPart(word_part):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('EscapedLiteralPart')
  __slots__ = ('token', 'spids')

  def __init__(self, token=None, spids=None):
    self.token = token
    self.spids = spids or []

class EmptyPart(word_part):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('EmptyPart')
  tag = 4

class SingleQuotedPart(word_part):
  tag = 5
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('SingleQuotedPart')
  __slots__ = ('left', 'tokens', 'spids')

  def __init__(self, left=None, tokens=None, spids=None):
    self.left = left
    self.tokens = tokens or []
    self.spids = spids or []

class DoubleQuotedPart(word_part):
  tag = 6
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('DoubleQuotedPart')
  __slots__ = ('parts', 'spids')

  def __init__(self, parts=None, spids=None):
    self.parts = parts or []
    self.spids = spids or []

class SimpleVarSub(word_part):
  tag = 7
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('SimpleVarSub')
  __slots__ = ('token', 'spids')

  def __init__(self, token=None, spids=None):
    self.token = token
    self.spids = spids or []

class BracedVarSub(word_part):
  tag = 8
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BracedVarSub')
  __slots__ = ('token', 'prefix_op', 'bracket_op', 'suffix_op', 'spids')

  def __init__(self, token=None, prefix_op=None, bracket_op=None,
               suffix_op=None, spids=None):
    self.token = token
    self.prefix_op = prefix_op or None
    self.bracket_op = bracket_op or None
    self.suffix_op = suffix_op or None
    self.spids = spids or []

class TildeSubPart(word_part):
  tag = 9
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('TildeSubPart')
  __slots__ = ('prefix', 'spids')

  def __init__(self, prefix=None, spids=None):
    self.prefix = prefix
    self.spids = spids or []

class CommandSubPart(word_part):
  tag = 10
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('CommandSubPart')
  __slots__ = ('command_list', 'left_token', 'spids')

  def __init__(self, command_list=None, left_token=None, spids=None):
    self.command_list = command_list
    self.left_token = left_token
    self.spids = spids or []

class ArithSubPart(word_part):
  tag = 11
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArithSubPart')
  __slots__ = ('anode', 'spids')

  def __init__(self, anode=None, spids=None):
    self.anode = anode
    self.spids = spids or []

class BracedAltPart(word_part):
  tag = 12
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BracedAltPart')
  __slots__ = ('words', 'spids')

  def __init__(self, words=None, spids=None):
    self.words = words or []
    self.spids = spids or []

class BracedIntRangePart(word_part):
  tag = 13
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BracedIntRangePart')
  __slots__ = ('start', 'end', 'step', 'spids')

  def __init__(self, start=None, end=None, step=None, spids=None):
    self.start = start
    self.end = end
    self.step = step or None
    self.spids = spids or []

class BracedCharRangePart(word_part):
  tag = 14
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BracedCharRangePart')
  __slots__ = ('start', 'end', 'step', 'spids')

  def __init__(self, start=None, end=None, step=None, spids=None):
    self.start = start
    self.end = end
    self.step = step or None
    self.spids = spids or []

class ExtGlobPart(word_part):
  tag = 15
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ExtGlobPart')
  __slots__ = ('op', 'arms', 'spids')

  def __init__(self, op=None, arms=None, spids=None):
    self.op = op
    self.arms = arms or []
    self.spids = spids or []

class word_e(object):
  TokenWord = 1
  CompoundWord = 2
  BracedWordTree = 3
  StringWord = 4

class word(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('word')

class TokenWord(word):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('TokenWord')
  __slots__ = ('token', 'spids')

  def __init__(self, token=None, spids=None):
    self.token = token
    self.spids = spids or []

class CompoundWord(word):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('CompoundWord')
  __slots__ = ('parts', 'spids')

  def __init__(self, parts=None, spids=None):
    self.parts = parts or []
    self.spids = spids or []

class BracedWordTree(word):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BracedWordTree')
  __slots__ = ('parts', 'spids')

  def __init__(self, parts=None, spids=None):
    self.parts = parts or []
    self.spids = spids or []

class StringWord(word):
  tag = 4
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('StringWord')
  __slots__ = ('id', 's', 'spids')

  def __init__(self, id=None, s=None, spids=None):
    self.id = id
    self.s = s
    self.spids = spids or []

class lhs_expr_e(object):
  LhsName = 1
  LhsIndexedName = 2

class lhs_expr(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('lhs_expr')

class LhsName(lhs_expr):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LhsName')
  __slots__ = ('name', 'spids')

  def __init__(self, name=None, spids=None):
    self.name = name
    self.spids = spids or []

class LhsIndexedName(lhs_expr):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LhsIndexedName')
  __slots__ = ('name', 'index', 'spids')

  def __init__(self, name=None, index=None, spids=None):
    self.name = name
    self.index = index
    self.spids = spids or []

class arith_expr_e(object):
  ArithVarRef = 1
  ArithWord = 2
  UnaryAssign = 3
  BinaryAssign = 4
  ArithUnary = 5
  ArithBinary = 6
  TernaryOp = 7
  FuncCall = 8

class arith_expr(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('arith_expr')

class ArithVarRef(arith_expr):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArithVarRef')
  __slots__ = ('name', 'spids')

  def __init__(self, name=None, spids=None):
    self.name = name
    self.spids = spids or []

class ArithWord(arith_expr):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArithWord')
  __slots__ = ('w', 'spids')

  def __init__(self, w=None, spids=None):
    self.w = w
    self.spids = spids or []

class UnaryAssign(arith_expr):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('UnaryAssign')
  __slots__ = ('op_id', 'child', 'spids')

  def __init__(self, op_id=None, child=None, spids=None):
    self.op_id = op_id
    self.child = child
    self.spids = spids or []

class BinaryAssign(arith_expr):
  tag = 4
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BinaryAssign')
  __slots__ = ('op_id', 'left', 'right', 'spids')

  def __init__(self, op_id=None, left=None, right=None, spids=None):
    self.op_id = op_id
    self.left = left
    self.right = right
    self.spids = spids or []

class ArithUnary(arith_expr):
  tag = 5
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArithUnary')
  __slots__ = ('op_id', 'child', 'spids')

  def __init__(self, op_id=None, child=None, spids=None):
    self.op_id = op_id
    self.child = child
    self.spids = spids or []

class ArithBinary(arith_expr):
  tag = 6
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArithBinary')
  __slots__ = ('op_id', 'left', 'right', 'spids')

  def __init__(self, op_id=None, left=None, right=None, spids=None):
    self.op_id = op_id
    self.left = left
    self.right = right
    self.spids = spids or []

class TernaryOp(arith_expr):
  tag = 7
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('TernaryOp')
  __slots__ = ('cond', 'true_expr', 'false_expr', 'spids')

  def __init__(self, cond=None, true_expr=None, false_expr=None, spids=None):
    self.cond = cond
    self.true_expr = true_expr
    self.false_expr = false_expr
    self.spids = spids or []

class FuncCall(arith_expr):
  tag = 8
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('FuncCall')
  __slots__ = ('func', 'args', 'spids')

  def __init__(self, func=None, args=None, spids=None):
    self.func = func
    self.args = args or []
    self.spids = spids or []

class bool_expr_e(object):
  WordTest = 1
  BoolBinary = 2
  BoolUnary = 3
  LogicalNot = 4
  LogicalAnd = 5
  LogicalOr = 6

class bool_expr(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('bool_expr')

class WordTest(bool_expr):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('WordTest')
  __slots__ = ('w', 'spids')

  def __init__(self, w=None, spids=None):
    self.w = w
    self.spids = spids or []

class BoolBinary(bool_expr):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BoolBinary')
  __slots__ = ('op_id', 'left', 'right', 'spids')

  def __init__(self, op_id=None, left=None, right=None, spids=None):
    self.op_id = op_id
    self.left = left
    self.right = right
    self.spids = spids or []

class BoolUnary(bool_expr):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BoolUnary')
  __slots__ = ('op_id', 'child', 'spids')

  def __init__(self, op_id=None, child=None, spids=None):
    self.op_id = op_id
    self.child = child
    self.spids = spids or []

class LogicalNot(bool_expr):
  tag = 4
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LogicalNot')
  __slots__ = ('child', 'spids')

  def __init__(self, child=None, spids=None):
    self.child = child
    self.spids = spids or []

class LogicalAnd(bool_expr):
  tag = 5
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LogicalAnd')
  __slots__ = ('left', 'right', 'spids')

  def __init__(self, left=None, right=None, spids=None):
    self.left = left
    self.right = right
    self.spids = spids or []

class LogicalOr(bool_expr):
  tag = 6
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LogicalOr')
  __slots__ = ('left', 'right', 'spids')

  def __init__(self, left=None, right=None, spids=None):
    self.left = left
    self.right = right
    self.spids = spids or []

class redir_e(object):
  Redir = 1
  HereDoc = 2

class redir(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('redir')

class Redir(redir):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Redir')
  __slots__ = ('op_id', 'fd', 'arg_word', 'spids')

  def __init__(self, op_id=None, fd=None, arg_word=None, spids=None):
    self.op_id = op_id
    self.fd = fd
    self.arg_word = arg_word
    self.spids = spids or []

class HereDoc(redir):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('HereDoc')
  __slots__ = ('op_id', 'fd', 'body', 'do_expansion', 'here_end', 'was_filled',
               'spids')

  def __init__(self, op_id=None, fd=None, body=None, do_expansion=None,
               here_end=None, was_filled=None, spids=None):
    self.op_id = op_id
    self.fd = fd
    self.body = body or None
    self.do_expansion = do_expansion
    self.here_end = here_end
    self.was_filled = was_filled
    self.spids = spids or []

class assign_op_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('assign_op')

assign_op_e.Equal = assign_op_e(1, 'Equal')
assign_op_e.PlusEqual = assign_op_e(2, 'PlusEqual')

class assign_pair(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('assign_pair')
  __slots__ = ('lhs', 'op', 'rhs', 'spids')

  def __init__(self, lhs=None, op=None, rhs=None, spids=None):
    self.lhs = lhs
    self.op = op
    self.rhs = rhs or None
    self.spids = spids or []

class env_pair(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('env_pair')
  __slots__ = ('name', 'val', 'spids')

  def __init__(self, name=None, val=None, spids=None):
    self.name = name
    self.val = val
    self.spids = spids or []

class case_arm(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('case_arm')
  __slots__ = ('pat_list', 'action', 'spids')

  def __init__(self, pat_list=None, action=None, spids=None):
    self.pat_list = pat_list or []
    self.action = action or []
    self.spids = spids or []

class if_arm(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('if_arm')
  __slots__ = ('cond', 'action', 'spids')

  def __init__(self, cond=None, action=None, spids=None):
    self.cond = cond or []
    self.action = action or []
    self.spids = spids or []

class iterable_e(object):
  IterArgv = 1
  IterArray = 2

class iterable(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('iterable')

class IterArgv(iterable):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('IterArgv')
  tag = 1

class IterArray(iterable):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('IterArray')
  __slots__ = ('words', 'spids')

  def __init__(self, words=None, spids=None):
    self.words = words or []
    self.spids = spids or []

class command_e(object):
  NoOp = 1
  SimpleCommand = 2
  Sentence = 3
  Assignment = 4
  ControlFlow = 5
  Pipeline = 6
  AndOr = 7
  DoGroup = 8
  BraceGroup = 9
  Subshell = 10
  DParen = 11
  DBracket = 12
  ForEach = 13
  ForExpr = 14
  While = 15
  Until = 16
  If = 17
  Case = 18
  FuncDef = 19
  TimeBlock = 20
  CommandList = 21

class command(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('command')

class NoOp(command):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('NoOp')
  tag = 1

class SimpleCommand(command):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('SimpleCommand')
  __slots__ = ('words', 'redirects', 'more_env', 'spids')

  def __init__(self, words=None, redirects=None, more_env=None, spids=None):
    self.words = words or []
    self.redirects = redirects or []
    self.more_env = more_env or []
    self.spids = spids or []

class Sentence(command):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Sentence')
  __slots__ = ('child', 'terminator', 'spids')

  def __init__(self, child=None, terminator=None, spids=None):
    self.child = child
    self.terminator = terminator
    self.spids = spids or []

class Assignment(command):
  tag = 4
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Assignment')
  __slots__ = ('keyword', 'flags', 'pairs', 'spids')

  def __init__(self, keyword=None, flags=None, pairs=None, spids=None):
    self.keyword = keyword
    self.flags = flags or []
    self.pairs = pairs or []
    self.spids = spids or []

class ControlFlow(command):
  tag = 5
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ControlFlow')
  __slots__ = ('token', 'arg_word', 'spids')

  def __init__(self, token=None, arg_word=None, spids=None):
    self.token = token
    self.arg_word = arg_word or None
    self.spids = spids or []

class Pipeline(command):
  tag = 6
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Pipeline')
  __slots__ = ('children', 'negated', 'stderr_indices', 'spids')

  def __init__(self, children=None, negated=None, stderr_indices=None,
               spids=None):
    self.children = children or []
    self.negated = negated
    self.stderr_indices = stderr_indices or []
    self.spids = spids or []

class AndOr(command):
  tag = 7
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('AndOr')
  __slots__ = ('ops', 'children', 'spids')

  def __init__(self, ops=None, children=None, spids=None):
    self.ops = ops or []
    self.children = children or []
    self.spids = spids or []

class DoGroup(command):
  tag = 8
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('DoGroup')
  __slots__ = ('children', 'redirects', 'spids')

  def __init__(self, children=None, redirects=None, spids=None):
    self.children = children or []
    self.redirects = redirects or []
    self.spids = spids or []

class BraceGroup(command):
  tag = 9
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('BraceGroup')
  __slots__ = ('children', 'redirects', 'spids')

  def __init__(self, children=None, redirects=None, spids=None):
    self.children = children or []
    self.redirects = redirects or []
    self.spids = spids or []

class Subshell(command):
  tag = 10
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Subshell')
  __slots__ = ('child', 'redirects', 'spids')

  def __init__(self, child=None, redirects=None, spids=None):
    self.child = child
    self.redirects = redirects or []
    self.spids = spids or []

class DParen(command):
  tag = 11
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('DParen')
  __slots__ = ('child', 'redirects', 'spids')

  def __init__(self, child=None, redirects=None, spids=None):
    self.child = child
    self.redirects = redirects or []
    self.spids = spids or []

class DBracket(command):
  tag = 12
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('DBracket')
  __slots__ = ('expr', 'redirects', 'spids')

  def __init__(self, expr=None, redirects=None, spids=None):
    self.expr = expr
    self.redirects = redirects or []
    self.spids = spids or []

class ForEach(command):
  tag = 13
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ForEach')
  __slots__ = ('iter_name', 'iter_words', 'do_arg_iter', 'body', 'redirects',
               'spids')

  def __init__(self, iter_name=None, iter_words=None, do_arg_iter=None,
               body=None, redirects=None, spids=None):
    self.iter_name = iter_name
    self.iter_words = iter_words or []
    self.do_arg_iter = do_arg_iter
    self.body = body
    self.redirects = redirects or []
    self.spids = spids or []

class ForExpr(command):
  tag = 14
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ForExpr')
  __slots__ = ('init', 'cond', 'update', 'body', 'redirects', 'spids')

  def __init__(self, init=None, cond=None, update=None, body=None,
               redirects=None, spids=None):
    self.init = init or None
    self.cond = cond or None
    self.update = update or None
    self.body = body or None
    self.redirects = redirects or []
    self.spids = spids or []

class While(command):
  tag = 15
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('While')
  __slots__ = ('cond', 'body', 'redirects', 'spids')

  def __init__(self, cond=None, body=None, redirects=None, spids=None):
    self.cond = cond or []
    self.body = body
    self.redirects = redirects or []
    self.spids = spids or []

class Until(command):
  tag = 16
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Until')
  __slots__ = ('cond', 'body', 'redirects', 'spids')

  def __init__(self, cond=None, body=None, redirects=None, spids=None):
    self.cond = cond or []
    self.body = body
    self.redirects = redirects or []
    self.spids = spids or []

class If(command):
  tag = 17
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('If')
  __slots__ = ('arms', 'else_action', 'redirects', 'spids')

  def __init__(self, arms=None, else_action=None, redirects=None, spids=None):
    self.arms = arms or []
    self.else_action = else_action or []
    self.redirects = redirects or []
    self.spids = spids or []

class Case(command):
  tag = 18
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Case')
  __slots__ = ('to_match', 'arms', 'redirects', 'spids')

  def __init__(self, to_match=None, arms=None, redirects=None, spids=None):
    self.to_match = to_match
    self.arms = arms or []
    self.redirects = redirects or []
    self.spids = spids or []

class FuncDef(command):
  tag = 19
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('FuncDef')
  __slots__ = ('name', 'body', 'redirects', 'spids')

  def __init__(self, name=None, body=None, redirects=None, spids=None):
    self.name = name
    self.body = body
    self.redirects = redirects or []
    self.spids = spids or []

class TimeBlock(command):
  tag = 20
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('TimeBlock')
  __slots__ = ('pipeline', 'spids')

  def __init__(self, pipeline=None, spids=None):
    self.pipeline = pipeline
    self.spids = spids or []

class CommandList(command):
  tag = 21
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('CommandList')
  __slots__ = ('children', 'spids')

  def __init__(self, children=None, spids=None):
    self.children = children or []
    self.spids = spids or []

class arena(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('arena')
  __slots__ = ('lines', 'spans', 'root', 'spids')

  def __init__(self, lines=None, spans=None, root=None, spids=None):
    self.lines = lines or []
    self.spans = spans or []
    self.root = root
    self.spids = spids or []

class whole_file(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('whole_file')
  __slots__ = ('path', 'a', 'spids')

  def __init__(self, path=None, a=None, spids=None):
    self.path = path
    self.a = a
    self.spids = spids or []

class partial_file(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('partial_file')
  __slots__ = ('path', 'funcs', 'spids')

  def __init__(self, path=None, funcs=None, spids=None):
    self.path = path
    self.funcs = funcs or []
    self.spids = spids or []

