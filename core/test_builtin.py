#!/usr/bin/python
"""
test_builtin.py
"""

import sys

from core import id_kind
from core import expr_eval
from core import word
from core import runtime
from core.util import log, e_die

from osh import bool_parse
from osh import ast_ as ast

Id = id_kind.Id


_ID_LOOKUP = {}  # string -> Id

id_kind.SetupTestBuiltin(_ID_LOOKUP)


class _WordParser:
  """For test/[, we need a word parser that returns StringWord.
  
  The BoolParser calls word.BoolId(w), and deals with Kind.BoolUnary,
  Kind.BoolBinary, etc.  This is instead of CompoundWord/TokenWord (as in the
  [[ case.
  """
  def __init__(self, argv):
    self.argv = argv
    self.i = 0
    self.n = len(argv)

  def ReadWord(self, lex_mode):
    if self.i == self.n:
      # NOTE: Could define something special
      return ast.StringWord(Id.Eof_Real, '')

    #log('ARGV %s i %d', self.argv, self.i)
    s = self.argv[self.i]
    self.i += 1

    id_ = _ID_LOOKUP.get(s, Id.Word_Compound)  # default is an operand word
    return ast.StringWord(id_, s)


class _WordEvaluator:

  def EvalWordToString(self, w, do_fnmatch=False):
    # do_fnmatch: for the [[ == ]] semantics which we don't have!
    # I think I need another type of node
    # Maybe it should be BuiltinEqual and BuiltinDEqual?  Parse it into a different tree.
    return runtime.Str(w.s)


def Test(argv, need_right_bracket):
  """The test/[ builtin.

  The only difference between test and [ is that [ needs a matching ].
  """
  w_parser = _WordParser(argv)
  b_parser = bool_parse.BoolParser(w_parser)
  node = b_parser.ParseForBuiltin(need_right_bracket)
  if node is None:
    for e in b_parser.Error():
      log("error %s", e)
    e_die("Error parsing test/[ expression")

  log('Bool expr %s', node)

  # def __init__(self, mem, exec_opts, word_ev):
  # mem: Don't need it for BASH_REMATCH?  Or I guess you could support it
  # exec_opts: don't need it
  # word_ev: don't need it

  mem = None
  exec_opts = None
  word_ev = _WordEvaluator()

  bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, word_ev)
  # TODO: Catch exceptions and turn into failure.  It can't have a fatal error, like [[ ${foo?error} ]].
  result = bool_ev.Eval(node)
  status = 0 if result else 1
  return status
