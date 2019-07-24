"""
word_eval.py - Evaluator for the word language.
"""

import pwd

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import (
    word_e, word__CompoundWord,
    bracket_op_e, suffix_op_e, word_part_e
)
from _devbuild.gen.syntax_asdl import word as osh_word
from _devbuild.gen.runtime_asdl import (
    builtin_e,
    part_value, part_value_e, part_value__String,
    value, value_e, value_t,
    lvalue,
    effect_e, arg_vector,
    assign_arg, cmd_value, cmd_value__Assign,
)
from core import process
from core.meta import LookupKind
from core import util
from core.util import log, e_die
from frontend import match
from osh import braces
from osh import builtin
from osh import glob_
from osh import string_ops
from osh import state
from osh import word
from osh import word_compile

import posix_ as posix

from typing import List


# NOTE: Could be done with util.BackslashEscape like glob_.GlobEscape().
def _BackslashEscape(s):
  """Double up backslashes.

  Useful for strings about to be globbed and strings about to be IFS escaped.
  """
  return s.replace('\\', '\\\\')


def _ValueToPartValue(val, quoted):
  """Helper for VarSub evaluation.

  Called by _EvalBracedVarSub and _EvalWordPart for SimpleVarSub.
  """
  assert isinstance(val, value_t), val

  if val.tag == value_e.Str:
    return part_value.String(val.s, quoted, not quoted)

  elif val.tag == value_e.StrArray:
    return part_value.Array(val.strs)

  elif val.tag == value_e.AssocArray:
    # TODO: Is this correct?
    return part_value.Array(val.d.values())

  elif val.tag == value_e.Obj:
    return part_value.String(repr(val.obj), quoted, not quoted)

  else:
    # Undef should be caught by _EmptyStrOrError().
    raise AssertionError(val.__class__.__name__)


def _MakeWordFrames(part_vals):
  """
  A word evaluates to a flat list of part_value (String or Array).  frame is a
  portion that results in zero or more args.  It can never be joined.  This
  idea exists because of arrays like "$@" and "${a[@]}".

  Args:
    part_vals: array of part_value.

  Returns:
    List[Tuple[str, quoted, do_split]].  Each Tuple is called a "frame".

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
    if p.tag == part_value_e.String:
      current.append((p.s, p.quoted, p.do_split))

    elif p.tag == part_value_e.Array:
      for i, s in enumerate(s for s in p.strs if s is not None):
        # Arrays parts are always quoted; otherwise they would have decayed to
        # a string.
        new = (s, True, False)
        if i == 0:
          current.append(new)
        else:
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
    if p.tag == part_value_e.String:
       out.append(p.s)
    else:
      out.append(join_char.join(s for s in p.strs if s is not None))
  return ''.join(out)


def _PerformSlice(val, begin, length, part):
  if val.tag == value_e.Str:  # Slice UTF-8 characters in a string.
    s = val.s

    if begin < 0:
      # It could be negative if we compute unicode length, but that's
      # confusing.

      # TODO: Instead of attributing it to the word part, it would be
      # better if we attributed it to arith_expr begin.
      raise util.InvalidSlice(
          "The start index of a string slice can't be negative: %d",
          begin, part=part)

    byte_begin = string_ops.AdvanceUtf8Chars(s, begin, 0)

    if length is None:
      byte_end = len(s)
    else:
      if length < 0:
        # TODO: Instead of attributing it to the word part, it would be
        # better if we attributed it to arith_expr begin.
        raise util.InvalidSlice(
            "The length of a string slice can't be negative: %d",
            length, part=part)

      byte_end = string_ops.AdvanceUtf8Chars(s, length, byte_begin)

    substr = s[byte_begin : byte_end]
    val = value.Str(substr)

  elif val.tag == value_e.StrArray:  # Slice array entries.
    # NOTE: This error is ALWAYS fatal in bash.  It's inconsistent with
    # strings.
    if length and length < 0:
      e_die("The length index of a array slice can't be negative: %d",
            length, part=part)

    # NOTE: unset elements don't count towards the length.
    strs = []
    for s in val.strs[begin:]:
      if s is not None:
        strs.append(s)
        if len(strs) == length:  # never true for unspecified length
          break
    val = value.StrArray(strs)

  elif val.tag == value_e.AssocArray:
    e_die("Can't slice associative arrays", part=part)

  else:
    raise NotImplementedError(val.__class__.__name__)

  return val


class _WordEvaluator(object):
  """Abstract base class for word evaluators.

  Public entry points:
    EvalWordToString
    EvalForPlugin
    EvalRhsWord
    EvalWordSequence
    EvalWordSequence2
  """
  def __init__(self, mem, exec_opts, exec_deps, arena):
    self.mem = mem  # for $HOME, $1, etc.
    self.exec_opts = exec_opts  # for nounset
    self.splitter = exec_deps.splitter
    self.prompt_ev = exec_deps.prompt_ev
    self.arith_ev = exec_deps.arith_ev
    self.errfmt = exec_deps.errfmt

    self.globber = glob_.Globber(exec_opts)
    # TODO: Consolidate into exec_deps.  Executor also instantiates one.

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

  def _EvalTildeSub(self, token):
    """Evaluates ~ and ~user.

    Args:
      prefix: The tilde prefix (possibly empty)
    """
    if token.val == '~':
      # First look up the HOME var, then ask the OS.  This is what bash does.
      val = self.mem.GetVar('HOME')
      if val.tag == value_e.Str:
        return val.s
      return process.GetHomeDir()

    # For ~otheruser/src.  TODO: Should this be cached?
    # http://linux.die.net/man/3/getpwnam
    name = token.val[1:]
    try:
      e = pwd.getpwnam(name)
    except KeyError:
      # If not found, it's ~nonexistente.  TODO: In strict mode, this should be
      # an error, kind of like failglob and nounset.  Perhaps strict-tilde or
      # even strict-word-eval.
      result = token.val
    else:
      result = e.pw_dir

    return result

  def _EvalVarNum(self, var_num):
    assert var_num >= 0
    return self.mem.GetArgNum(var_num)

  def _EvalSpecialVar(self, op_id, quoted):
    """Returns (val, bool maybe_decay_array).

    TODO: Should that boolean be part of the value?
    """
    # $@ is special -- it need to know whether it is in a double quoted
    # context.
    #
    # - If it's $@ in a double quoted context, return an ARRAY.
    # - If it's $@ in a normal context, return a STRING, which then will be
    # subject to splitting.

    if op_id in (Id.VSub_At, Id.VSub_Star):
      argv = self.mem.GetArgv()
      val = value.StrArray(argv)
      if op_id == Id.VSub_At:
        # "$@" evaluates to an array, $@ should be decayed
        return val, not quoted
      else:  # $@ $* "$*"
        return val, True

    elif op_id == Id.VSub_Hyphen:
      s = self.exec_opts.GetDollarHyphen()
      return value.Str(s), False
    else:
      val = self.mem.GetSpecialVar(op_id)
      return val, False  # don't decay

  def _ApplyTestOp(self, val, op, quoted, part_vals):
    """
    Returns:
      effect_part_vals, effect_e

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
        self._EvalWordToParts(op.arg_word, quoted, part_vals, is_subst=True)
        return None, effect_e.SpliceParts
      else:
        return None, effect_e.NoOp

    elif op.op_id in (Id.VTest_ColonPlus, Id.VTest_Plus):
      # Inverse of the above.
      if is_falsey:
        return None, effect_e.NoOp
      else:
        self._EvalWordToParts(op.arg_word, quoted, part_vals, is_subst=True)
        return None, effect_e.SpliceParts

    elif op.op_id in (Id.VTest_ColonEquals, Id.VTest_Equals):
      if is_falsey:
        # Collect new part vals.
        assign_part_vals = []
        self._EvalWordToParts(op.arg_word, quoted, assign_part_vals,
                              is_subst=True)

        # Append them to out param AND return them.
        part_vals.extend(assign_part_vals)
        return assign_part_vals, effect_e.SpliceAndAssign
      else:
        return None, effect_e.NoOp

    elif op.op_id in (Id.VTest_ColonQMark, Id.VTest_QMark):
      if is_falsey:
        # The arg is the error mesage
        error_part_vals = []
        self._EvalWordToParts(op.arg_word, quoted, error_part_vals,
                              is_subst=True)
        return error_part_vals, effect_e.Error
      else:
        return None, effect_e.NoOp

    else:
      raise NotImplementedError(id)

  def _EvalIndirectArrayExpansion(self, name, index):
    """Expands ${!ref} when $ref has the form `name[index]`.

    Args:
      name, index: arbitrary strings
    Returns:
      value, or None if invalid
    """
    if not match.IsValidVarName(name):
      return None
    val = self.mem.GetVar(name)
    if val.tag == value_e.StrArray:
      if index in ('@', '*'):
        # TODO: maybe_decay_array
        return value.StrArray(val.strs)
      try:
        index_num = int(index)
      except ValueError:
        return None
      try:
        return value.Str(val.strs[index_num])
      except IndexError:
        return value.Undef()
    elif val.tag == value_e.AssocArray:
      if index in ('@', '*'):
        raise NotImplementedError
      try:
        return value.Str(val.d[index])
      except KeyError:
        return value.Undef()
    elif val.tag == value_e.Undef:
      return value.Undef()
    elif val.tag == value_e.Str:
      return None
    else:
      raise AssertionError

  def _ApplyPrefixOp(self, val, op_id, token):
    """
    Returns:
      value
    """
    assert val.tag != value_e.Undef

    if op_id == Id.VSub_Pound:  # LENGTH
      if val.tag == value_e.Str:
        # NOTE: Whether bash counts bytes or chars is affected by LANG
        # environment variables.
        # Should we respect that, or another way to select?  set -o
        # count-bytes?

        # https://stackoverflow.com/questions/17368067/length-of-string-in-bash
        try:
          length = string_ops.CountUtf8Chars(val.s)
        except util.InvalidUtf8 as e:
          # TODO: Add location info from 'part'?  Only the caller has it.
          if self.exec_opts.strict_word_eval:
            raise
          else:
            # NOTE: Doesn't make the command exit with 1; it just returns a
            # length of -1.
            self.errfmt.PrettyPrintError(e, prefix='warning: ')
            return value.Str('-1')

      elif val.tag == value_e.StrArray:
        # There can be empty placeholder values in the array.
        length = sum(1 for s in val.strs if s is not None)

      elif val.tag == value_e.AssocArray:
        length = len(val.d)

      else:
        raise AssertionError(val.__class__.__name__)

      return value.Str(str(length))

    elif op_id == Id.VSub_Bang:  # ${!foo}, "indirect expansion"
      # NOTES:
      # - Could translate to eval('$' + name) or eval("\$$name")
      # - ${!array[@]} means something completely different.  TODO: implement
      #   that.
      # - It might make sense to suggest implementing this with associative
      #   arrays?

      if val.tag == value_e.Str:
        # plain variable name, like 'foo'
        if match.IsValidVarName(val.s):
          return self.mem.GetVar(val.s)

        # positional argument, like '1'
        try:
          return self.mem.GetArgNum(int(val.s))
        except ValueError:
          pass

        if val.s in ('@', '*'):
          # TODO maybe_decay_array
          return value.StrArray(self.mem.GetArgv())

        # otherwise an array reference, like 'arr[0]' or 'arr[xyz]' or 'arr[@]'
        i = val.s.find('[')
        if i >= 0 and val.s[-1] == ']':
          name, index = val.s[:i], val.s[i+1:-1]
          result = self._EvalIndirectArrayExpansion(name, index)
          if result is not None:
            return result

        # Note that bash doesn't consider this fatal.  It makes the
        # command exit with '1', but we don't have that ability yet?
        e_die('Bad indirect expansion: %r', val.s, token=token)

      elif val.tag == value_e.StrArray:
        indices = [str(i) for i, s in enumerate(val.strs) if s is not None]
        return value.StrArray(indices)

      elif val.tag == value_e.AssocArray:
        indices = [str(k) for k in val.d]
        return value.StrArray(indices)

    else:
      raise AssertionError(op_id)

  def _ApplyUnarySuffixOp(self, val, op):
    assert val.tag != value_e.Undef

    op_kind = LookupKind(op.op_id)

    if op_kind == Kind.VOp1:
      # NOTE: glob syntax is supported in ^ ^^ , ,, !  As well as % %% # ##.
      arg_val = self.EvalWordToString(op.arg_word, do_fnmatch=True)
      assert arg_val.tag == value_e.Str

      if val.tag == value_e.Str:
        s = string_ops.DoUnarySuffixOp(val.s, op, arg_val.s)
        #log('%r %r -> %r', val.s, arg_val.s, s)
        new_val = value.Str(s)

      elif val.tag == value_e.StrArray:
        # ${a[@]#prefix} is VECTORIZED on arrays.  Oil should have this too.
        strs = []
        for s in val.strs:
          if s is not None:
            strs.append(string_ops.DoUnarySuffixOp(s, op, arg_val.s))
        new_val = value.StrArray(strs)

      elif val.tag == value_e.AssocArray:
        strs = []
        for s in val.d.itervalues():
          strs.append(string_ops.DoUnarySuffixOp(s, op, arg_val.s))
        new_val = value.StrArray(strs)

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
      v = part_value.String('', True, False)
      part_vals.append(v)
      return

    for p in part.parts:
      self._EvalWordPart(p, part_vals, quoted=True)

  def _DecayArray(self, val):
    assert val.tag == value_e.StrArray, val
    sep = self.splitter.GetJoinChar()
    return value.Str(sep.join(s for s in val.strs if s is not None))

  def _EmptyStrOrError(self, val, token=None):
    assert isinstance(val, value_t), val

    if val.tag == value_e.Undef:
      if self.exec_opts.nounset:
        if token is None:
          e_die('Undefined variable')
        else:
          name = token.val[1:] if token.val.startswith('$') else token.val
          e_die('Undefined variable %r', name, token=token)
      else:
        return value.Str('')
    else:
      return val

  def _EmptyStrArrayOrError(self, token):
    assert token is not None
    if self.exec_opts.nounset:
      e_die('Undefined array %r', token.val, token=token)
    else:
      return value.StrArray([])

  def _EvalBracedVarSub(self, part, part_vals, quoted):
    """
    Args:
      part_vals: output param to append to.
    """
    # We have four types of operator that interact.
    #
    # 1. Bracket: value -> (value, bool maybe_decay_array)
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
    # 3. Process maybe_decay_array here before returning.

    maybe_decay_array = False  # for $*, ${a[*]}, etc.

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
      val, maybe_decay_array = self._EvalSpecialVar(part.token.id, quoted)

    # 2. Bracket: value -> (value v, bool maybe_decay_array)
    # maybe_decay_array is for joining ${a[*]} and unquoted ${a[@]} AFTER
    # suffix ops are applied.  If we take the length with a prefix op, the
    # distinction is ignored.
    if part.bracket_op:
      if part.bracket_op.tag == bracket_op_e.WholeArray:
        op_id = part.bracket_op.op_id

        if op_id == Id.Lit_At:
          maybe_decay_array = not quoted  # ${a[@]} decays but "${a[@]}" doesn't
          if val.tag == value_e.Undef:
            val = self._EmptyStrArrayOrError(part.token)
          elif val.tag == value_e.Str:
            e_die("Can't index string with @: %r", val, part=part)
          elif val.tag == value_e.StrArray:
            # TODO: Is this a no-op?  Just leave 'val' alone.
            val = value.StrArray(val.strs)

        elif op_id == Id.Arith_Star:
          maybe_decay_array = True  # both ${a[*]} and "${a[*]}" decay
          if val.tag == value_e.Undef:
            val = self._EmptyStrArrayOrError(part.token)
          elif val.tag == value_e.Str:
            e_die("Can't index string with *: %r", val, part=part)
          elif val.tag == value_e.StrArray:
            # TODO: Is this a no-op?  Just leave 'val' alone.
            # ${a[*]} or "${a[*]}" :  maybe_decay_array is always true
            val = value.StrArray(val.strs)

        else:
          raise AssertionError(op_id)  # unknown

      elif part.bracket_op.tag == bracket_op_e.ArrayIndex:
        anode = part.bracket_op.expr

        if val.tag == value_e.Undef:
          pass  # it will be checked later

        elif val.tag == value_e.Str:
          # Bash treats any string as an array, so we can't add our own
          # behavior here without making valid OSH invalid bash.
          e_die("Can't index string %r with integer", part.token.val,
                token=part.token)

        elif val.tag == value_e.StrArray:
          index = self.arith_ev.EvalToIndex(anode)
          try:
            # could be None because representation is sparse
            s = val.strs[index]
          except IndexError:
            s = None

          if s is None:
            val = value.Undef()
          else:
            val = value.Str(s)

        elif val.tag == value_e.AssocArray:
          key = self.arith_ev.EvalWordToString(anode)
          s = val.d.get(key)

          if s is None:
            val = value.Undef()
          else:
            val = value.Str(s)

        else:
          raise AssertionError(val.__class__.__name__)

      else:
        raise AssertionError(part.bracket_op.tag)

    else:  # no bracket op
      # When the array is "$@", var_name is None
      if var_name and val.tag in (value_e.StrArray, value_e.AssocArray):
        e_die("Array %r can't be referred to as a scalar (without @ or *)",
              var_name, part=part)

    if part.prefix_op:
      val = self._EmptyStrOrError(val)  # maybe error

      # TODO: maybe_decay_array for "${!assoc[@]}" vs. ${!assoc[*]}
      val = self._ApplyPrefixOp(val, part.prefix_op, token=part.token)
      # NOTE: When applying the length operator, we can't have a test or
      # suffix afterward.  And we don't want to decay the array

    elif part.suffix_op:
      op = part.suffix_op
      if op.tag == suffix_op_e.StringNullary:
        if op.op_id == Id.VOp0_P:
          prompt = self.prompt_ev.EvalPrompt(val)
          # readline gets rid of these, so we should too.
          p = prompt.replace('\x01', '').replace('\x02', '')
          val = value.Str(p)
        elif op.op_id == Id.VOp0_Q:
          val = value.Str(string_ops.ShellQuote(val.s))
        else:
          raise NotImplementedError(op.op_id)

      elif op.tag == suffix_op_e.StringUnary:
        if LookupKind(part.suffix_op.op_id) == Kind.VTest:
          # TODO: Change style to:
          # if self._ApplyTestOp(...)
          #   return
          # It should return whether anything was done.  If not, we continue to
          # the end, where we might throw an error.

          effect_part_vals, effect = self._ApplyTestOp(val, part.suffix_op,
                                                       quoted, part_vals)

          # NOTE: Splicing part_values is necessary because of code like
          # ${undef:-'a b' c 'd # e'}.  Each part_value can have a different
          # do_glob/do_elide setting.
          if effect == effect_e.SpliceParts:
            return  # EARLY RETURN, part_vals mutated

          elif effect == effect_e.SpliceAndAssign:
            if var_name is None:
              # TODO: error context
              e_die("Can't assign to special variable")
            else:
              # NOTE: This decays arrays too!  'set -o strict_array' could
              # avoid it.
              rhs_str = _DecayPartValuesToString(effect_part_vals,
                                                 self.splitter.GetJoinChar())
              state.SetLocalString(self.mem, var_name, rhs_str)
            return  # EARLY RETURN, part_vals mutated

          elif effect == effect_e.Error:
            error_str = _DecayPartValuesToString(effect_part_vals,
                                                 self.splitter.GetJoinChar())
            e_die("unset variable %r", error_str, token=part.token)

          else:
            pass  # do nothing, may still be undefined

        else:
          val = self._EmptyStrOrError(val)  # maybe error
          # Other suffix: value -> value
          val = self._ApplyUnarySuffixOp(val, part.suffix_op)

      elif op.tag == suffix_op_e.PatSub:  # PatSub, vectorized
        val = self._EmptyStrOrError(val)  # ${undef//x/y}

        # globs are supported in the pattern
        pat_val = self.EvalWordToString(op.pat, do_fnmatch=True)
        assert pat_val.tag == value_e.Str, pat_val

        if op.replace:
          replace_val = self.EvalWordToString(op.replace)
          assert replace_val.tag == value_e.Str, replace_val
          replace_str = replace_val.s
        else:
          replace_str = ''

        regex, warnings = glob_.GlobToERE(pat_val.s)
        if warnings:
          # TODO:
          # - Add 'set -o strict-glob' mode and expose warnings.
          #   "Glob is not in CANONICAL FORM".
          # - Propagate location info back to the 'op.pat' word.
          pass
        replacer = string_ops.GlobReplacer(regex, replace_str, op.spids[0])

        if val.tag == value_e.Str:
          s = replacer.Replace(val.s, op)
          val = value.Str(s)

        elif val.tag == value_e.StrArray:
          strs = []
          for s in val.strs:
            if s is not None:
              strs.append(replacer.Replace(s, op))
          val = value.StrArray(strs)

        elif val.tag == value_e.AssocArray:
          strs = []
          for s in val.d.itervalues():
            strs.append(replacer.Replace(s, op))
          val = value.StrArray(strs)

        else:
          raise AssertionError(val.__class__.__name__)

      elif op.tag == suffix_op_e.Slice:
        val = self._EmptyStrOrError(val)  # ${undef:3:1}

        if op.begin:
          begin = self.arith_ev.Eval(op.begin)
        else:
          begin = 0

        if op.length:
          length = self.arith_ev.Eval(op.length)
        else:
          length = None

        try:
          val = _PerformSlice(val, begin, length, part)
        except (util.InvalidSlice, util.InvalidUtf8) as e:
          if self.exec_opts.strict_word_eval:
            raise
          else:
            self.errfmt.PrettyPrintError(e, prefix='warning: ')
            if val.tag == value_e.Str:
              val = value.Str('')
            elif val.tag == value_e.StrArray:
              val = value.StrArray([])
            else:
              raise NotImplementedError

    # After applying suffixes, process maybe_decay_array here.
    if maybe_decay_array and val.tag == value_e.StrArray:
      val = self._DecayArray(val)

    # For the case where there are no prefix or suffix ops.
    val = self._EmptyStrOrError(val)

    # For example, ${a} evaluates to value.Str(), but we want a
    # part_value.String().
    part_val = _ValueToPartValue(val, quoted)
    part_vals.append(part_val)

  def _EvalWordPart(self, part, part_vals, quoted=False, is_subst=False):
    """Evaluate a word part.

    Args:
      part_vals: Output parameter.

    Returns:
      None
    """
    if part.tag == word_part_e.ArrayLiteralPart:  # e.g. ls a=(1 2)
      e_die("Unexpected array literal", part=part)
    elif part.tag == word_part_e.AssocArrayLiteral:
      e_die("Unexpected associative array literal", part=part)

    elif part.tag == word_part_e.LiteralPart:
      # Split if it's in a substitution.
      # That is: echo is not split, but ${foo:-echo} is split
      v = part_value.String(part.token.val, quoted, is_subst)
      part_vals.append(v)

    elif part.tag == word_part_e.EscapedLiteralPart:
      val = part.token.val
      assert len(val) == 2, val  # e.g. \*
      assert val[0] == '\\'
      s = val[1]
      v = part_value.String(s, True, False)
      part_vals.append(v)

    elif part.tag == word_part_e.SingleQuotedPart:
      if part.left.id == Id.Left_SingleQuote:
        s = ''.join(t.val for t in part.tokens)
      elif part.left.id == Id.Left_DollarSingleQuote:
        # NOTE: This could be done at compile time
        # TODO: Add location info for invalid backslash
        s = ''.join(word_compile.EvalCStringToken(t.id, t.val)
                    for t in part.tokens)
      else:
        raise AssertionError(part.left.id)

      v = part_value.String(s, True, False)
      part_vals.append(v)

    elif part.tag == word_part_e.DoubleQuotedPart:
      self._EvalDoubleQuotedPart(part, part_vals)

    elif part.tag == word_part_e.CommandSubPart:
      id_ = part.left_token.id
      if id_ in (Id.Left_DollarParen, Id.Left_Backtick):
        v = self._EvalCommandSub(part.command_list, quoted)

      elif id_ in (Id.Left_ProcSubIn, Id.Left_ProcSubOut):
        v = self._EvalProcessSub(part.command_list, id_)

      else:
        raise AssertionError(id_)

      part_vals.append(v)

    elif part.tag == word_part_e.SimpleVarSub:
      maybe_decay_array = False
      # 1. Evaluate from (var_name, var_num, token) -> defined, value
      if part.token.id == Id.VSub_DollarName:
        var_name = part.token.val[1:]
        val = self.mem.GetVar(var_name)
        if val.tag in (value_e.StrArray, value_e.AssocArray):
          e_die("Array %r can't be referred to as a scalar (without @ or *)",
                var_name, part=part)

      elif part.token.id == Id.VSub_Number:
        var_num = int(part.token.val[1:])
        val = self._EvalVarNum(var_num)
      else:
        val, maybe_decay_array = self._EvalSpecialVar(part.token.id, quoted)

      #log('SIMPLE %s', part)
      val = self._EmptyStrOrError(val, token=part.token)
      if maybe_decay_array and val.tag == value_e.StrArray:
        val = self._DecayArray(val)
      v = _ValueToPartValue(val, quoted)
      part_vals.append(v)

    elif part.tag == word_part_e.BracedVarSub:
      self._EvalBracedVarSub(part, part_vals, quoted)

    elif part.tag == word_part_e.TildeSubPart:
      # We never parse a quoted string into a TildeSubPart.
      assert not quoted
      s = self._EvalTildeSub(part.token)
      v = part_value.String(s, True, False)  # NOT split even when unquoted!
      part_vals.append(v)

    elif part.tag == word_part_e.ArithSubPart:
      num = self.arith_ev.Eval(part.anode)
      v = part_value.String(str(num), quoted, not quoted)
      part_vals.append(v)

    elif part.tag == word_part_e.ExtGlobPart:
      # Do NOT split these.
      part_vals.append(part_value.String(part.op.val, False, False))
      for i, w in enumerate(part.arms):
        if i != 0:
          part_vals.append(part_value.String('|', False, False))  # separator
        # This flattens the tree!
        self._EvalWordToParts(w, False, part_vals)  # eval like not quoted?
      part_vals.append(part_value.String(')', False, False))  # closing )

    else:
      raise AssertionError(part.__class__.__name__)

  def _EvalWordToParts(self, word, quoted, part_vals, is_subst=False):
    """Helper for EvalRhsWord, EvalWordSequence, etc.

    Returns:
      List of part_value.
      But note that this is a TREE.
    """
    if word.tag == word_e.CompoundWord:
      for p in word.parts:
        self._EvalWordPart(p, part_vals, quoted=quoted, is_subst=is_subst)

    elif word.tag == word_e.EmptyWord:
      part_vals.append(part_value.String('', quoted, not quoted))

    else:
      raise AssertionError(word.__class__.__name__)

  # Do we need this?
  def EvalWordToPattern(self, word):
    """
    Given a word, returns pattern.ERE if has an ExtGlobPart, or pattern.Fnmatch
    otherwise.

    NOTE: Have to handle nested extglob like: [[ foo == ${empty:-@(foo|bar) ]]
    """
    pass

  def EvalWordToString(self, word, do_fnmatch=False, do_ere=False):
    """
    Args:
      word: CompoundWord

    Used for redirect arg, ControlFlow arg, ArithWord, BoolWord, etc.

    do_fnmatch is true for case $pat and RHS of [[ == ]].

    pat="*.py"
    case $x in
      $pat) echo 'matches glob pattern' ;;
      "$pat") echo 'equal to glob string' ;;  # must be glob escaped
    esac

    TODO: Raise AssertionError if it has ExtGlobPart.
    """
    if word.tag == word_e.EmptyWord:
      return value.Str('')

    part_vals = []
    for p in word.parts:
      self._EvalWordPart(p, part_vals, quoted=False)

    strs = []
    for part_val in part_vals:
      if part_val.tag == part_value_e.String:
        # [[ foo == */"*".py ]] or case *.py) ... esac
        if do_fnmatch and part_val.quoted:
          s = glob_.GlobEscape(part_val.s)
        elif do_ere and part_val.quoted:
          s = glob_.ExtendedRegexEscape(part_val.s)
        else:
          s = part_val.s
      else:
        if self.exec_opts.strict_array:
          # Examples: echo f > "$@"; local foo="$@"

          # TODO: This attributes too coarsely, to the word rather than the
          # parts.  Problem: the word is a TREE of parts, but we only have a
          # flat list of part_vals.  The only case where we really get arrays
          # is "$@", "${a[@]}", "${a[@]//pat/replace}", etc.
          e_die("This word should yield a string, but it contains an array",
                word=word)

          # TODO: Maybe add detail like this.
          #e_die('RHS of assignment should only have strings.  '
          #      'To assign arrays, use b=( "${a[@]}" )')
        else:
          # It appears to not respect IFS
          s = ' '.join(s for s in part_val.strs if s is not None)

      strs.append(s)

    return value.Str(''.join(strs))

  def EvalForPlugin(self, w):
    """Wrapper around EvalWordToString that prevents errors.
    
    Runtime errors like $(( 1 / 0 )) and mutating $? like $(exit 42) are
    handled here.
    """
    self.mem.PushStatusFrame()  # to "sandbox" $? and $PIPESTATUS
    try:
      val = self.EvalWordToString(w)
    except util.FatalRuntimeError as e:
      val = value.Str('<Runtime error: %s>' % e.UserErrorString())
    except (OSError, IOError) as e:
      # This is like the catch-all in Executor.ExecuteAndCatch().
      val = value.Str('<I/O error: %s>' % posix.strerror(e.errno))
    except KeyboardInterrupt:
      val = value.Str('<Ctrl-C>')
    finally:
      self.mem.PopStatusFrame()
    return val

  def EvalRhsWord(self, word):
    """syntax.word -> value

    Used for RHS of assignment.  There is no splitting.
    """
    if word.tag == word_e.EmptyWord:
      return value.Str('')

    if len(word.parts) == 1:
      part0 = word.parts[0]

      # Special case for a=(1 2).  ArrayLiteralPart won't appear in words that
      # don't look like assignments.
      if part0.tag == word_part_e.ArrayLiteralPart:
        array_words = part0.words
        words = braces.BraceExpandWords(array_words)
        strs = self.EvalWordSequence(words)
        #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
        return value.StrArray(strs)

      if part0.tag == word_part_e.AssocArrayLiteral:
        d = {}
        n = len(part0.pairs)
        i = 0
        while i < n:
          k = self.EvalWordToString(part0.pairs[i])
          v = self.EvalWordToString(part0.pairs[i+1])
          d[k.s] = v.s
          i += 2
        return value.AssocArray(d)

    # If RHS doens't look like a=( ... ), then it must be a string.
    return self.EvalWordToString(word)

  def _EvalWordFrame(self, frame, argv):
    all_empty = True
    all_quoted = True
    any_quoted = False

    #log('--- frame %s', frame)

    for s, quoted, _ in frame:
      if s:
        all_empty = False

      if quoted:
        any_quoted = True
      else:
        all_quoted = False

    # Elision of ${empty}${empty} but not $empty"$empty" or $empty""
    if all_empty and not any_quoted:
      return

    # If every frag is quoted, e.g. "$a$b" or any part in "${a[@]}"x, then
    # don't do word splitting or globbing.
    if all_quoted:
      a = ''.join(s for s, _, _ in frame)
      argv.append(a)
      return

    will_glob = not self.exec_opts.noglob

    # Array of strings, some of which are BOTH IFS-escaped and GLOB escaped!
    frags = []
    for frag, quoted, do_split in frame:
      if will_glob:
        if quoted:
          frag = glob_.GlobEscape(frag)
        else:
          # We're going to both split and glob, so backslash escape TWICE.

          # If we have a literal \, then we turn it into \\\\.
          # Splitting takes \\\\ -> \\
          # Globbing takes \\ to \ if it doesn't match
          frag = _BackslashEscape(frag)

      if do_split:
        frag = _BackslashEscape(frag)
      else:
        frag = self.splitter.Escape(frag)

      frags.append(frag)

    flat = ''.join(frags)
    #log('flat: %r', flat)

    args = self.splitter.SplitForWordEval(flat)

    # space=' '; argv $space"".  We have a quoted part, but we CANNOT elide.
    # Add it back and don't bother globbing.
    if not args and any_quoted:
      argv.append('')
      return

    #log('split args: %r', args)
    for a in args:
      # TODO: Expand() should take out parameter.
      results = self.globber.Expand(a)
      argv.extend(results)

  def _EvalWordToArgv(self, w):
    # type: (word__CompoundWord) -> List[str]
    """Helper for _EvalAssignBuiltin.

    Splitting and globbing are disabled for assignment builtins.

    Example: declare -"${a[@]}" b=(1 2)
    where a is [x b=a d=a]
    """
    part_vals = []
    self._EvalWordToParts(w, False, part_vals)  # not double quoted
    frames = _MakeWordFrames(part_vals)
    argv = []
    for frame in frames:
      argv.append(''.join(s for (s, _, _) in frame))  # no split or glob
    #log('argv: %s', argv)
    return argv

  def _EvalAssignBuiltin(self, builtin_id, arg0, words):
    # type: (List[word__CompoundWord]) -> cmd_value__Assign
    """
    Handles both static and dynamic assignment, e.g.

      x='foo=bar'
      local a=(1 2) $x
    """
    # Grammar:
    #
    # ('builtin' | 'command')* keyword flag* pair*
    # flag = [-+].*
    #
    # There is also command -p, but we haven't implemented it.  Maybe just punt
    # on it.  Punted on 'builtin' and 'command' for now too.

    def _SplitAssignArg(arg, w):
      i = arg.find('=')
      prefix = arg[:i]
      if i != -1 and match.IsValidVarName(prefix):
        return lvalue.Named(prefix), value.Str(arg[i+1:]),
      else:
        if match.IsValidVarName(arg):  # local foo   # foo becomes undefined
          return lvalue.Named(arg), None
        else:
          e_die("Invalid variable name %r", arg, word=w)

    started_pairs = False

    flags = [arg0]
    flag_spids = [word.LeftMostSpanForWord(words[0])]
    assign_args = []

    n = len(words)
    for i in xrange(1, n):  # skip first word
      w = words[i]
      word_spid = word.LeftMostSpanForWord(w)

      if word.IsVarLike(w):
        started_pairs = True  # Everything from now on is an assign_pair

      if started_pairs:
        left_token, close_token, part_offset = word.DetectAssignment(w)
        if left_token:  # Detected statically
          if left_token.id != Id.Lit_VarLike:
            # (not guaranteed since started_pairs is set twice)
            e_die('LHS array not allowed in assignment builtin', word=w)
          tok_val = left_token.val
          if tok_val[-2] == '+':
            e_die('+= not allowed in assignment builtin', word=w)

          left = lvalue.Named(tok_val[:-1])
          rhs_word = osh_word.CompoundWord(w.parts[part_offset:])
          # tilde detection only happens on static assignments!
          rhs_word = word.TildeDetect(rhs_word) or rhs_word
          right = self.EvalRhsWord(rhs_word)
          arg2 = assign_arg(left, right, word_spid)
          assign_args.append(arg2)

        else:  # e.g. export $dynamic
          argv = self._EvalWordToArgv(w)
          for arg in argv:
            left, right = _SplitAssignArg(arg, w)
            arg2 = assign_arg(left, right, word_spid)
            assign_args.append(arg2)

      else:
        argv = self._EvalWordToArgv(w)
        for arg in argv:
          if arg.startswith('-') or arg.startswith('+'):  # e.g. declare -r +r
            flags.append(arg)
            flag_spids.append(word_spid)
          else:  # e.g. export $dynamic 
            left, right = _SplitAssignArg(arg, w)
            arg2 = assign_arg(left, right, word_spid)
            assign_args.append(arg2)
            started_pairs = True

    return cmd_value.Assign(builtin_id, flags, flag_spids, assign_args)

  def EvalWordSequence2(self, words, allow_assign=False):
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
    arg_vec = arg_vector()
    strs = []
    spids = []

    n = 0
    for i, w in enumerate(words):
      part_vals = []
      self._EvalWordToParts(w, False, part_vals)  # not double quoted

      # DYNAMICALLY detect if we're going to run an assignment builtin, and
      # change the rest of the evaluation algorithm if so.
      #
      # We want to allow:
      #   e=export
      #   $e foo=bar
      #
      # But we don't want to evaluate the first word twice in the case of:
      #   $(some-command) --flag

      if allow_assign and i == 0 and len(part_vals) == 1:
        val0 = part_vals[0]
        if isinstance(val0, part_value__String) and not val0.quoted:
          builtin_id = builtin.ResolveAssign(val0.s)
          if builtin_id != builtin_e.NONE:
            return self._EvalAssignBuiltin(builtin_id, val0.s, words)

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

      # Do splitting and globbing.  Each frame will append zero or more args.
      for frame in frames:
        self._EvalWordFrame(frame, strs)

      # Fill in spids parallel to strs.
      n_next = len(strs)
      spid = word.LeftMostSpanForWord(w)
      for _ in xrange(n_next - n):
        spids.append(spid)
      n = n_next

    # A non-assignment command.
    # NOTE: Can't look up builtins here like we did for assignment, because
    # functions can override builtins.
    return cmd_value.Argv(strs, spids)

  def EvalWordSequence(self, words):
    # type: (List[word__CompoundWord]) -> List[str]
    """For arrays and for loops.  They don't allow assignment builtins."""
    cmd_val = self.EvalWordSequence2(words)
    return cmd_val.argv


class NormalWordEvaluator(_WordEvaluator):

  def __init__(self, mem, exec_opts, exec_deps, arena):
    _WordEvaluator.__init__(self, mem, exec_opts, exec_deps, arena)
    self.ex = exec_deps.ex

  def _EvalCommandSub(self, node, quoted):
    stdout = self.ex.RunCommandSub(node)
    return part_value.String(stdout, quoted, not quoted)

  def _EvalProcessSub(self, node, id_):
    dev_path = self.ex.RunProcessSub(node, id_)
    # pretend it's quoted; no split or glob
    return part_value.String(dev_path, True, False)


class CompletionWordEvaluator(_WordEvaluator):
  """An evaluator that has no access to an executor.

  NOTE: core/completion.py doesn't actually try to use these strings to
  complete.  If you have something like 'echo $(echo hi)/f<TAB>', it sees the
  inner command as the last one, and knows that it is not at the end of the
  line.
  """
  def _EvalCommandSub(self, node, quoted):
    return part_value.String('__NO_COMMAND_SUB__', quoted, not quoted)

  def _EvalProcessSub(self, node, id_):
    # pretend it's quoted; no split or glob
    return part_value.String('__NO_PROCESS_SUB__', True, False)
