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


def BEval(node, ev):
  """Evaluate a boolean expression.

  TODO:
  - A better pattern for failure.  This ok, val stuff is UNREADABLE.  Maybe
    use out params.  Same with val.AsString()
  - Add error context would be good.
  - Also consider stack trace?  For boolean expressions it probably doesn't
    matter.  Although it would be nice to point to the exact token that
    failed.

    [[ 0 -eq foo ]]
             ~~~
    cannot compare integer to string

  if not self.BEval(node.child, ev, ret):
    self.SetError("foo")
    return None
  b, = ret

  ref = []
  if not val.AsString(ref):
    return False
  s, = ret

  This is how expr worked.  It mutated the bool.  I guess that's better in C.

  And we can do that for arithmetic too.
  """
  btype = node.btype
  # TODO: We could look this up at parse time too?  Is that easier or harder?
  try:
    logical, arity, arg_type = BOOL_OPS[btype]
  except KeyError:
    print('NOT FOUND', IdName(btype))
    raise

  if logical:
    if arity == 1:
      ok, b = BEval(node.child, ev)
      if not ok:
        return False, None

      return True, not b  # logical negation
    else:
      assert arity == 2

      ok, b1 = BEval(node.left, ev)
      if not ok:
        return False, None

      # Short-circuit evaluation
      if btype == Id.Op_DAmp:
        if b1:
          ok, b2 = BEval(node.right, ev)
          if not ok:
            return False, None
          return True, b2
        else:
          return True, False

      if btype == Id.Op_DPipe:
        if b1:
          return True, True
        else:
          ok, b2 = BEval(node.right, ev)
          if not ok:
            return False, None

          return True, b2

      raise AssertionError

  else:  # primitive operation
    if arity == 1:
      ok, val = ev.BoolEvalWord(node.word)
      if not ok:
        return False, None

      is_str, s = val.AsString()
      assert is_str

      if arg_type == BArgType.FILE:
        try:
          mode = os.stat(s).st_mode
        except FileNotFoundError as e:
          mode = None

        if btype == Id.BoolUnary_f:
          if mode:
            ret = stat.S_ISREG(mode)
          else:
            ret = False
          return True, ret  # TODO

      if arg_type == BArgType.STRING:
        if btype == Id.BoolUnary_z:
          return True, not bool(s)
        if btype == Id.BoolUnary_n:
          return True, bool(s)
        raise NotImplementedError(btype)

    else:
      assert arity == 2

      ok, val1 = ev.BoolEvalWord(node.left)
      if not ok:
        return False, None

      if btype in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual, Id.BoolBinary_NEqual):
        # quoted parts are escaped for globs.
        ok, val2 = ev.BoolEvalWord(node.right, do_glob=True)
        if not ok:
          return False, None
      else:
        # normal evaluation
        ok, val2 = ev.BoolEvalWord(node.right)
        if not ok:
          return False, None

      #print(val1, val2)
      is_str1, s1 = val1.AsString()
      is_str2, s2 = val2.AsString()

      if arg_type == BArgType.FILE:
        if not is_str1 or not is_str2:
          print("Operator %r requires a string, got %r %r" % (btype, s1, s2))
          return False, None
        st1 = os.stat(s1)
        st2 = os.stat(s2)

        if btype == Id.BoolBinary_nt:
          return True, True  # TODO: newer than

      if arg_type == BArgType.INT:
        if not is_str1 or not is_str2:
          return False, None

        try:
          i1 = int(s1)
          i2 = int(s2)
        except ValueError:
          # TODO: error message
          # Also I think this should turn into exit code 3:
          # - 0 true / 1 false / 3 runtime error
          # - 2 is for PARSE error.
          # And I think you also need a "strict" mode.
          # exec_opts.strict_compare = OFF / ON / WARN
          return False, None

        if btype == Id.BoolBinary_eq:
          return True, i1 == i2
        if btype == Id.BoolBinary_ne:
          return True, i1 != i2

      if arg_type == BArgType.STRING:
        # TODO:
        # - Compare arrays.  (Although bash coerces them to string first)
        if not is_str1 or not is_str2:
          print("Operator %r requires a string, got %r %r" % (btype, s1, s2))
          return False, None

        if btype in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
          #return True, _ValuesAreEqual(val1, val2)
          return True, libc.fnmatch(s2, s1)
        if btype == Id.BoolBinary_NEqual:
          #return True, not _ValuesAreEqual(val1, val2)
          return True, not libc.fnmatch(s2, s1)

        if btype == Id.BoolBinary_EqualTilde:
          match = libc.regex_match(s2, s1)
          # TODO: BASH_REMATCH or REGEX_MATCH
          if match == 1:
            ev.SetRegexMatches('TODO')
            ret = True
          elif match == 0:
            ret = False
          elif match == -1:
            raise AssertionError(
                "Invalid regex %r: should have been caught at compile time" %
                s2)
          else:
            raise AssertionError

          # NOTE: regex matching can't fail if compilation succeeds.
          return True, ret

        if btype == Id.Redir_Less:  # pun
          return True, s1 < s2
        if btype == Id.Redir_Great:  # pun
          return True, s1 > s2

        raise NotImplementedError

      raise AssertionError
