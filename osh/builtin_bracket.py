"""
builtin_bracket.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import value
from _devbuild.gen.syntax_asdl import word, bool_expr
from _devbuild.gen.types_asdl import lex_mode_e

from asdl import const
from core import util
from core.util import p_die
from core import meta
from core.meta import IdInstance

from osh import expr_eval
from osh import bool_parse


_UNARY_LOOKUP = meta.TEST_UNARY_LOOKUP
_BINARY_LOOKUP = meta.TEST_BINARY_LOOKUP
_OTHER_LOOKUP = meta.TEST_OTHER_LOOKUP


class _StringWordEmitter(object):
  """For test/[, we need a word parser that returns StringWord.

  The BoolParser calls word.BoolId(w), and deals with Kind.BoolUnary,
  Kind.BoolBinary, etc.  This is instead of CompoundWord/TokenWord (as in the
  [[ case.
  """
  def __init__(self, arg_vec):
    self.arg_vec = arg_vec
    self.i = 0
    self.n = len(arg_vec.strs)

  def ReadWord(self, unused_lex_mode):
    """Interface for bool_parse.py."""
    if self.i == self.n:
      # Does it make sense to define Eof_Argv or something?
      w = word.StringWord(Id.Eof_Real, '')
      # TODO: Add a way to show this.  Show 1 char past the right-most spid of
      # the last word?  But we only have the left-most spid.
      w.spids.append(const.NO_INTEGER)
      return w

    #log('ARGV %s i %d', self.argv, self.i)
    s = self.arg_vec.strs[self.i]
    left_spid = self.arg_vec.spids[self.i]
    self.i += 1

    # default is an operand word
    id_int = (
        _UNARY_LOOKUP.get(s) or _BINARY_LOOKUP.get(s) or _OTHER_LOOKUP.get(s))

    id_ = Id.Word_Compound if id_int is None else IdInstance(id_int)

    # NOTE: We only have the left spid now.  It might be useful to add the
    # right one.
    w = word.StringWord(id_, s)
    w.spids.append(left_spid)
    return w

  def Read(self):
    """Interface used for special cases below."""
    return self.ReadWord(lex_mode_e.ShCommand)

  def Peek(self, offset):
    """For special cases."""
    return self.arg_vec.strs[self.i + offset]

  def Rewind(self, offset):
    """For special cases."""
    self.i -= offset


class _WordEvaluator(object):

  def EvalWordToString(self, w, do_fnmatch=False, do_ere=False):
    # do_fnmatch: for the [[ == ]] semantics which we don't have!
    # I think I need another type of node
    # Maybe it should be BuiltinEqual and BuiltinDEqual?  Parse it into a
    # different tree.
    return value.Str(w.s)


def _TwoArgs(w_parser):
  """Returns an expression tree to be evaluated."""
  w0 = w_parser.Read()
  w1 = w_parser.Read()
  if w0.s == '!':
    return bool_expr.LogicalNot(bool_expr.WordTest(w1))
  unary_id = _UNARY_LOOKUP.get(w0.s)
  if unary_id is None:
    # TODO:
    # - separate lookup by unary
    p_die('Expected unary operator, got %r (2 args)', w0.s, word=w0)
  return bool_expr.BoolUnary(IdInstance(unary_id), w1)


def _ThreeArgs(w_parser):
  """Returns an expression tree to be evaluated."""
  w0 = w_parser.Read()
  w1 = w_parser.Read()
  w2 = w_parser.Read()

  # NOTE: Order is important here.

  binary_id = _BINARY_LOOKUP.get(w1.s)
  if binary_id is not None:
    return bool_expr.BoolBinary(IdInstance(binary_id), w0, w2)

  if w1.s == '-a':
    return bool_expr.LogicalAnd(bool_expr.WordTest(w0), bool_expr.WordTest(w2))

  if w1.s == '-o':
    return bool_expr.LogicalOr(bool_expr.WordTest(w0), bool_expr.WordTest(w2))

  if w0.s == '!':
    w_parser.Rewind(2)
    child = _TwoArgs(w_parser)
    return bool_expr.LogicalNot(child)

  if w0.s == '(' and w2.s == ')':
    return bool_expr.WordTest(w1)

  p_die('Expected binary operator, got %r (3 args)', w1.s, word=w1)


class Test(object):
  def __init__(self, need_right_bracket, errfmt):
    self.need_right_bracket = need_right_bracket
    self.errfmt = errfmt

  def __call__(self, arg_vec):
    """The test/[ builtin.

    The only difference between test and [ is that [ needs a matching ].
    """
    if self.need_right_bracket:  # Preprocess right bracket
      strs = arg_vec.strs
      if not strs or strs[-1] != ']':
        self.errfmt.Print('missing closing ]', span_id=arg_vec.spids[0])
        return 2
      # Remove the right bracket
      arg_vec.strs.pop()
      arg_vec.spids.pop()

    w_parser = _StringWordEmitter(arg_vec)
    w_parser.Read()  # dummy: advance past argv[0]
    b_parser = bool_parse.BoolParser(w_parser)

    # There is a fundamental ambiguity due to poor language design, in cases like:
    # [ -z ]
    # [ -z -a ]
    # [ -z -a ] ]
    #
    # See posixtest() in bash's test.c:
    # "This is an implementation of a Posix.2 proposal by David Korn."
    # It dispatches on expressions of length 0, 1, 2, 3, 4, and N args.  We do
    # the same here.
    #
    # Another ambiguity:
    # -a is both a unary prefix operator and an infix operator.  How to fix this
    # ambiguity?

    bool_node = None
    n = len(arg_vec.strs) - 1
    try:
      if n == 0:
        return 1  # [ ] is False
      elif n == 1:
        w = w_parser.Read()
        bool_node = bool_expr.WordTest(w)
      elif n == 2:
        bool_node = _TwoArgs(w_parser)
      elif n == 3:
        bool_node = _ThreeArgs(w_parser)
      if n == 4:
        a0 = w_parser.Peek(0)
        if a0 == '!':
          w_parser.Read()  # skip !
          child = _ThreeArgs(w_parser)
          bool_node = bool_expr.LogicalNot(child)
        elif a0 == '(' and w_parser.Peek(3) == ')':
          w_parser.Read()  # skip ')'
          bool_node = _TwoArgs(w_parser)
        else:
          pass  # fallthrough

      if bool_node is None:
        bool_node = b_parser.ParseForBuiltin()

    except util.ParseError as e:
      self.errfmt.PrettyPrintError(e, prefix='(test) ')
      return 2

    # mem: Don't need it for BASH_REMATCH?  Or I guess you could support it
    mem = None  # Not necessary
    word_ev = _WordEvaluator()
    arena = None

    # We want [ a -eq a ] to always be an error, unlike [[ a -eq a ]].  This is a
    # weird case of [[ being less strict.
    class _DummyExecOpts():
      def __init__(self):
        self.strict_arith = True
    exec_opts = _DummyExecOpts()

    bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, word_ev, arena)
    try:
      b = bool_ev.Eval(bool_node)
    except util.FatalRuntimeError as e:
      self.errfmt.PrettyPrintError(e, prefix='(test) ')
      return 2  # 1 means 'false', and this usage error is like a parse error.

    status = 0 if b else 1
    return status
