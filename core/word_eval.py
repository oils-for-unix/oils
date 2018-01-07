"""
word_eval.py - Evaluator for the word language.
"""

import glob
import re
import sys

from core import braces
from core import expr_eval
from core import legacy
from core import glob_
from core.id_kind import Id, Kind, LookupKind
from core import runtime
from core import state
from core import util
from osh import ast_ as ast

part_value_e = runtime.part_value_e
value_e = runtime.value_e

bracket_op_e = ast.bracket_op_e
suffix_op_e = ast.suffix_op_e
word_part_e = ast.word_part_e
log = util.log
e_die = util.e_die


def _ValueToPartValue(val, quoted):
  """Helper for VarSub evaluation.

  Called by _EvalBracedVarSub and __EvalWordPart for SimpleVarSub.
  """
  assert isinstance(val, runtime.value), val

  if val.tag == value_e.Str:
    return runtime.StringPartValue(val.s, not quoted)

  elif val.tag == value_e.StrArray:
    return runtime.ArrayPartValue(val.strs)

  else:
    # Undef should be caught by _EmptyStrOrError().
    raise AssertionError


def _MakeWordFrames(part_vals):
  """
  A word evaluates to a flat list of word parts (StringPartValue or
  ArrayPartValue).  A frame is a portion that results in zero or more args.  It
  can never be joined.  This idea exists because of arrays like "$@" and
  "${a[@]}".

  Args:
    part_vals: array of part_value.  Either StringPartValue or ArrayPartValue.

  Returns:
    An array of frames.  Each frame is a tuple.

  Example:

    a=(1 '2 3' 4)
    x=x
    y=y
    $x"${a[@]}"$y

    Three frames:
      [ ('x', False), ('1', True) ]
      [ ('2 3', True) ]
      [ ('4', True), ('y', False ]
  """
  current = []
  frames = [current]

  for p in part_vals:
    if p.tag == part_value_e.StringPartValue:
      current.append((p.s, p.do_split_glob))

    elif p.tag == part_value_e.ArrayPartValue:
      for i, s in enumerate(p.strs):
        if i == 0:
          current.append((s, False))  # don't split or glob
        else:
          new = (s, False)
          current = [new]
          frames.append(current)  # singleton frame

    else:
      raise AssertionError(p.__class__.__name__)

  return frames


# TODO: This could be _MakeWordFrames and then sep.join().  It's redunant.
def _DecayPartValuesToString(part_vals, join_char):
  # Decay ${a=x"$@"x} to string.
  out = []
  for p in part_vals:
    if p.tag == part_value_e.StringPartValue:
       out.append(p.s)
    else:
      last = len(p.strs) - 1
      for i, s in enumerate(p.strs):
        out.append(s)
        if i != last:
          out.append(join_char)
  return ''.join(out)


# TODO:
# - Unicode support: Convert both pattern, string, and replacement to unicode,
#   then the result back at the end.
# - Add location info to errors.  Maybe pass spid pair all the way down.
#   - Compile time errors for [[:space:]] ?

def _DoUnarySuffixOp(s, op, arg):
  """Helper for ${x#prefix} and family."""

  pat_re, err = glob_.GlobToPythonRegex(arg)
  if err:
    e_die("Can't convert glob to regex: %r", arg)

  if pat_re is None:  # simple/fast path for fixed strings
    if op.op_id in (Id.VOp1_Pound, Id.VOp1_DPound):  # const prefix
      if s.startswith(arg):
        return s[len(arg):]
      else:
        return s

    elif op.op_id in (Id.VOp1_Percent, Id.VOp1_DPercent):  # const suffix
      if s.endswith(arg):
        # Mutate it so we preserve the flags.
        return s[:-len(arg)]
      else:
        return s

    else:  # e.g. ^ ^^ , ,,
      raise AssertionError(op.op_id)

  else:  # glob pattern
    # Extract the group from the regex and return it
    if op.op_id == Id.VOp1_Pound:  # shortest prefix
      # Need non-greedy match
      pat_re2, err = glob_.GlobToPythonRegex(arg, greedy=False)
      r = re.compile(pat_re2)
      m = r.match(s)
      if m:
        return s[m.end(0):]
      else:
        return s

    elif op.op_id == Id.VOp1_DPound:  # longest prefix
      r = re.compile(pat_re)
      m = r.match(s)
      if m:
        return s[m.end(0):]
      else:
        return s

    elif op.op_id == Id.VOp1_Percent:  # shortest suffix
      # NOTE: This is different than re.search, which will find the longest
      # suffix.
      r = re.compile('^(.*)' + pat_re + '$')
      m = r.match(s)
      if m:
        return m.group(1)
      else:
        return s
      
    elif op.op_id == Id.VOp1_DPercent:  # longest suffix
      r = re.compile('^(.*?)' + pat_re + '$')  # non-greedy
      m = r.match(s)
      if m:
        return m.group(1)
      else:
        return s

    else:
      raise AssertionError(op.op_id)


def _PatSub(s, op, pat, replace_str):
  """Helper for ${x/pat/replace}."""
  #log('PAT %r REPLACE %r', pat, replace_str)
  py_regex, err = glob_.GlobToPythonRegex(pat)
  if err:
    e_die("Can't convert glob to regex: %r", pat)

  if py_regex is None:  # Simple/fast path for fixed strings
    if op.do_all:
      return s.replace(pat, replace_str)
    elif op.do_prefix:
      if s.startswith(pat):
        n = len(pat)
        return replace_str + s[n:]
      else:
        return s
    elif op.do_suffix:
      if s.endswith(pat):
        n = len(pat)
        return s[:-n] + replace_str
      else:
        return s
    else:
      return s.replace(pat, replace_str, 1)  # just the first one

  else:
    count = 1  # replace first occurrence only
    if op.do_all:
      count = 0  # replace all
    elif op.do_prefix:
      py_regex = '^' + py_regex
    elif op.do_suffix:
      py_regex = py_regex + '$'

    pat_re = re.compile(py_regex)
    return pat_re.sub(replace_str, s, count)


# SliceParts is for ${a-} and ${a+}, Error is for ${a?}, and SliceAndAssign is
# for ${a=}.

Effect = util.Enum('Effect', 'SpliceParts Error SpliceAndAssign NoOp'.split())


class _WordEvaluator:
  """Abstract base class for word evaluators.

  Public entry points:
    EvalWordToString
    EvalRhsWord
    EvalWordSequence
  """
  def __init__(self, mem, exec_opts, splitter):
    self.mem = mem  # for $HOME, $1, etc.
    self.exec_opts = exec_opts  # for nounset
    self.splitter = splitter
    self.globber = glob_.Globber(exec_opts)
    # NOTE: Executor also instantiates one.
    self.arith_ev = expr_eval.ArithEvaluator(mem, exec_opts, self)

  def _EvalCommandSub(self, part, quoted):
    """Abstract since it has a side effect.

    Args:
      part: CommandSubPart

    Returns:
       part_value
    """
    raise NotImplementedError

  def _EvalProcessSub(self, part, id_):
    """Abstract since it has a side effect.

    Args:
      part: CommandSubPart

    Returns:
       part_value
    """
    raise NotImplementedError

  def _EvalTildeSub(self, prefix):
    """Evaluates ~ and ~user.

    Args:
      prefix: The tilde prefix (possibly empty)
    """
    if prefix == '':
      # First look up the HOME var, and then env var
      val = self.mem.GetVar('HOME')
      if val.tag == value_e.Str:
        return val.s
      elif val.tag == value_e.StrArray:
        raise AssertionError

      s = util.GetHomeDir()
      if s is None:
        s = '~' + prefix  # No expansion I guess
      return s

    # http://linux.die.net/man/3/getpwnam
    try:
      e = pwd.getpwnam(prefix)
    except KeyError:
      s = '~' + prefix
    else:
      s = e.pw_dir
    return s

  def _EvalVarNum(self, var_num):
    assert var_num >= 0
    return self.mem.GetArgNum(var_num)

  def _EvalSpecialVar(self, op_id, quoted):
    # $@ is special -- it need to know whether it is in a double quoted
    # context.
    #
    # - If it's $@ in a double quoted context, return an ARRAY.
    # - If it's $@ in a normal context, return a STRING, which then will be
    # subject to splitting.

    if op_id in (Id.VSub_At, Id.VSub_Star):
      argv = self.mem.GetArgv()
      val = runtime.StrArray(argv)
      if op_id == Id.VSub_At:
        # "$@" evaluates to an array, $@ should be decayed
        return val, not quoted
      else:  # $@ $* "$*"
        return val, True

    elif op_id == Id.VSub_Hyphen:
      s = self.exec_opts.GetDollarHyphen()
      return runtime.Str(s), False
    else:
      val = self.mem.GetSpecialVar(op_id)
      return val, False  # dont' decay

  def _ApplyTestOp(self, val, op, quoted, part_vals):
    """
    Returns:
      assign_part_vals, Effect

      ${a:-} returns part_value[]
      ${a:+} returns part_value[]
      ${a:?error} returns error word?
      ${a:=} returns part_value[] but also needs self.mem for side effects.

      So I guess it should return part_value[], and then a flag for raising an
      error, and then a flag for assigning it?
      The original BracedVarSub will have the name.

    Example of needing multiple part_value[]

      echo X-${a:-'def'"ault"}-X

    We return two part values from the BracedVarSub.  Also consider:

      echo ${a:-x"$@"x}
    """
    undefined = (val.tag == value_e.Undef)

    # TODO: Change this to a bitwise test?
    if op.op_id in (
        Id.VTest_ColonHyphen, Id.VTest_ColonEquals, Id.VTest_ColonQMark,
        Id.VTest_ColonPlus):
      is_falsey = (
          undefined or
          (val.tag == value_e.Str and not val.s) or
          (val.tag == value_e.StrArray and not val.strs)
      )
    else:
      is_falsey = undefined

    #print('!!',id, is_falsey)
    if op.op_id in (Id.VTest_ColonHyphen, Id.VTest_Hyphen):
      if is_falsey:
        self._EvalWordToParts(op.arg_word, quoted, part_vals)
        return None, Effect.SpliceParts
      else:
        return None, Effect.NoOp

    elif op.op_id in (Id.VTest_ColonPlus, Id.VTest_Plus):
      # Inverse of the above.
      if is_falsey:
        return None, Effect.NoOp
      else:
        self._EvalWordToParts(op.arg_word, quoted, part_vals)
        return None, Effect.SpliceParts

    elif op.op_id in (Id.VTest_ColonEquals, Id.VTest_Equals):
      if is_falsey:
        # Collect new part vals.
        assign_part_vals = []
        self._EvalWordToParts(op.arg_word, quoted, assign_part_vals)

        # Append them to out param and return them.
        part_vals.extend(assign_part_vals)
        return assign_part_vals, Effect.SpliceAndAssign
      else:
        return None, Effect.NoOp

    elif op.op_id in (Id.VTest_ColonQMark, Id.VTest_QMark):
      # TODO: Construct error
      # So the test fails!  Exit code 1 makes it pass.
      sys.exit(33)
      raise NotImplementedError

    # TODO:
    # +  -- inverted test -- assign to default
    # ?  -- error
    # =  -- side effect assignment
    else:
      raise NotImplementedError(id)

  def _ApplyPrefixOp(self, val, op_id):
    """
    Returns:
      value
    """
    assert val.tag != value_e.Undef

    if op_id == Id.VSub_Pound:  # LENGTH
      if val.tag == value_e.Str:
        length = len(val.s)
      elif val.tag == value_e.StrArray:
        # TODO: There can be empty placeholder values in the array.
        length = len(val.strs)
      return runtime.Str(str(length))
    elif op_id == Id.VSub_Bang:
      # NOTES:
      # - Could translate to eval('$' + name) or eval("\$$name")
      # - ${!array[@]} means something completely different.  TODO: implement
      #   that.
      # - It might make sense to suggest implementing this with associative
      #   arrays?

      # Treat the value of the variable as a variable name.
      return self.mem.GetVar(val.s)
    else:
      raise AssertionError(op_id)

  def _ApplyUnarySuffixOp(self, val, op):
    assert val.tag != value_e.Undef

    op_kind = LookupKind(op.op_id)

    if op_kind == Kind.VOp1:
      #log('%s', op)
      arg_val = self.EvalWordToString(op.arg_word, do_fnmatch=True)
      assert arg_val.tag == value_e.Str

      if val.tag == value_e.Str:
        s = _DoUnarySuffixOp(val.s, op, arg_val.s)
        new_val = runtime.Str(s)
      else:  # val.tag == value_e.StrArray:
        # ${a[@]#prefix} is VECTORIZED on arrays.  Oil should have this too.
        strs = []
        for s in val.strs:
          strs.append(_DoUnarySuffixOp(s, op, arg_val.s))
        new_val = runtime.StrArray(strs)

    else:
      raise AssertionError(op_kind)

    return new_val

  def _EvalDoubleQuotedPart(self, part, part_vals):
    """DoubleQuotedPart -> part_value

    Args:
      part_vals: output param to append to.
    """
    # Example of returning array:
    # $ a=(1 2); b=(3); $ c=(4 5)
    # $ argv "${a[@]}${b[@]}${c[@]}"
    # ['1', '234', '5']
    # Example of multiple parts
    # $ argv "${a[@]}${undef[@]:-${c[@]}}"
    # ['1', '24', '5']

    #log('DQ part %s', part)

    # Special case for "".  The parser outputs (DoubleQuotedPart []), instead
    # of (DoubleQuotedPart [LiteralPart '']).  This is better but it means we
    # have to check for it.
    if not part.parts:
      v = runtime.StringPartValue('', False)
      part_vals.append(v)
      return

    for p in part.parts:
      self._EvalWordPart(p, part_vals, quoted=True)

  def _DecayArray(self, val):
    assert val.tag == value_e.StrArray, val
    sep = self.splitter.GetJoinChar()
    return runtime.Str(sep.join(val.strs))

  def _EmptyStrOrError(self, val, token=None):
    assert isinstance(val, runtime.value), val

    if val.tag == value_e.Undef:
      if self.exec_opts.nounset:
        if token is None:
          e_die('Undefined variable')
        else:
          name = token.val[1:] if token.val.startswith('$') else token.val
          e_die('Undefined variable %r', name, token=token)
      else:
        return runtime.Str('')
    else:
      return val

  def _EmptyStrArrayOrError(self, token):
    assert token is not None
    if self.exec_opts.nounset:
      e_die('Undefined array %r', token.val, token=token)
    else:
      return runtime.StrArray([])

  def _EvalBracedVarSub(self, part, part_vals, quoted):
    """
    Args:
      part_vals: output param to append to.
    """
    # We have four types of operator that interact.
    #
    # 1. Bracket: value -> (value, bool decay_array)
    #
    # 2. Then these four cases are mutually exclusive:
    #
    #   a. Prefix length: value -> value
    #   b. Test: value -> part_value[]
    #   c. Other Suffix: value -> value
    #   d. no operator: you have a value
    #
    # That is, we don't have both prefix and suffix operators.
    #
    # 3. Process decay_array here before returning.

    decay_array = False  # for $*, ${a[*]}, etc.

    var_name = None  # For ${foo=default}

    # 1. Evaluate from (var_name, var_num, token Id) -> value
    if part.token.id == Id.VSub_Name:
      var_name = part.token.val
      val = self.mem.GetVar(var_name)
      #log('EVAL NAME %s -> %s', var_name, val)

    elif part.token.id == Id.VSub_Number:
      var_num = int(part.token.val)
      val = self._EvalVarNum(var_num)
    else:
      # $* decays
      val, decay_array = self._EvalSpecialVar(part.token.id, quoted)

    # 2. Bracket: value -> (value v, bool decay_array)
    # decay_array is for joining ${a[*]} and unquoted ${a[@]} AFTER suffix ops
    # are applied.  If we take the length with a prefix op, the distinction is
    # ignored.
    if part.bracket_op:
      if part.bracket_op.tag == bracket_op_e.WholeArray:
        op_id = part.bracket_op.op_id

        if op_id == Id.Lit_At:
          if not quoted:
            decay_array = True  # ${a[@]} decays but "${a[@]}" doesn't
          if val.tag == value_e.Undef:
            val = self._EmptyStrArrayOrError(part.token)
          elif val.tag == value_e.Str:
            e_die("Can't index string with @: %r", val, part=part)
          elif val.tag == value_e.StrArray:
            val = runtime.StrArray(val.strs)

        elif op_id == Id.Arith_Star:
          decay_array = True  # both ${a[*]} and "${a[*]}" decay
          if val.tag == value_e.Undef:
            val = self._EmptyStrArrayOrError(part.token)
          elif val.tag == value_e.Str:
            e_die("Can't index string with *: %r", val, part=part)
          elif val.tag == value_e.StrArray:
            # Always decay_array with ${a[*]} or "${a[*]}"
            val = runtime.StrArray(val.strs)

        else:
          raise AssertionError(op_id)  # unknown

      elif part.bracket_op.tag == bracket_op_e.ArrayIndex:
        anode = part.bracket_op.expr
        index = self.arith_ev.Eval(anode)

        if val.tag == value_e.Undef:
          pass  # it will be checked later
        elif val.tag == value_e.Str:
          # TODO: Implement this as an extension. Requires unicode support.
          # Bash treats it as an array.
          e_die("Can't index string %r with integer", part.token.val)
        elif val.tag == value_e.StrArray:
          try:
            s = val.strs[index]
          except IndexError:
            val = runtime.Undef()
          else:
            val = runtime.Str(s)

      else:
        raise AssertionError(part.bracket_op.tag)

    if part.prefix_op:
      val = self._EmptyStrOrError(val)  # maybe error
      val = self._ApplyPrefixOp(val, part.prefix_op)
      # At least for length, we can't have a test or suffix afterward.

    elif part.suffix_op:
      op = part.suffix_op
      if op.tag == suffix_op_e.StringUnary:
        if LookupKind(part.suffix_op.op_id) == Kind.VTest:
          # TODO: Change style to:
          # if self._ApplyTestOp(...)
          #   return
          # It should return whether anything was done.  If not, we continue to
          # the end, where we might throw an error.

          assign_part_vals, effect = self._ApplyTestOp(val, part.suffix_op,
                                                       quoted, part_vals)

          # NOTE: Splicing part_values is necessary because of code like
          # ${undef:-'a b' c 'd # e'}.  Each part_value can have a different
          # do_glob/do_elide setting.
          if effect == Effect.SpliceParts:
            return  # EARLY RETURN, part_vals mutated

          elif effect == Effect.SpliceAndAssign:
            if var_name is None:
              # TODO: error context
              e_die("Can't assign to special variable")
            else:
              # NOTE: This decays arrays too!  'set -o strict_array' could
              # avoid it.
              rhs_str = _DecayPartValuesToString(assign_part_vals,
                                                 self.splitter.GetJoinChar())
              state.SetLocalString(self.mem, var_name, rhs_str)
            return  # EARLY RETURN, part_vals mutated

          elif effect == Effect.Error:
            raise NotImplementedError

          else:
            # The old one
            #val = self._EmptyStringPartOrError(part_val, quoted)
            pass  # do nothing, may still be undefined

        else:
          val = self._EmptyStrOrError(val)  # maybe error
          # Other suffix: value -> value
          val = self._ApplyUnarySuffixOp(val, part.suffix_op)

      elif op.tag == suffix_op_e.PatSub:  # PatSub, vectorized
        val = self._EmptyStrOrError(val)

        pat_val = self.EvalWordToString(op.pat, do_fnmatch=True)
        assert pat_val.tag == value_e.Str, pat_val

        if op.replace:
          replace_val = self.EvalWordToString(op.replace, do_fnmatch=True)
          assert replace_val.tag == value_e.Str, replace_val
          replace_str = replace_val.s
        else:
          replace_str = ''

        pat = pat_val.s
        if val.tag == value_e.Str:
          s = _PatSub(val.s, op, pat, replace_str)
          val = runtime.Str(s)

        elif val.tag == value_e.StrArray:
          strs = []
          for s in val.strs:
            strs.append(_PatSub(s, op, pat, replace_str))
          val = runtime.StrArray(strs)

        else:
          raise AssertionError(val.__class__.__name__)

      elif op.tag == suffix_op_e.Slice:
        # NOTE: The beginning can be negative, but Python handles this.  Might
        # want to make it explicit.
        # TODO: Check out of bounds errors?  begin > end?
        if op.begin:
          begin = self.arith_ev.Eval(op.begin)
        else:
          begin = 0

        if op.length:
          length = self.arith_ev.Eval(op.length)
          end = begin + length
        else:
          end = None  # Python supports None as the end

        if val.tag == value_e.Str:  # Slice characters in a string.
          # TODO: Need to support unicode?  Write spec # tests.
          val = runtime.Str(val.s[begin : end])

        elif val.tag == value_e.StrArray:  # Slice array entries.
          val = runtime.StrArray(val.strs[begin : end])

        else:
          raise AssertionError(val.__class__.__name__)

    # After applying suffixes, process decay_array here.
    if decay_array:
      val = self._DecayArray(val)

    # No prefix or suffix ops
    val = self._EmptyStrOrError(val)

    # For example, ${a} evaluates to value_t.Str(), but we want a
    # part_value.StringPartValue.
    part_val = _ValueToPartValue(val, quoted)
    part_vals.append(part_val)

  def _EvalWordPart(self, part, part_vals, quoted=False):
    """Evaluate a word part.

    Args:
      part_vals: Output parameter.

    Returns:
      None
    """
    if part.tag == word_part_e.ArrayLiteralPart:
      raise AssertionError(
          'Array literal should have been handled at word level')

    elif part.tag == word_part_e.LiteralPart:
      v = runtime.StringPartValue(part.token.val, not quoted)
      part_vals.append(v)

    elif part.tag == word_part_e.EscapedLiteralPart:
      val = part.token.val
      assert len(val) == 2, val  # e.g. \*
      assert val[0] == '\\'
      s = val[1]
      v = runtime.StringPartValue(s, False)
      part_vals.append(v)

    elif part.tag == word_part_e.SingleQuotedPart:
      s = ''.join(t.val for t in part.tokens)
      v = runtime.StringPartValue(s, False)
      part_vals.append(v)

    elif part.tag == word_part_e.DoubleQuotedPart:
      self._EvalDoubleQuotedPart(part, part_vals)

    elif part.tag == word_part_e.CommandSubPart:
      id_ = part.left_token.id
      if id_ in (Id.Left_CommandSub, Id.Left_Backtick):
        v = self._EvalCommandSub(part.command_list, quoted)

      elif id_ in (Id.Left_ProcSubIn, Id.Left_ProcSubOut):
        v = self._EvalProcessSub(part.command_list, id_)

      else:
        raise AssertionError(id_)

      part_vals.append(v)

    elif part.tag == word_part_e.SimpleVarSub:
      decay_array = False
      # 1. Evaluate from (var_name, var_num, token) -> defined, value
      if part.token.id == Id.VSub_Name:
        var_name = part.token.val[1:]
        val = self.mem.GetVar(var_name)
      elif part.token.id == Id.VSub_Number:
        var_num = int(part.token.val[1:])
        val = self._EvalVarNum(var_num)
      else:
        val, decay_array = self._EvalSpecialVar(part.token.id, quoted)

      #log('SIMPLE %s', part)
      val = self._EmptyStrOrError(val, token=part.token)
      if decay_array:
        val = self._DecayArray(val)
      v = _ValueToPartValue(val, quoted)
      part_vals.append(v)

    elif part.tag == word_part_e.BracedVarSub:
      self._EvalBracedVarSub(part, part_vals, quoted)

    elif part.tag == word_part_e.TildeSubPart:
      # We never parse a quoted string into a TildeSubPart.
      assert not quoted
      s = self._EvalTildeSub(part.prefix)
      v = runtime.StringPartValue(s, False)
      part_vals.append(v)

    elif part.tag == word_part_e.ArithSubPart:
      num = self.arith_ev.Eval(part.anode)
      v = runtime.StringPartValue(str(num), False)
      part_vals.append(v)

    else:
      raise AssertionError(part.__class__.__name__)

  def _EvalWordToParts(self, word, quoted, part_vals):
    """Helper for EvalRhsWord, EvalWordSequence, etc.

    Returns:
      List of part_value.
      But note that this is a TREE.
    """
    assert isinstance(word, ast.CompoundWord), \
        "Expected CompoundWord, got %s" % word

    for p in word.parts:
      v = self._EvalWordPart(p, part_vals, quoted=quoted)

  def EvalWordToString(self, word, do_fnmatch=False, decay=False):
    """
    Used for redirect arg, ControlFlow arg, ArithWord, BoolWord, etc.

    do_fnmatch is true for case $pat and RHS of [[ == ]].

    pat="*.py"
    case $x in
      $pat) echo 'matches glob pattern' ;;
      "$pat") echo 'equal to glob string' ;;  // must be glob escaped
    esac
    """
    part_vals = []
    for part in word.parts:
      self._EvalWordPart(part, part_vals, quoted=False)

    strs = []
    for part_val in part_vals:
      # TODO: if decay, then allow string part.  e.g. for here word or here
      # doc with "$@".

      if part_val.tag != part_value_e.StringPartValue:
        # Example: echo f > "$@".  TODO: Add proper context.  
        e_die("Expected string, got %s", part_val)

        # TODO: Maybe add detail like this.
        #e_die('RHS of assignment should only have strings.  '
        #      'To assign arrays, using b=( "${a[@]}" )')

      # [[ foo == */"*".py ]] or case *.py) ... esac
      if do_fnmatch and not part_val.do_split_glob:
        s = glob_.GlobEscape(part_val.s)
      else:
        s = part_val.s
      strs.append(s)

    return runtime.Str(''.join(strs))

  def EvalRhsWord(self, word):
    """word_t -> value_t.

    Used for RHS of assignment.  There is no splitting.

    Args:
      word.CompoundWord

    Returns:
      value
    """
    # Special case for a=(1 2).  ArrayLiteralPart won't appear in words that
    # don't look like assignments.
    if (len(word.parts) == 1 and
        word.parts[0].tag == word_part_e.ArrayLiteralPart):

      array_words = word.parts[0].words
      words = braces.BraceExpandWords(array_words)
      strs = self._EvalWordSequence(words)
      #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
      return runtime.StrArray(strs)

    # If RHS doens't look like a=( ... ), then it must be a string.
    return self.EvalWordToString(word)

  def _EvalWordFrame(self, frame, argv):
    all_empty = True
    all_split_glob = True
    any_split_glob = False

    for s, do_split_glob in frame:
      #log('-- %r %r', s, do_split_glob)
      if s:
        all_empty = False

      if do_split_glob:
        any_split_glob = True
      else:
        all_split_glob = False

    # Elision of ${empty}${empty} but not $empty"$empty" or $empty""
    if all_empty and all_split_glob:
      return

    # If every frag is quoted, e.g. "$a$b" or any part in "${a[@]}"x, then
    # don't do word splitting or globbing.
    if not any_split_glob:
      a = ''.join(s for s, _ in frame)
      argv.append(a)
      return

    will_glob = not self.exec_opts.noglob

    # Array of strings, some of which are BOTH IFS-escaped and GLOB escaped!
    frags = []
    for frag, do_split_glob in frame:
      #log('do_split_glob %s', do_split_glob)
      if will_glob and not do_split_glob:
        frag = glob_.GlobEscape(frag)
        #log('GLOB ESCAPED %r', p2)

      if not do_split_glob:
        frag = self.splitter.Escape(frag)
        #log('IFS ESCAPED %r', p2)

      frags.append(frag)

    flat = ''.join(frags)
    #log('flat: %r', flat)

    args = self.splitter.SplitForWordEval(flat)

    # space=' '; argv $space"".  We have a quoted part, but we CANNOT elide.
    # Add it back and don't bother globbing.
    if not args and not all_split_glob:
      argv.append('')
      return

    #log('split args: %r', args)
    #out = []
    for a in args:
      results = self.globber.Expand(a)
      #out.extend(results)
      argv.extend(results)

  def _EvalWordSequence(self, words):
    """Turns a list of Words into a list of strings.

    Unlike the EvalWord*() methods, it does globbing.

    Args:
      words: list of Word instances

    Returns:
      argv: list of string arguments, or None if there was an eval error
    """
    # Parse time:
    # 1. brace expansion.  TODO: Do at parse time.
    # 2. Tilde detection.  DONE at parse time.  Only if Id.Lit_Tilde is the
    # first WordPart.
    #
    # Run time:
    # 3. tilde sub, var sub, command sub, arith sub.  These are all
    # "concurrent" on WordParts.  (optional process sub with <() )
    # 4. word splitting.  Can turn this off with a shell option?  Definitely
    # off for oil.
    # 5. globbing -- several exec_opts affect this: nullglob, safeglob, etc.

    #log('W %s', words)
    argv = []
    for w in words:
      part_vals = []
      self._EvalWordToParts(w, False, part_vals)  # not double quoted

      if 0:
        log('')
        log('part_vals after _EvalWordToParts:')
        for entry in part_vals:
          log('  %s', entry)

      frames = _MakeWordFrames(part_vals)
      if 0:
        log('')
        log('frames after _MakeWordFrames:')
        for entry in frames:
          log('  %s', entry)

      # Now each frame will append zero or more args.
      for frame in frames:
        self._EvalWordFrame(frame, argv)

    #log('ARGV %s', argv)
    return argv

  def EvalWordSequence(self, words):
    """
    Used in: SimpleCommand, ForEach.
    """
    # TODO: Remove this stub
    return self._EvalWordSequence(words)


class NormalWordEvaluator(_WordEvaluator):

  def __init__(self, mem, exec_opts, splitter, ex):
    _WordEvaluator.__init__(self, mem, exec_opts, splitter)
    self.ex = ex

  def _EvalCommandSub(self, node, quoted):
    stdout = self.ex.RunCommandSub(node)
    return runtime.StringPartValue(stdout, not quoted)

  def _EvalProcessSub(self, node, id_):
    dev_path = self.ex.RunProcessSub(node, id_)
    return runtime.StringPartValue(dev_path, False)  # no split or glob


class CompletionWordEvaluator(_WordEvaluator):
  """
  Difference from NormalWordEvaluator: No access to executor!  But they both
  have a splitter.
  """
  def __init__(self, mem, exec_opts, splitter):
    _WordEvaluator.__init__(self, mem, exec_opts, splitter)

  def _EvalCommandSub(self, node, quoted):
    return runtime.StringPartValue('__COMMAND_SUB_NOT_EXECUTED__', not quoted)

  def _EvalProcessSub(self, node, id_):
    return runtime.StringPartValue('__PROCESS_SUB_NOT_EXECUTED__', False)
