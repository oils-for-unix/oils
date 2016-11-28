#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
bool_eval.py

TODO: Turn it into a BoolEvalutor class
"""

import os

try:
  from core import libc
except ImportError:
  from core import fake_libc as libc
from core.id_kind import BOOL_OPS, BArgType, Id, IdName
from core.value import TValue
from core.arith_eval import ExprEvaluator, ExprEvalError
from core.util import log


# NOTE: Not used now
def _ValuesAreEqual(x, y):
  """Equality is used for [[.

  NOTE: Equality of arrays works!
  """
  if x.type != y.type:
    # TODO: should we throw an INCOMPARABLE error?  Same with -eq on strings.
    return False

  if x.type == TValue.STRING:
    #return x.s == y.s
    # RHS is the PATTERN.  LHS is the value.
    return libc.fnmatch(y.s, x.s)

  raise NotImplementedError


class BoolEvaluator(ExprEvaluator):

  def _EvalCompoundWord(self, word, do_glob=False):
    """
    Args:
      node: Id.Word_Compound
      do_glob: TOOD: rename this
    """
    ok, val = self.word_ev.EvalCompoundWord(word, do_glob=do_glob,
                                            elide_empty=False)
    if not ok:
      raise ExprEvalError(self.word_ev.Error())

    is_str, s = val.AsString()
    if not is_str:
      raise ExprEvaluator("Expected string, got array")

    return s

  def _Eval(self, node):
    if node.id == Id.Word_Compound:
      s = self._EvalCompoundWord(node)
      return bool(s)

    if node.id == Id.Node_UnaryExpr:
      b_id = node.b_id
      if b_id == Id.KW_Bang:
        # child could either be a Word, or it could be a BNode
        b = self._Eval(node.child)
        return not b

      s = self._EvalCompoundWord(node.child)

      # Now dispatch on arg type
      _, _, arg_type = BOOL_OPS[b_id]
      if arg_type == BArgType.FILE:
        try:
          mode = os.stat(s).st_mode
        except FileNotFoundError as e:
          # TODO: Signal extra debug information?
          #self._AddErrorContext("Error from stat(%r): %s" % (s, e))
          return False

        if b_id == Id.BoolUnary_f:
          return stat.S_ISREG(mode)

      if arg_type == BArgType.STRING:
        if b_id == Id.BoolUnary_z:
          return not bool(s)
        if b_id == Id.BoolUnary_n:
          return bool(s)

        raise NotImplementedError(b_id)

      raise NotImplementedError(arg_type)

    if node.id == Id.Node_BinaryExpr:
      b_id = node.b_id

      # Short-circuit evaluation
      if b_id == Id.Op_DAmp:
        if self._Eval(node.left):
          return self._Eval(node.right)
        else:
          return False

      if b_id == Id.Op_DPipe:
        if self._Eval(node.left):
          return True
        else:
          return self._Eval(node.right)

      s1 = self._EvalCompoundWord(node.left)
      # Whehter to glob escape
      do_glob = b_id in (
          Id.BoolBinary_Equal, Id.BoolBinary_DEqual, Id.BoolBinary_NEqual)
      s2 = self._EvalCompoundWord(node.right, do_glob=do_glob)

      # Now dispatch on arg type
      _, _, arg_type = BOOL_OPS[b_id]

      if arg_type == BArgType.FILE:
        st1 = os.stat(s1)
        st2 = os.stat(s2)

        if b_id == Id.BoolBinary_nt:
          return True  # TODO: test newer than (mtime)

      if arg_type == BArgType.INT:
        try:
          i1 = int(s1)
          i2 = int(s2)
        except ValueError as e:
          # NOTE: Bash turns these into zero, but we won't by default.  Could
          # provide a compat option.
          # Also I think this should turn into exit code 3:
          # - 0 true / 1 false / 3 runtime error
          # - 2 is for PARSE error.
          raise ExprEvalError("Invalid integer: %s" % e)

        if b_id == Id.BoolBinary_eq:
          return i1 == i2
        if b_id == Id.BoolBinary_ne:
          return i1 != i2

        raise NotImplementedError(b_id)

      if arg_type == BArgType.STRING:
        # TODO:
        # - Compare arrays.  (Although bash coerces them to string first)

        if b_id in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
          #return True, _ValuesAreEqual(val1, val2)
          return libc.fnmatch(s2, s1)

        if b_id == Id.BoolBinary_NEqual:
          #return True, not _ValuesAreEqual(val1, val2)
          return not libc.fnmatch(s2, s1)

        if b_id == Id.BoolBinary_EqualTilde:
          # NOTE: regex matching can't fail if compilation succeeds.
          match = libc.regex_match(s2, s1)
          # TODO: BASH_REMATCH or REGEX_MATCH
          if match == 1:
            # TODO: Should we have self.mem?
            self.word_ev.SetRegexMatches('TODO')
            is_match = True
          elif match == 0:
            is_match = False
          elif match == -1:
            raise AssertionError(
                "Invalid regex %r: should have been caught at compile time" %
                s2)
          else:
            raise AssertionError

          return is_match

        if b_id == Id.Redir_Less:  # pun
          return s1 < s2

        if b_id == Id.Redir_Great:  # pun
          return s1 > s2

        raise NotImplementedError(b_id)

    # We could have govered all node IDs
    raise AssertionError(IdName(node.id))
