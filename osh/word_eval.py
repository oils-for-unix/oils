"""
word_eval.py - Evaluator for the word language.
"""

import pwd

from _devbuild.gen.id_kind_asdl import Id, Kind, Id_str, Kind_str
from _devbuild.gen.syntax_asdl import (
    braced_var_sub, Token,
    word, word_e, word_t, compound_word,
    bracket_op_e, suffix_op_e, word_part_e,
    bracket_op__ArrayIndex, bracket_op__WholeArray,
    suffix_op__Nullary, suffix_op__PatSub, suffix_op__Slice,
    suffix_op__Unary, sh_array_literal,
    single_quoted, double_quoted, simple_var_sub, command_sub,
    word_part__ArithSub, word_part__EscapedLiteral,
    word_part__AssocArrayLiteral, word_part__ExprSub,
    word_part__ExtGlob, word_part__FuncCall,
    word_part__Splice, word_part__TildeSub,
)
from _devbuild.gen.runtime_asdl import (
    builtin_e, effect_e,
    part_value, part_value_e, part_value_t, part_value__String, part_value__Array,
    value, value_e, value_t, lvalue,
    assign_arg, 
    cmd_value_e, cmd_value_t, cmd_value, cmd_value__Assign, cmd_value__Argv,
    value__Str, value__AssocArray, value__MaybeStrArray, value__Obj,
    value__Undef,
)
from core import error
from core import process
from core.util import log, e_die
from frontend import lookup
from frontend import match
from osh import braces
from osh import builtin
from osh import glob_
from osh import string_ops
from osh import state
from osh import word_
from osh import word_compile

from mycpp.mylib import tagswitch
from mycpp import mylib

import posix_ as posix

from typing import Optional, Tuple, List, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.id_kind_asdl import Id_t
  from _devbuild.gen.syntax_asdl import (
    command_t, speck, word_part_t
  )
  from _devbuild.gen.runtime_asdl import (
    builtin_t, effect_t, lvalue__Named
  )
  from core.alloc import Arena
  from osh.cmd_exec import Deps
  from osh.state import ExecOpts, Mem


# For compatibility, ${BASH_SOURCE} and ${BASH_SOURCE[@]} are both valid.
_STRING_AND_ARRAY = 'BASH_SOURCE'


def EvalSingleQuoted(part):
  # type: (single_quoted) -> str
  if part.left.id == Id.Left_SingleQuoteRaw:
    tmp = [t.val for t in part.tokens]
    s = ''.join(tmp)
  elif part.left.id == Id.Left_SingleQuoteC:
    # NOTE: This could be done at compile time
    # TODO: Add location info for invalid backslash
    tmp = [word_compile.EvalCStringToken(t.id, t.val) for t in part.tokens]
    s = ''.join(tmp)
  else:
    raise AssertionError(Id_str(part.left.id))
  return s


# NOTE: Could be done with util.BackslashEscape like glob_.GlobEscape().
def _BackslashEscape(s):
  # type: (str) -> str
  """Double up backslashes.

  Useful for strings about to be globbed and strings about to be IFS escaped.
  """
  return s.replace('\\', '\\\\')


def _ValueToPartValue(val, quoted):
  # type: (value_t, bool) -> part_value_t
  """Helper for VarSub evaluation.

  Called by _EvalBracedVarSub and _EvalWordPart for SimpleVarSub.
  """
  UP_val = val

  with tagswitch(val) as case:
    if case(value_e.Str):
      val = cast(value__Str, UP_val)
      return part_value.String(val.s, quoted, not quoted)

    elif case(value_e.MaybeStrArray):
      val = cast(value__MaybeStrArray, UP_val)
      return part_value.Array(val.strs)

    elif case(value_e.AssocArray):
      val = cast(value__AssocArray, UP_val)
      # TODO: Is this correct?
      return part_value.Array(val.d.values())

    elif case(value_e.Obj):
      if mylib.PYTHON:
        val = cast(value__Obj, UP_val)
        return part_value.String(str(val.obj), quoted, not quoted)
      # Not in C++
      raise AssertionError()

    else:
      # Undef should be caught by _EmptyStrOrError().
      raise AssertionError(val.tag_())


def _MakeWordFrames(part_vals):
  # type: (List[part_value_t]) -> List[List[Tuple[str, bool, bool]]]
  """
  A word evaluates to a flat list of part_value (String or Array).  frame is a
  portion that results in zero or more args.  It can never be joined.  This
  idea exists because of arrays like "$@" and "${a[@]}".

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
  current = []  # type: List[Tuple[str, bool, bool]]
  frames = [current]

  for p in part_vals:
    UP_p = p

    with tagswitch(p) as case:
      if case(part_value_e.String):
        p = cast(part_value__String, UP_p)
        current.append((p.s, p.quoted, p.do_split))

      elif case(part_value_e.Array):
        p = cast(part_value__Array, UP_p)

        is_first = True
        for s in p.strs:
          if s is None:
            continue  # ignore undefined array entries

          # Arrays parts are always quoted; otherwise they would have decayed to
          # a string.
          portion = (s, True, False)
          if is_first:
            current.append(portion)
            is_first = False
          else:
            current = [portion]
            frames.append(current)  # singleton frame

      else:
        raise AssertionError()

  return frames


# TODO: This could be _MakeWordFrames and then sep.join().  It's redunant.
def _DecayPartValuesToString(part_vals, join_char):
  # type: (List[part_value_t], str) -> str
  # Decay ${a=x"$@"x} to string.
  out = []  # type: List[str]
  for p in part_vals:
    UP_p = p
    with tagswitch(p) as case:
      if case(part_value_e.String):
        p = cast(part_value__String, UP_p)
        out.append(p.s)
      else:
        p = cast(part_value__Array, UP_p)
        # TODO: Eliminate double join for speed?
        tmp = [s for s in p.strs if s is not None]
        out.append(join_char.join(tmp))
  return ''.join(out)


def _PerformSlice(val,  # type: value_t
                  begin,  # type: int
                  length,  # type: Optional[int]
                  part,  # type: braced_var_sub
                  ):
  # type: (...) -> value_t
  UP_val = val
  with tagswitch(val) as case:
    if case(value_e.Str):  # Slice UTF-8 characters in a string.
      val = cast(value__Str, UP_val)
      s = val.s

      if begin < 0:
        # It could be negative if we compute unicode length, but that's
        # confusing.

        # TODO: Instead of attributing it to the word part, it would be
        # better if we attributed it to arith_expr begin.
        raise error.InvalidSlice(
            "The start index of a string slice can't be negative: %d",
            begin, part=part)

      byte_begin = string_ops.AdvanceUtf8Chars(s, begin, 0)

      if length is None:
        byte_end = len(s)
      else:
        if length < 0:
          # TODO: Instead of attributing it to the word part, it would be
          # better if we attributed it to arith_expr begin.
          raise error.InvalidSlice(
              "The length of a string slice can't be negative: %d",
              length, part=part)

        byte_end = string_ops.AdvanceUtf8Chars(s, length, byte_begin)

      substr = s[byte_begin : byte_end]
      val = value.Str(substr)

    elif case(value_e.MaybeStrArray):  # Slice array entries.
      val = cast(value__MaybeStrArray, UP_val)
      # NOTE: This error is ALWAYS fatal in bash.  It's inconsistent with
      # strings.
      if length and length < 0:
        e_die("The length index of a array slice can't be negative: %d",
              length, part=part)

      # NOTE: unset elements don't count towards the length.
      strs = []  # type: List[str]
      for s in val.strs[begin:]:
        if s is not None:
          strs.append(s)
          if len(strs) == length:  # never true for unspecified length
            break
      val = value.MaybeStrArray(strs)

    elif case(value_e.AssocArray):
      val = cast(value__AssocArray, UP_val)
      e_die("Can't slice associative arrays", part=part)

    else:
      raise NotImplementedError(val.tag_())

  return val


class SimpleWordEvaluator(object):
  """For use by the _ExprEvaluator."""

  def EvalWordToString(self, w, do_fnmatch=False, do_ere=False):
    # type: (word_t, bool, bool) -> value__Str
    raise NotImplementedError()


class _WordEvaluator(SimpleWordEvaluator):
  """Abstract base class for word evaluators.

  Public entry points:
    EvalWordToString
    EvalForPlugin
    EvalRhsWord
    EvalWordSequence
    EvalWordSequence2
  """
  def __init__(self, mem, exec_opts, exec_deps, arena):
    # type: (Mem, ExecOpts, Deps, Arena) -> None
    self.mem = mem  # for $HOME, $1, etc.
    self.exec_opts = exec_opts  # for nounset
    self.splitter = exec_deps.splitter
    self.prompt_ev = exec_deps.prompt_ev
    self.arith_ev = exec_deps.arith_ev
    self.expr_ev = exec_deps.expr_ev
    self.errfmt = exec_deps.errfmt

    self.globber = glob_.Globber(exec_opts)
    # TODO: Consolidate into exec_deps.  Executor also instantiates one.

  def _EvalCommandSub(self, part, quoted):
    # type: (command_t, bool) -> part_value_t
    """Abstract since it has a side effect.

    Args:
      part: command_sub

    Returns:
       part_value
    """
    raise NotImplementedError()

  def _EvalProcessSub(self, part, id_):
    # type: (command_t, int) -> part_value_t
    """Abstract since it has a side effect.

    Args:
      part: command_sub

    Returns:
       part_value
    """
    raise NotImplementedError()

  def _EvalTildeSub(self, token):
    # type: (Token) -> str
    """Evaluates ~ and ~user.

    Args:
      prefix: The tilde prefix (possibly empty)
    """
    if token.val == '~':
      # First look up the HOME var, then ask the OS.  This is what bash does.
      val = self.mem.GetVar('HOME')
      UP_val = val
      if val.tag_() == value_e.Str:
        val = cast(value__Str, UP_val)
        return val.s
      return process.GetHomeDir()

    # For ~otheruser/src.  TODO: Should this be cached?
    # http://linux.die.net/man/3/getpwnam
    name = token.val[1:]
    try:
      e = pwd.getpwnam(name)
    except KeyError:
      # If not found, it's ~nonexistent.  TODO: In strict mode, this should be
      # an error, kind of like failglob and nounset.  Perhaps strict-tilde or
      # even strict-word-eval.
      result = token.val
    else:
      result = e.pw_dir

    return result

  def _EvalVarNum(self, var_num):
    # type: (int) -> value__Str
    assert var_num >= 0
    return self.mem.GetArgNum(var_num)

  def _EvalSpecialVar(self, op_id, quoted):
    # type: (int, bool) -> Tuple[value_t, bool]
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
      val = value.MaybeStrArray(argv) # type: value_t
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

  def _ApplyTestOp(self,
                   val,  # type: value_t
                   op,  # type: suffix_op__Unary
                   quoted,  # type: bool
                   part_vals,  # type: Optional[List[part_value_t]]
                   ):
    # type: (...) -> Tuple[List[part_value_t], effect_t]
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
    undefined = (val.tag_() == value_e.Undef)

    no = None  # type: List[part_value_t]

    # TODO: Change this to a bitwise test?
    if op.op_id in (
        Id.VTest_ColonHyphen, Id.VTest_ColonEquals, Id.VTest_ColonQMark,
        Id.VTest_ColonPlus):
      UP_val = val
      with tagswitch(val) as case:
        if case(value_e.Undef):
          is_falsey = True
        elif case(value_e.Str):
          val = cast(value__Str, UP_val)
          is_falsey = not val.s
        elif case(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          is_falsey = not val.strs
        else:
          raise NotImplementedError(val.tag_())
    else:
      is_falsey = undefined

    #print('!!',id, is_falsey)
    if op.op_id in (Id.VTest_ColonHyphen, Id.VTest_Hyphen):
      if is_falsey:
        assert op.arg_word
        self._EvalWordToParts(op.arg_word, quoted, part_vals, is_subst=True)
        return no, effect_e.SpliceParts
      else:
        return no, effect_e.NoOp

    elif op.op_id in (Id.VTest_ColonPlus, Id.VTest_Plus):
      # Inverse of the above.
      if is_falsey:
        return no, effect_e.NoOp
      else:
        assert op.arg_word
        self._EvalWordToParts(op.arg_word, quoted, part_vals, is_subst=True)
        return no, effect_e.SpliceParts

    elif op.op_id in (Id.VTest_ColonEquals, Id.VTest_Equals):
      if is_falsey:
        # Collect new part vals.
        assign_part_vals = []  # type: List[part_value_t]
        self._EvalWordToParts(op.arg_word, quoted, assign_part_vals,
                              is_subst=True)

        # Append them to out param AND return them.
        part_vals.extend(assign_part_vals)
        return assign_part_vals, effect_e.SpliceAndAssign
      else:
        return no, effect_e.NoOp

    elif op.op_id in (Id.VTest_ColonQMark, Id.VTest_QMark):
      if is_falsey:
        # The arg is the error mesage
        error_part_vals = []  # type: List[part_value_t]
        self._EvalWordToParts(op.arg_word, quoted, error_part_vals,
                              is_subst=True)
        return error_part_vals, effect_e.Error
      else:
        return no, effect_e.NoOp

    else:
      raise NotImplementedError(Id_str(op.op_id))

  def _EvalIndirectArrayExpansion(self, name, index):
    # type: (str, str) -> Optional[value_t]
    """Expands ${!ref} when $ref has the form `name[index]`.

    Args:
      name, index: arbitrary strings
    Returns:
      value, or None if invalid
    """
    if not match.IsValidVarName(name):
      return None

    val = self.mem.GetVar(name)
    UP_val = val

    with tagswitch(val) as case:
      if case(value_e.Undef):
        return value.Undef()

      elif case(value_e.Str):
        return None

      elif case(value_e.MaybeStrArray):
        val = cast(value__MaybeStrArray, UP_val)
        if index in ('@', '*'):
          # TODO: maybe_decay_array
          return value.MaybeStrArray(val.strs)
        try:
          index_num = int(index)
        except ValueError:
          return None
        try:
          return value.Str(val.strs[index_num])
        except IndexError:
          return value.Undef()

      elif case(value_e.AssocArray):
        val = cast(value__AssocArray, UP_val)
        if index in ('@', '*'):
          raise NotImplementedError()
        try:
          return value.Str(val.d[index])
        except KeyError:
          return value.Undef()

      else:
        raise AssertionError()

  def _ApplyPrefixOp(self, val, prefix_op, token):
    # type: (value_t, speck, Token) -> value_t
    """
    Returns:
      value
    """
    assert val.tag != value_e.Undef

    op_id = prefix_op.id

    if op_id == Id.VSub_Pound:  # LENGTH
      UP_val = val
      with tagswitch(val) as case:
        if case(value_e.Str):
          val = cast(value__Str, UP_val)
          # NOTE: Whether bash counts bytes or chars is affected by LANG
          # environment variables.
          # Should we respect that, or another way to select?  set -o
          # count-bytes?

          # https://stackoverflow.com/questions/17368067/length-of-string-in-bash
          try:
            length = string_ops.CountUtf8Chars(val.s)
          except error.InvalidUtf8 as e:
            # Add this hear so we don't have to add it so far down the stack.
            # TODO: It's better to show BOTH this CODE an the actual DATA
            # somehow.
            e.span_id = token.span_id

            if self.exec_opts.strict_word_eval:
              raise
            else:
              # NOTE: Doesn't make the command exit with 1; it just returns a
              # length of -1.
              self.errfmt.PrettyPrintError(e, prefix='warning: ')
              return value.Str('-1')

        elif case(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          # There can be empty placeholder values in the array.
          length = 0
          for s in val.strs:
            if s is not None:
              length += 1

        elif case(value_e.AssocArray):
          val = cast(value__AssocArray, UP_val)
          length = len(val.d)

        else:
          raise AssertionError()

      return value.Str(str(length))

    elif op_id == Id.VSub_Bang:  # ${!foo}, "indirect expansion"
      # NOTES:
      # - Could translate to eval('$' + name) or eval("\$$name")
      # - ${!array[@]} means something completely different.  TODO: implement
      #   that.
      # - It might make sense to suggest implementing this with associative
      #   arrays?

      UP_val = val
      with tagswitch(val) as case:
        if case(value_e.Str):
          val = cast(value__Str, UP_val)
          # plain variable name, like 'foo'
          if match.IsValidVarName(val.s):
            return self.mem.GetVar(val.s)

          # positional argument, like '1'
          try:
            return self.mem.GetArgNum(int(val.s))
          except ValueError:
            pass

          if val.s in ('@', '*'):
            # TODO: maybe_decay_array
            return value.MaybeStrArray(self.mem.GetArgv())

          # otherwise an array reference, like 'arr[0]' or 'arr[xyz]' or 'arr[@]'
          i = val.s.find('[')
          if i >= 0 and val.s[-1] == ']':
            name = val.s[:i]
            index = val.s[i+1:-1]
            result = self._EvalIndirectArrayExpansion(name, index)
            if result is not None:
              return result

          # Note that bash doesn't consider this fatal.  It makes the
          # command exit with '1', but we don't have that ability yet?
          e_die('Bad indirect expansion: %r', val.s, token=token)

        elif case(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          # translation issue: tuple indices not supported in list comprehensions
          #indices = [str(i) for i, s in enumerate(val.strs) if s is not None]
          indices = []  # type: List[str]
          for i, s in enumerate(val.strs):
            if s is not None:
              indices.append(str(i))
          return value.MaybeStrArray(indices)

        elif case(value_e.AssocArray):
          val = cast(value__AssocArray, UP_val)
          assert val.d is not None  # for MyPy, so it's not Optional[]
          indices = [str(k) for k in val.d]
          return value.MaybeStrArray(indices)

        else:
          raise NotImplementedError(val.tag_())

    else:
      raise AssertionError(op_id)

  def _ApplyUnarySuffixOp(self, val, op):
    # type: (value_t, suffix_op__Unary) -> value_t
    assert val.tag != value_e.Undef

    op_kind = lookup.LookupKind(op.op_id)

    if op_kind == Kind.VOp1:
      # NOTE: glob syntax is supported in ^ ^^ , ,, !  As well as % %% # ##.
      arg_val = self.EvalWordToString(op.arg_word, do_fnmatch=True)
      assert arg_val.tag == value_e.Str

      UP_val = val
      with tagswitch(val) as case:
        if case(value_e.Str):
          val = cast(value__Str, UP_val)
          s = string_ops.DoUnarySuffixOp(val.s, op, arg_val.s)
          #log('%r %r -> %r', val.s, arg_val.s, s)
          new_val = value.Str(s) # type: value_t

        elif case(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          # ${a[@]#prefix} is VECTORIZED on arrays.  Oil should have this too.
          strs = []  # type: List[str]
          for s in val.strs:
            if s is not None:
              strs.append(string_ops.DoUnarySuffixOp(s, op, arg_val.s))
          new_val = value.MaybeStrArray(strs)

        elif case(value_e.AssocArray):
          val = cast(value__AssocArray, UP_val)
          strs = []
          for s in val.d.itervalues():
            strs.append(string_ops.DoUnarySuffixOp(s, op, arg_val.s))
          new_val = value.MaybeStrArray(strs)

        else:
          raise AssertionError(val.tag_())

    else:
      raise AssertionError(Kind_str(op_kind))

    return new_val

  def _EvalDoubleQuoted(self,
                        parts,  # type: List[word_part_t]
                        part_vals,  # type: List[part_value_t]
                        ):
    # type: (...) -> None
    """DoubleQuoted -> part_value

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

    # Special case for "".  The parser outputs (DoubleQuoted []), instead
    # of (DoubleQuoted [Literal '']).  This is better but it means we
    # have to check for it.
    if len(parts) == 0:
      v = part_value.String('', True, False)
      part_vals.append(v)
      return

    for p in parts:
      self._EvalWordPart(p, part_vals, quoted=True)

  def EvalDoubleQuotedToString(self, dq_part):
    # type: (double_quoted) -> str
    """For double quoted strings in Oil expressions.

    Example: var x = "$foo-${foo}"
    """
    part_vals = []  # type: List[part_value_t]
    self._EvalDoubleQuoted(dq_part.parts, part_vals)
    return self._PartValsToString(part_vals, dq_part.left.span_id)

  def _DecayArray(self, val):
    # type: (value__MaybeStrArray) -> value__Str
    """Decay $* to a string."""
    assert val.tag == value_e.MaybeStrArray, val
    sep = self.splitter.GetJoinChar()
    tmp = [s for s in val.strs if s is not None]
    return value.Str(sep.join(tmp))

  def _BashArrayCompat(self, val):
    # type: (value__MaybeStrArray) -> value__Str
    """Decay ${array} to ${array[0]}."""
    assert val.tag == value_e.MaybeStrArray, val
    s = val.strs[0] if val.strs else ''
    return value.Str(s)

  def _EmptyStrOrError(self, val, token=None):
    # type: (value_t, Optional[Token]) -> value_t
    if val.tag_() == value_e.Undef:
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

  def _EmptyMaybeStrArrayOrError(self, token):
    # type: (Token) -> value_t
    assert token is not None
    if self.exec_opts.nounset:
      e_die('Undefined array %r', token.val, token=token)
    else:
      return value.MaybeStrArray([])

  def _EvalBracedVarSub(self, part, part_vals, quoted):
    # type: (braced_var_sub, List[part_value_t], bool) -> None
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
    bash_array_compat = False  # for ${BASH_SOURCE}

    var_name = None  # For ${foo=default}

    # 1. Evaluate from (var_name, var_num, token Id) -> value
    if part.token.id == Id.VSub_Name:
      var_name = part.token.val
      # TODO: LINENO can use its own span_id!
      val = self.mem.GetVar(var_name)
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
      bracket_op = part.bracket_op
      UP_bracket_op = bracket_op
      with tagswitch(bracket_op) as case:
        if case(bracket_op_e.WholeArray):
          bracket_op = cast(bracket_op__WholeArray, UP_bracket_op)
          op_id = bracket_op.op_id

          if op_id == Id.Lit_At:
            maybe_decay_array = not quoted  # ${a[@]} decays but "${a[@]}" doesn't
            UP_val = val
            with tagswitch(val) as case2:
              if case2(value_e.Undef):
                val = self._EmptyMaybeStrArrayOrError(part.token)
              elif case2(value_e.Str):
                val = cast(value__Str, UP_val)
                e_die("Can't index string with @: %r", val, part=part)
              elif case2(value_e.MaybeStrArray):
                val = cast(value__MaybeStrArray, UP_val)
                # TODO: Is this a no-op?  Just leave 'val' alone.
                val = value.MaybeStrArray(val.strs)

          elif op_id == Id.Arith_Star:
            maybe_decay_array = True  # both ${a[*]} and "${a[*]}" decay
            UP_val = val
            with tagswitch(val) as case2:
              if case2(value_e.Undef):
                val = self._EmptyMaybeStrArrayOrError(part.token)
              elif case2(value_e.Str):
                val = cast(value__Str, UP_val)
                e_die("Can't index string with *: %r", val, part=part)
              elif case2(value_e.MaybeStrArray):
                val = cast(value__MaybeStrArray, UP_val)
                # TODO: Is this a no-op?  Just leave 'val' alone.
                # ${a[*]} or "${a[*]}" :  maybe_decay_array is always true
                val = value.MaybeStrArray(val.strs)

          else:
            raise AssertionError(op_id)  # unknown

        elif case(bracket_op_e.ArrayIndex):
          bracket_op = cast(bracket_op__ArrayIndex, UP_bracket_op)
          anode = bracket_op.expr

          UP_val = val
          with tagswitch(val) as case2:
            if case2(value_e.Undef):
              pass  # it will be checked later

            elif case2(value_e.Str):
              # Bash treats any string as an array, so we can't add our own
              # behavior here without making valid OSH invalid bash.
              e_die("Can't index string %r with integer", part.token.val,
                    token=part.token)

            elif case2(value_e.MaybeStrArray):
              val = cast(value__MaybeStrArray, UP_val)
              index = self.arith_ev.EvalToInt(anode)
              try:
                # could be None because representation is sparse
                s = val.strs[index]
              except IndexError:
                s = None

              if s is None:
                val = value.Undef()
              else:
                val = value.Str(s)

            elif case2(value_e.AssocArray):
              val = cast(value__AssocArray, UP_val)
              key = self.arith_ev.EvalWordToString(anode)
              s = val.d.get(key)

              if s is None:
                val = value.Undef()
              else:
                val = value.Str(s)

            else:
              raise AssertionError(val.tag_())

        else:
          raise AssertionError(bracket_op.tag_())

    else:  # no bracket op
      # When the array is "$@", var_name is None
      if var_name and val.tag_() in (value_e.MaybeStrArray, value_e.AssocArray):
        if var_name == _STRING_AND_ARRAY:
          bash_array_compat = True
        else:
          e_die("Array %r can't be referred to as a scalar (without @ or *)",
                var_name, part=part)

    if part.prefix_op:
      val = self._EmptyStrOrError(val)  # maybe error

      if part.suffix_op:
        # Must be ${!prefix@}
        assert part.prefix_op.id == Id.VSub_Bang
        names = self.mem.VarNamesStartingWith(part.token.val)
        names.sort()
        val = value.MaybeStrArray(names)

        # Test for maybe_decay_array
        UP_suffix_op = part.suffix_op
        if UP_suffix_op.tag_() == suffix_op_e.Nullary:
          suffix_op = cast(suffix_op__Nullary, UP_suffix_op)
          # "${!prefix@}" is the only one that doesn't decay
          maybe_decay_array = not (quoted and suffix_op.op_id == Id.VOp3_At)
        else:
          raise AssertionError()

      else:
        # TODO: maybe_decay_array for "${!assoc[@]}" vs. ${!assoc[*]}
        val = self._ApplyPrefixOp(val, part.prefix_op, part.token)
        # NOTE: When applying the length operator, we can't have a test or
        # suffix afterward.  And we don't want to decay the array

    elif part.suffix_op:
      op = part.suffix_op
      UP_op = op
      with tagswitch(op) as case:
        if case(suffix_op_e.Nullary):
          op = cast(suffix_op__Nullary, UP_op)
          if op.op_id == Id.VOp0_P:
            prompt = self.prompt_ev.EvalPrompt(val)
            # readline gets rid of these, so we should too.
            p = prompt.replace('\x01', '').replace('\x02', '')
            val = value.Str(p)
          elif op.op_id == Id.VOp0_Q:
            assert val.tag_() == value_e.Str, val
            val = cast(value__Str, val)
            val = value.Str(string_ops.ShellQuote(val.s))
          else:
            raise NotImplementedError(op.op_id)

        elif case(suffix_op_e.Unary):
          op = cast(suffix_op__Unary, UP_op)
          if lookup.LookupKind(op.op_id) == Kind.VTest:
            # TODO: Change style to:
            # if self._ApplyTestOp(...)
            #   return
            # It should return whether anything was done.  If not, we continue to
            # the end, where we might throw an error.

            effect_part_vals, effect = self._ApplyTestOp(val, op, quoted, part_vals)

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
            val = self._ApplyUnarySuffixOp(val, op)

        elif case(suffix_op_e.PatSub):  # PatSub, vectorized
          op = cast(suffix_op__PatSub, UP_op)
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
          if len(warnings):
            # TODO:
            # - Add 'set -o strict-glob' mode and expose warnings.
            #   "Glob is not in CANONICAL FORM".
            # - Propagate location info back to the 'op.pat' word.
            pass
          replacer = string_ops.GlobReplacer(regex, replace_str, op.spids[0])

          UP_val = val
          with tagswitch(val) as case2:
            if case2(value_e.Str):
              val = cast(value__Str, UP_val)
              s = replacer.Replace(val.s, op)
              val = value.Str(s)

            elif case2(value_e.MaybeStrArray):
              val = cast(value__MaybeStrArray, UP_val)
              strs = []  # type: List[str]
              for s in val.strs:
                if s is not None:
                  strs.append(replacer.Replace(s, op))
              val = value.MaybeStrArray(strs)

            elif case2(value_e.AssocArray):
              val = cast(value__AssocArray, UP_val)
              strs = []
              for s in val.d.itervalues():
                strs.append(replacer.Replace(s, op))
              val = value.MaybeStrArray(strs)

            else:
              raise AssertionError(val.tag_())

        elif case(suffix_op_e.Slice):
          op = cast(suffix_op__Slice, UP_op)
          val = self._EmptyStrOrError(val)  # ${undef:3:1}

          if op.begin:
            begin = self.arith_ev.EvalToInt(op.begin)
          else:
            begin = 0

          if op.length:
            length = self.arith_ev.EvalToInt(op.length)
          else:
            length = None

          try:
            val = _PerformSlice(val, begin, length, part)
          except (error.InvalidSlice, error.InvalidUtf8) as e:
            if self.exec_opts.strict_word_eval:
              raise
            else:
              self.errfmt.PrettyPrintError(e, prefix='warning: ')
              with tagswitch(val) as case2:
                if case2(value_e.Str):
                  val = value.Str('')
                elif case2(value_e.MaybeStrArray):
                  val = value.MaybeStrArray([])
                else:
                  raise NotImplementedError()

    # After applying suffixes, process maybe_decay_array here.
    UP_val = val
    if val.tag_() == value_e.MaybeStrArray:
      val = cast(value__MaybeStrArray, UP_val)
      if maybe_decay_array:
        val = self._DecayArray(val)
      elif bash_array_compat:
        val = self._BashArrayCompat(val)

    # For the case where there are no prefix or suffix ops.
    val = self._EmptyStrOrError(val)

    # For example, ${a} evaluates to value.Str(), but we want a
    # part_value.String().
    part_val = _ValueToPartValue(val, quoted)
    part_vals.append(part_val)

  def _PartValsToString(self, part_vals, span_id):
    # type: (List[part_value_t], int) -> str
    strs = []  # type: List[str]
    for part_val in part_vals:
      UP_part_val = part_val
      with tagswitch(part_val) as case:
        if case(part_value_e.String):
          part_val = cast(part_value__String, UP_part_val)
          s = part_val.s

        elif case(part_value_e.Array):
          part_val = cast(part_value__Array, UP_part_val)
          if self.exec_opts.strict_array:
            # Examples: echo f > "$@"; local foo="$@"
            e_die("Illegal array word part (strict_array)",
                  span_id=span_id)
          else:
            # It appears to not respect IFS
            # TODO: eliminate double join()?
            tmp = [s for s in part_val.strs if s is not None]
            s = ' '.join(tmp)

      strs.append(s)

    return ''.join(strs)

  def EvalBracedVarSubToString(self, part):
    # type: (braced_var_sub) -> str
    """For double quoted strings in Oil expressions.

    Example: var x = "$foo-${foo}"
    """
    part_vals = [] # type: List[part_value_t]
    self._EvalBracedVarSub(part, part_vals, False)
    # blame ${ location
    return self._PartValsToString(part_vals, part.spids[0])

  def _EvalSimpleVarSub(self, token, part_vals, quoted):
    # type: (Token, List[part_value_t], bool) -> None
    maybe_decay_array = False
    bash_array_compat = False

    # 1. Evaluate from (var_name, var_num, Token) -> defined, value
    if token.id == Id.VSub_DollarName:
      var_name = token.val[1:]

      # TODO: Special case for LINENO
      val = self.mem.GetVar(var_name)
      if val.tag_() in (value_e.MaybeStrArray, value_e.AssocArray):
        if var_name == _STRING_AND_ARRAY:
          bash_array_compat = True
        else:
          e_die("Array %r can't be referred to as a scalar (without @ or *)",
                var_name, token=token)

    elif token.id == Id.VSub_Number:
      var_num = int(token.val[1:])
      val = self._EvalVarNum(var_num)
    else:
      val, maybe_decay_array = self._EvalSpecialVar(token.id, quoted)

    #log('SIMPLE %s', part)
    val = self._EmptyStrOrError(val, token=token)
    UP_val = val
    if val.tag_() == value_e.MaybeStrArray:
      val = cast(value__MaybeStrArray, UP_val)
      if maybe_decay_array:
        val = self._DecayArray(val)
      elif bash_array_compat:
        val = self._BashArrayCompat(val)

    v = _ValueToPartValue(val, quoted)
    part_vals.append(v)

  def EvalSimpleVarSubToString(self, tok):
    # type: (Token) -> str
    """For double quoted strings in Oil expressions.

    Example: var x = "$foo-${foo}"
    """
    part_vals = []  # type: List[part_value_t]
    self._EvalSimpleVarSub(tok, part_vals, False)
    return self._PartValsToString(part_vals, tok.span_id)

  def _EvalWordPart(self, part, part_vals, quoted=False, is_subst=False):
    # type: (word_part_t, List[part_value_t], bool, bool) -> None
    """Evaluate a word part.

    Args:
      part_vals: Output parameter.

    Returns:
      None
    """
    UP_part = part
    with tagswitch(part) as case:
      if case(word_part_e.ShArrayLiteral):
        part = cast(sh_array_literal, UP_part)
        e_die("Unexpected array literal", part=part)
      elif case(word_part_e.AssocArrayLiteral):
        part = cast(word_part__AssocArrayLiteral, UP_part)
        e_die("Unexpected associative array literal", part=part)

      elif case(word_part_e.Literal):
        part = cast(Token, UP_part)
        # Split if it's in a substitution.
        # That is: echo is not split, but ${foo:-echo} is split
        v = part_value.String(part.val, quoted, is_subst)
        part_vals.append(v)

      elif case(word_part_e.EscapedLiteral):
        part = cast(word_part__EscapedLiteral, UP_part)
        tval = part.token.val
        assert len(tval) == 2, tval  # e.g. \*
        assert tval[0] == '\\'
        s = tval[1]
        v = part_value.String(s, True, False)
        part_vals.append(v)

      elif case(word_part_e.SingleQuoted):
        part = cast(single_quoted, UP_part)
        s = EvalSingleQuoted(part)
        v = part_value.String(s, True, False)
        part_vals.append(v)

      elif case(word_part_e.DoubleQuoted):
        part = cast(double_quoted, UP_part)
        self._EvalDoubleQuoted(part.parts, part_vals)

      elif case(word_part_e.CommandSub):
        part = cast(command_sub, UP_part)
        id_ = part.left_token.id
        if id_ in (Id.Left_DollarParen, Id.Left_Backtick):
          sv = self._EvalCommandSub(part.command_list, quoted) # type: part_value_t

        elif id_ in (Id.Left_ProcSubIn, Id.Left_ProcSubOut):
          sv = self._EvalProcessSub(part.command_list, id_)

        else:
          raise AssertionError(id_)

        part_vals.append(sv)

      elif case(word_part_e.SimpleVarSub):
        part = cast(simple_var_sub, UP_part)
        self._EvalSimpleVarSub(part.token, part_vals, quoted)

      elif case(word_part_e.BracedVarSub):
        part = cast(braced_var_sub, UP_part)
        self._EvalBracedVarSub(part, part_vals, quoted)

      elif case(word_part_e.TildeSub):
        part = cast(word_part__TildeSub, UP_part)
        # We never parse a quoted string into a TildeSub.
        assert not quoted
        s = self._EvalTildeSub(part.token)
        v = part_value.String(s, True, False)  # NOT split even when unquoted!
        part_vals.append(v)

      elif case(word_part_e.ArithSub):
        part = cast(word_part__ArithSub, UP_part)
        num = self.arith_ev.EvalToInt(part.anode)
        v = part_value.String(str(num), quoted, not quoted)
        part_vals.append(v)

      elif case(word_part_e.ExtGlob):
        part = cast(word_part__ExtGlob, UP_part)
        # Do NOT split these.
        part_vals.append(part_value.String(part.op.val, False, False))
        for i, w in enumerate(part.arms):
          if i != 0:
            part_vals.append(part_value.String('|', False, False))  # separator
          # This flattens the tree!
          self._EvalWordToParts(w, False, part_vals)  # eval like not quoted?
        part_vals.append(part_value.String(')', False, False))  # closing )

      elif case(word_part_e.Splice):
        part = cast(word_part__Splice, UP_part)
        var_name = part.name.val[1:]
        val = self.mem.GetVar(var_name)

        UP_val = val
        with tagswitch(val) as case2:
          if case2(value_e.MaybeStrArray):
            val = cast(value__MaybeStrArray, UP_val)
            items = val.strs
          elif case2(value_e.AssocArray):
            val = cast(value__AssocArray, UP_val)
            items = val.d.keys()

          # TODO: Get rid of this case!  Need to DEFER a lot of oil spec
          # tests though.
          elif case2(value_e.Obj):
            if mylib.PYTHON:
              val = cast(value__Obj, UP_val)
              items = [str(item) for item in val.obj]
            else:
              raise AssertionError()

          else:
            e_die("Can't splice %r", var_name, part=part)

        part_vals.append(part_value.Array(items))

      elif case(word_part_e.FuncCall):
        part = cast(word_part__FuncCall, UP_part)
        if mylib.PYTHON:
          func_name = part.name.val[1:]

          fn_val = self.mem.GetVar(func_name) # type: value_t
          if fn_val.tag != value_e.Obj:
            e_die("Expected function named %r, got %r ", func_name, fn_val)
          assert isinstance(fn_val, value__Obj)

          func = fn_val.obj
          pos_args, named_args = self.expr_ev.EvalArgList(part.args)

          id_ = part.name.id
          if id_ == Id.VSub_DollarName:
            s = str(func(*pos_args, **named_args))
            part_val = part_value.String(s) # type: part_value_t

          elif id_ == Id.Lit_Splice:
            # NOTE: Using iterable protocol as with @array.  TODO: Optimize this so
            # it doesn't make a copy?
            a = [str(item) for item in func(*pos_args, **named_args)]
            part_val = part_value.Array(a)

          else:
            raise AssertionError(id_)

          part_vals.append(part_val)

      elif case(word_part_e.ExprSub):
        if mylib.PYTHON:
          part = cast(word_part__ExprSub, UP_part)
          py_val = self.expr_ev.EvalExpr(part.child)
          part_val = part_value.String(str(py_val))
          part_vals.append(part_val)

      else:
        raise AssertionError(part.tag_())

  def _EvalWordToParts(self, w, quoted, part_vals, is_subst=False):
    # type: (word_t, bool, List[part_value_t], bool) -> None
    """Helper for EvalRhsWord, EvalWordSequence, etc.

    Returns:
      List of part_value.
      But note that this is a TREE.
    """
    UP_w = w
    with tagswitch(w) as case:
      if case(word_e.Compound):
        w = cast(compound_word, UP_w)
        for p in w.parts:
          self._EvalWordPart(p, part_vals, quoted=quoted, is_subst=is_subst)

      elif case(word_e.Empty):
        part_vals.append(part_value.String('', quoted, not quoted))

      else:
        raise AssertionError(w.tag_())

  def EvalWordToString(self, UP_w, do_fnmatch=False, do_ere=False):
    # type: (word_t, bool, bool) -> value__Str
    """
    Args:
      w: Compound

    Used for redirect arg, ControlFlow arg, ArithWord, BoolWord, etc.

    do_fnmatch is true for case $pat and RHS of [[ == ]].

    pat="*.py"
    case $x in
      $pat) echo 'matches glob pattern' ;;
      "$pat") echo 'equal to glob string' ;;  # must be glob escaped
    esac

    TODO: Raise AssertionError if it has ExtGlob.
    """
    if UP_w.tag_() == word_e.Empty:
      return value.Str('')

    assert UP_w.tag_() == word_e.Compound, UP_w
    w = cast(compound_word, UP_w)

    part_vals = []  # type: List[part_value_t]
    for p in w.parts:
      self._EvalWordPart(p, part_vals, quoted=False)

    strs = []  # type: List[str]
    for part_val in part_vals:
      UP_part_val = part_val
      with tagswitch(part_val) as case:
        if case(part_value_e.String):
          part_val = cast(part_value__String, UP_part_val)
          # [[ foo == */"*".py ]] or case *.py) ... esac
          if do_fnmatch and part_val.quoted:
            s = glob_.GlobEscape(part_val.s)
          elif do_ere and part_val.quoted:
            s = glob_.ExtendedRegexEscape(part_val.s)
          else:
            s = part_val.s

        elif case(part_value_e.Array):
          part_val = cast(part_value__Array, UP_part_val)
          if self.exec_opts.strict_array:
            # Examples: echo f > "$@"; local foo="$@"

            # TODO: This attributes too coarsely, to the word rather than the
            # parts.  Problem: the word is a TREE of parts, but we only have a
            # flat list of part_vals.  The only case where we really get arrays
            # is "$@", "${a[@]}", "${a[@]//pat/replace}", etc.
            e_die("This word should yield a string, but it contains an array",
                  word=w)

            # TODO: Maybe add detail like this.
            #e_die('RHS of assignment should only have strings.  '
            #      'To assign arrays, use b=( "${a[@]}" )')
          else:
            # It appears to not respect IFS
            tmp = [s for s in part_val.strs if s is not None]
            s = ' '.join(tmp)  # TODO: eliminate double join()?

      strs.append(s)

    #log('EvalWordToString %s', w.parts)
    return value.Str(''.join(strs))

  def EvalForPlugin(self, w):
    # type: (compound_word) -> value__Str
    """Wrapper around EvalWordToString that prevents errors.
    
    Runtime errors like $(( 1 / 0 )) and mutating $? like $(exit 42) are
    handled here.
    """
    self.mem.PushStatusFrame()  # to "sandbox" $? and $PIPESTATUS
    try:
      val = self.EvalWordToString(w)
    except error.FatalRuntime as e:
      val = value.Str('<Runtime error: %s>' % e.UserErrorString())
    except (OSError, IOError) as e:
      # This is like the catch-all in Executor.ExecuteAndCatch().
      val = value.Str('<I/O error: %s>' % posix.strerror(e.errno))
    except KeyboardInterrupt:
      val = value.Str('<Ctrl-C>')
    finally:
      self.mem.PopStatusFrame()
    return val

  def EvalRhsWord(self, UP_w):
    # type: (word_t) -> value_t
    """Used for RHS of assignment.  There is no splitting.
    """
    if UP_w.tag_() == word_e.Empty:
      return value.Str('')

    assert UP_w.tag_() == word_e.Compound, UP_w
    w = cast(compound_word, UP_w)

    if len(w.parts) == 1:
      part0 = w.parts[0]
      UP_part0 = part0
      tag = part0.tag_()
      # Special case for a=(1 2).  ShArrayLiteral won't appear in words that
      # don't look like assignments.
      if tag == word_part_e.ShArrayLiteral:
        part0 = cast(sh_array_literal, UP_part0)
        array_words = part0.words
        words = braces.BraceExpandWords(array_words)
        strs = self.EvalWordSequence(words)
        #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
        return value.MaybeStrArray(strs)

      if tag == word_part_e.AssocArrayLiteral:
        part0 = cast(word_part__AssocArrayLiteral, UP_part0)
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
    return self.EvalWordToString(w)

  def _EvalWordFrame(self, frame, argv):
    # type: (List[Tuple[str, bool, bool]], List[str]) -> None
    all_empty = True
    all_quoted = True
    any_quoted = False

    #log('--- frame %s', frame)

    for s, quoted, _ in frame:
      if len(s):
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
      tmp = [s for s, _, _ in frame]
      a = ''.join(tmp)
      argv.append(a)
      return

    will_glob = not self.exec_opts.noglob

    # Array of strings, some of which are BOTH IFS-escaped and GLOB escaped!
    frags = []  # type: List[str]
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
    # type: (compound_word) -> List[str]
    """Helper for _EvalAssignBuiltin.

    Splitting and globbing are disabled for assignment builtins.

    Example: declare -"${a[@]}" b=(1 2)
    where a is [x b=a d=a]
    """
    part_vals = []  # type: List[part_value_t]
    self._EvalWordToParts(w, False, part_vals)  # not double quoted
    frames = _MakeWordFrames(part_vals)
    argv = []  # type: List[str]
    for frame in frames:
      if len(frame):  # empty array gives empty frame!
        tmp = [s for (s, _, _) in frame]
        argv.append(''.join(tmp))  # no split or glob
    #log('argv: %s', argv)
    return argv

  def _EvalAssignBuiltin(self, builtin_id, arg0, words):
    # type: (builtin_t, str, List[compound_word]) -> cmd_value__Assign
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

    started_pairs = False

    flags = [arg0]
    flag_spids = [word_.LeftMostSpanForWord(words[0])]
    assign_args = []  # type: List[assign_arg]

    n = len(words)
    for i in xrange(1, n):  # skip first word
      w = words[i]
      word_spid = word_.LeftMostSpanForWord(w)

      if word_.IsVarLike(w):
        started_pairs = True  # Everything from now on is an assign_pair

      if started_pairs:
        left_token, close_token, part_offset = word_.DetectShAssignment(w)
        if left_token:  # Detected statically
          if left_token.id != Id.Lit_VarLike:
            # (not guaranteed since started_pairs is set twice)
            e_die('LHS array not allowed in assignment builtin', word=w)
          tok_val = left_token.val
          if tok_val[-2] == '+':
            e_die('+= not allowed in assignment builtin', word=w)

          left = lvalue.Named(tok_val[:-1])
          if part_offset == len(w.parts):
            rhs_word = word.Empty()  # type: word_t
          else:
            rhs_word = compound_word(w.parts[part_offset:])
            # tilde detection only happens on static assignments!
            tmp = word_.TildeDetect(rhs_word) 
            if tmp:
              rhs_word = tmp

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

  def StaticEvalWordSequence2(self, words, allow_assign):
    # type: (List[compound_word], bool) -> cmd_value_t
    """Static word evaluation for Oil."""
    #log('W %s', words)
    strs = []  # type: List[str]
    spids = []  # type: List[int]

    n = 0
    for i, w in enumerate(words):
      word_spid = word_.LeftMostSpanForWord(w)

      # No globbing in the first arg!  That seems like a feature, not a bug.
      if i == 0:
        strs0 = self._EvalWordToArgv(w)  # respects strict-array
        if len(strs0) == 1:
          arg0 = strs0[0]
          builtin_id = builtin.ResolveAssign(arg0)
          if builtin_id != builtin_e.NONE:
            # Same logic as legacy word eval, with no splitting
            return self._EvalAssignBuiltin(builtin_id, arg0, words)

        strs.extend(strs0)
        for _ in strs0:
          spids.append(word_spid)
        continue

      if glob_.LooksLikeStaticGlob(w):
        val = self.EvalWordToString(w)  # respects strict-array
        results = self.globber.Expand(val.s)
        strs.extend(results)
        for _ in results:
          spids.append(word_spid)
        continue

      part_vals = []  # type: List[part_value_t]
      self._EvalWordToParts(w, False, part_vals)  # not double quoted

      if 0:
        log('')
        log('Static: part_vals after _EvalWordToParts:')
        for entry in part_vals:
          log('  %s', entry)

      # Still need to process
      frames = _MakeWordFrames(part_vals)

      if 0:
        log('')
        log('Static: frames after _MakeWordFrames:')
        for entry in frames:
          log('  %s', entry)

      # We will still allow x"${a[@]"x, though it's deprecated by @a, which
      # disallows such expressions at parse time.
      for frame in frames:
        if len(frame):  # empty array gives empty frame!
          tmp = [s for (s, _, _) in frame]
          strs.append(''.join(tmp))  # no split or glob
          spids.append(word_spid)

    return cmd_value.Argv(strs, spids, None)

  def EvalWordSequence2(self, words, allow_assign=False):
    # type: (List[compound_word], bool) -> cmd_value_t
    """Turns a list of Words into a list of strings.

    Unlike the EvalWord*() methods, it does globbing.

    Args:
      words: list of Word instances

    Returns:
      argv: list of string arguments, or None if there was an eval error
    """
    if self.exec_opts.simple_word_eval:
      return self.StaticEvalWordSequence2(words, allow_assign)

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
    strs = []  # type: List[str]
    spids = []  # type: List[int]

    n = 0
    for i, w in enumerate(words):
      part_vals = []  # type: List[part_value_t]
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
        UP_val0 = val0
        if val0.tag_() == part_value_e.String:
          val0 = cast(part_value__String, UP_val0)
          if not val0.quoted:
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
      spid = word_.LeftMostSpanForWord(w)
      for _ in xrange(n_next - n):
        spids.append(spid)
      n = n_next

    # A non-assignment command.
    # NOTE: Can't look up builtins here like we did for assignment, because
    # functions can override builtins.
    return cmd_value.Argv(strs, spids, None)

  def EvalWordSequence(self, words):
    # type: (List[compound_word]) -> List[str]
    """For arrays and for loops.  They don't allow assignment builtins."""
    UP_cmd_val = self.EvalWordSequence2(words)

    assert UP_cmd_val.tag_() == cmd_value_e.Argv
    cmd_val = cast(cmd_value__Argv, UP_cmd_val)
    return cmd_val.argv


def _SplitAssignArg(arg, w):
  # type: (str, compound_word) -> Tuple[lvalue__Named, Optional[value__Str]]
  i = arg.find('=')
  prefix = arg[:i]
  if i != -1 and match.IsValidVarName(prefix):
    return lvalue.Named(prefix), value.Str(arg[i+1:]),
  else:
    if match.IsValidVarName(arg):  # local foo   # foo becomes undefined
      return lvalue.Named(arg), None
    else:
      e_die("Invalid variable name %r", arg, word=w)


class NormalWordEvaluator(_WordEvaluator):

  def __init__(self, mem, exec_opts, exec_deps, arena):
    # type: (Mem, ExecOpts, Deps, Arena) -> None
    _WordEvaluator.__init__(self, mem, exec_opts, exec_deps, arena)
    self.ex = exec_deps.ex

  def _EvalCommandSub(self, node, quoted):
    # type: (command_t, bool) -> part_value__String
    stdout = self.ex.RunCommandSub(node)
    return part_value.String(stdout, quoted, not quoted)

  def _EvalProcessSub(self, node, id_):
    # type: (command_t, Id_t) -> part_value__String
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
    # type: (command_t, bool) -> part_value__String
    return part_value.String('__NO_COMMAND_SUB__', quoted, not quoted)

  def _EvalProcessSub(self, node, id_):
    # type: (command_t, Id_t) -> part_value__String
    # pretend it's quoted; no split or glob
    return part_value.String('__NO_PROCESS_SUB__', True, False)
