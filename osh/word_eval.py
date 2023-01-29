"""
word_eval.py - Evaluator for the word language.
"""

from _devbuild.gen.id_kind_asdl import Id, Kind, Kind_str
from _devbuild.gen.syntax_asdl import (
    Token, loc,
    braced_var_sub, command_sub,
    bracket_op_e, bracket_op__ArrayIndex, bracket_op__WholeArray,
    suffix_op_e, suffix_op__PatSub, suffix_op__Slice,
    suffix_op__Unary, suffix_op__Static,
    sh_array_literal, single_quoted, double_quoted, simple_var_sub,
    word_e, word_t, compound_word,
    rhs_word, rhs_word_e, rhs_word_t,
    word_part_e, word_part__ArithSub, word_part__EscapedLiteral,
    word_part__AssocArrayLiteral, word_part__ExprSub, word_part__ExtGlob,
    word_part__FuncCall, word_part__Splice, word_part__TildeSub,
)
from _devbuild.gen.runtime_asdl import (
    part_value, part_value_e, part_value_t, part_value__String,
    part_value__Array, part_value__ExtGlob,
    value, value_e, value_t, value__Str, value__AssocArray,
    value__MaybeStrArray, value__Obj,
    lvalue, lvalue_t,
    assign_arg, 
    cmd_value_e, cmd_value_t, cmd_value, cmd_value__Assign, cmd_value__Argv,
    a_index, a_index_e, a_index__Int, a_index__Str,
    VTestPlace, VarSubState,
)
from core import error
from core import pyos
from core import pyutil
from core import state
from core import ui
from qsn_ import qsn
from core.pyerror import log, e_die
from frontend import consts
from mycpp.mylib import tagswitch, NewDict
from mycpp import mylib
from osh import braces
from osh import glob_
from osh import string_ops
from osh import word_
from osh import word_compile

import libc

from typing import Optional, Tuple, List, Dict, cast, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import word_part_t
  from _devbuild.gen.option_asdl import builtin_t
  from core import optview
  from core.state import Mem
  from core.ui import ErrorFormatter
  from core.vm import _Executor
  from osh.split import SplitContext
  from osh import prompt
  from osh import sh_expr_eval
  from oil_lang import expr_eval


# Flags for _EvalWordToParts and _EvalWordPart (not all are used for both)
QUOTED = 1 << 0
IS_SUBST = 1 << 1

EXTGLOB_FILES = 1 << 2  # allow @(cc) from file system?
EXTGLOB_MATCH = 1 << 3  # allow @(cc) in pattern matching?
EXTGLOB_NESTED = 1 << 4  # for @(one|!(two|three))

# For EvalWordToString
QUOTE_FNMATCH = 1 << 5
QUOTE_ERE = 1 << 6

# For compatibility, ${BASH_SOURCE} and ${BASH_SOURCE[@]} are both valid.
# Ditto for ${FUNCNAME} and ${BASH_LINENO}.
_STRING_AND_ARRAY = ['BASH_SOURCE', 'FUNCNAME', 'BASH_LINENO']

def ShouldArrayDecay(var_name, exec_opts, is_plain_var_sub=True):
  # type: (str, optview.Exec, bool) -> bool
  """Return whether we should allow ${a} to mean ${a[0]}."""
  return (
      exec_opts.compat_array() or
      is_plain_var_sub and var_name in _STRING_AND_ARRAY
  )


def DecayArray(val):
  # type: (value_t) -> value_t
  """Resolve ${array} to ${array[0]}."""
  if val.tag_() == value_e.MaybeStrArray:
    array_val = cast(value__MaybeStrArray, val)
    s = array_val.strs[0] if len(array_val.strs) else None
  elif val.tag_() == value_e.AssocArray:
    assoc_val = cast(value__AssocArray, val)
    s = assoc_val.d['0'] if '0' in assoc_val.d else None
  else:
    raise AssertionError(val.tag_())

  if s is None:
    return value.Undef()
  else:
    return value.Str(s)


def GetArrayItem(strs, index):
  # type: (List[str], int) -> Optional[str]

  n = len(strs)
  if index < 0:
    index += n

  if 0 <= index and index < n:
    # TODO: strs->index() has a redundant check for (i < 0)
    s = strs[index]
    # note: s could be None because representation is sparse
  else:
    s = None
  return s


# Use libc to parse NAME, NAME=value, and NAME+=value.  We want submatch
# extraction, but I haven't used that in re2c, and we would need a new kind of
# binding.
#
ASSIGN_ARG_RE = '^([a-zA-Z_][a-zA-Z0-9_]*)((=|\+=)(.*))?$'

# Eggex equivalent:
#
# VarName = /
#   [a-z A-Z _ ]
#   [a-z A-Z 0-9 _ ]*
# /
#
# SplitArg = /
#   %begin
#   < VarName >
#   < < '=' | '+=' > < dot* > > ?
#   %end
# /
# Note: must use < > for grouping because there is no non-capturing group.

def _SplitAssignArg(arg, word_spid):
  # type: (str, int) -> assign_arg
  """Dynamically parse argument to declare, export, etc.

  This is a fallback to the static parsing done below.
  """
  # Note: it would be better to cache regcomp(), but we don't have an API for
  # that, and it probably isn't a bottleneck now
  m = libc.regex_match(ASSIGN_ARG_RE, arg)
  if m is None:
    e_die("Assignment builtin expected NAME=value, got %r" % arg,
          loc.Span(word_spid))

  var_name = m[1]
  # m[2] is used for grouping; ERE doesn't have non-capturing groups

  op = m[3]
  if len(op):  # declare NAME=
    val = value.Str(m[4])  # type: Optional[value_t]
    append = op[0] == '+'
  else:  # declare NAME
    val = None  # no operator
    append = False

  #log('ret %s', assign_arg(left, right, append, word_spid))
  return assign_arg(var_name, val, append, word_spid)


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
    if case(value_e.Undef):
      # This happens in the case of ${undef+foo}.  We skipped _EmptyStrOrError,
      # but we have to append to the empty string.
      return part_value.String('', quoted, not quoted)

    elif case(value_e.Str):
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
        from oil_lang import expr_eval
        s = expr_eval.Stringify(val.obj)
        return part_value.String(s, quoted, not quoted)
      # Not in C++
      raise AssertionError()

    else:
      # Undef should be caught by _EmptyStrOrError().
      raise AssertionError(val.tag_())

  raise AssertionError('for -Wreturn-type in C++')


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

    # This word
    $x"${a[@]}"$y

    # Results in Three frames:
    [ ('x', False, True), ('1', True, False) ]
    [ ('2 3', True, False) ]
    [ ('4', True, False), ('y', False, True) ]

  Note: A frame is a 3-tuple that's identical to part_value.String()?  Maybe we
  should make that top level type.
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


# TODO: This could be _MakeWordFrames and then sep.join().  It's redundant.
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
      elif case(part_value_e.Array):
        p = cast(part_value__Array, UP_p)
        # TODO: Eliminate double join for speed?
        tmp = [s for s in p.strs if s is not None]
        out.append(join_char.join(tmp))
      else:
        raise AssertionError()
  return ''.join(out)


def _PerformSlice(val,  # type: value_t
                  begin,  # type: int
                  length,  # type: int
                  has_length,  # type: bool
                  part,  # type: braced_var_sub
                  arg0_val, # type: value__Str
                  ):
  # type: (...) -> value_t
  UP_val = val
  with tagswitch(val) as case:
    if case(value_e.Str):  # Slice UTF-8 characters in a string.
      val = cast(value__Str, UP_val)
      s = val.s
      n = len(s)

      if begin < 0:  # Compute offset with unicode
        byte_begin = n
        num_iters = -begin
        for _ in xrange(num_iters):
          byte_begin = string_ops.PreviousUtf8Char(s, byte_begin)
      else:
        byte_begin = string_ops.AdvanceUtf8Chars(s, begin, 0)

      if has_length:
        if length < 0:  # Compute offset with unicode
          # Confusing: this is a POSITION
          byte_end = n
          num_iters = -length
          for _ in xrange(num_iters):
            byte_end = string_ops.PreviousUtf8Char(s, byte_end)
        else:
          byte_end = string_ops.AdvanceUtf8Chars(s, length, byte_begin)
      else:
        byte_end = len(s)

      substr = s[byte_begin : byte_end]
      result = value.Str(substr)  # type: value_t

    elif case(value_e.MaybeStrArray):  # Slice array entries.
      val = cast(value__MaybeStrArray, UP_val)
      # NOTE: This error is ALWAYS fatal in bash.  It's inconsistent with
      # strings.
      if has_length and length < 0:
        e_die("The length index of a array slice can't be negative: %d" %
              length, loc.WordPart(part))

      # Quirk: "begin" for positional arguments ($@ and $*) counts $0.
      if arg0_val is not None:
        orig = [arg0_val.s]
        orig.extend(val.strs)
      else:
        orig = val.strs

      n = len(orig)
      if begin < 0:
        i = n + begin  # ${@:-3} starts counts from the end
      else:
        i = begin
      strs = []  # type: List[str]
      count = 0
      while i < n:
        if has_length and count == length:  # length could be 0
          break
        s = orig[i]
        if s is not None:  # Unset elements don't count towards the length
          strs.append(s)
          count += 1
        i += 1
       
      result = value.MaybeStrArray(strs)

    elif case(value_e.AssocArray):
      e_die("Can't slice associative arrays", loc.WordPart(part))

    else:
      raise NotImplementedError(val.tag_())

  return result


class StringWordEvaluator(object):
  """For use by the _ExprEvaluator."""

  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    pass

  def EvalWordToString(self, w, eval_flags=0):
    # type: (word_t, int) -> value__Str
    raise NotImplementedError()


def _GetDollarHyphen(exec_opts):
  # type: (optview.Exec) -> str
  chars = []  # type: List[str]
  if exec_opts.interactive():
    chars.append('i')

  if exec_opts.errexit():
    chars.append('e')
  if exec_opts.noglob():
    chars.append('f')
  if exec_opts.noexec():
    chars.append('n')
  if exec_opts.nounset():
    chars.append('u')
  # NO letter for pipefail?
  if exec_opts.xtrace():
    chars.append('x')
  if exec_opts.noclobber():
    chars.append('C')

  # bash has:
  # - c for sh -c, i for sh -i (mksh also has this)
  # - h for hashing (mksh also has this)
  # - B for brace expansion
  return ''.join(chars)


class TildeEvaluator(object):

  def __init__(self, mem, exec_opts):
    # type: (Mem, optview.Exec) -> None
    self.mem = mem
    self.exec_opts = exec_opts

  def Eval(self, token):
    # type: (Token) -> str
    """Evaluates ~ and ~user, given a Lit_TildeLike token"""
    if token.val == '~':
      # First look up the HOME var, then ask the OS.  This is what bash does.
      val = self.mem.GetValue('HOME')
      UP_val = val
      if val.tag_() == value_e.Str:
        val = cast(value__Str, UP_val)
        return val.s
      result = pyos.GetMyHomeDir()
    else:
      result = pyos.GetHomeDir(token.val[1:])

    if result is None:
      if self.exec_opts.strict_tilde():
        e_die("Error expanding tilde (e.g. invalid user)", token)
      else:
        return token.val  # Return ~ or ~user literally

    return result


class AbstractWordEvaluator(StringWordEvaluator):
  """Abstract base class for word evaluators.

  Public entry points:
    EvalWordToString
    EvalForPlugin
    EvalRhsWord
    EvalWordSequence
    EvalWordSequence2
  """
  def __init__(self, mem, exec_opts, mutable_opts, splitter, errfmt):
    # type: (Mem, optview.Exec, state.MutableOpts, SplitContext, ErrorFormatter) -> None
    self.arith_ev = None  # type: sh_expr_eval.ArithEvaluator
    self.expr_ev = None  # type: expr_eval.OilEvaluator
    self.prompt_ev = None  # type: prompt.Evaluator

    self.unsafe_arith = None  # type: sh_expr_eval.UnsafeArith

    self.tilde_ev = TildeEvaluator(mem, exec_opts)

    self.mem = mem  # for $HOME, $1, etc.
    self.exec_opts = exec_opts  # for nounset
    self.mutable_opts = mutable_opts  # for allow_csub_psub
    self.splitter = splitter
    self.errfmt = errfmt

    self.globber = glob_.Globber(exec_opts)

  def CheckCircularDeps(self):
    # type: () -> None
    raise NotImplementedError()

  def _EvalCommandSub(self, cs_part, quoted):
    # type: (command_sub, bool) -> part_value_t
    """Abstract since it has a side effect.

    Args:
      part: command_sub

    Returns:
       part_value
    """
    raise NotImplementedError()

  def _EvalProcessSub(self, cs_part):
    # type: (command_sub) -> part_value_t
    """Abstract since it has a side effect.

    Args:
      part: command_sub

    Returns:
       part_value
    """
    raise NotImplementedError()

  def _EvalVarNum(self, var_num):
    # type: (int) -> value_t
    assert var_num >= 0
    return self.mem.GetArgNum(var_num)

  def _EvalSpecialVar(self, op_id, quoted, vsub_state):
    # type: (int, bool, VarSubState) -> value_t
    """Evaluate $? and so forth"""
    # $@ is special -- it need to know whether it is in a double quoted
    # context.
    #
    # - If it's $@ in a double quoted context, return an ARRAY.
    # - If it's $@ in a normal context, return a STRING, which then will be
    # subject to splitting.

    if op_id in (Id.VSub_At, Id.VSub_Star):
      argv = self.mem.GetArgv()
      val = value.MaybeStrArray(argv)  # type: value_t
      if op_id == Id.VSub_At:
        # "$@" evaluates to an array, $@ should be decayed
        vsub_state.join_array = not quoted
      else:  # $* "$*" are both decayed
        vsub_state.join_array = True

    elif op_id == Id.VSub_Hyphen:
      val = value.Str(_GetDollarHyphen(self.exec_opts))

    else:
      val = self.mem.GetSpecialVar(op_id)

    return val

  def _ApplyTestOp(self,
                   val,  # type: value_t
                   op,  # type: suffix_op__Unary
                   quoted,  # type: bool
                   part_vals,  # type: Optional[List[part_value_t]]
                   vtest_place,  # type: VTestPlace
                   blame_token,  # type: Token
                   ):
    # type: (...) -> bool
    """
    Returns:
      Whether part_vals was mutated

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
    eval_flags = IS_SUBST
    if quoted:
      eval_flags |= QUOTED

    tok = op.tok
    # NOTE: Splicing part_values is necessary because of code like
    # ${undef:-'a b' c 'd # e'}.  Each part_value can have a different
    # do_glob/do_elide setting.
    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.Undef):
        is_falsey = True
      elif case(value_e.Str):
        val = cast(value__Str, UP_val)
        if tok.id in (Id.VTest_ColonHyphen, Id.VTest_ColonEquals,
                      Id.VTest_ColonQMark, Id.VTest_ColonPlus):
          is_falsey = len(val.s) == 0
        else:
          is_falsey = False
      elif case(value_e.MaybeStrArray):
        val = cast(value__MaybeStrArray, UP_val)
        is_falsey = len(val.strs) == 0
      elif case(value_e.AssocArray):
        val = cast(value__AssocArray, UP_val)
        is_falsey = len(val.d) == 0
      else:
        raise NotImplementedError(val.tag_())

    if tok.id in (Id.VTest_ColonHyphen, Id.VTest_Hyphen):
      if is_falsey:
        self._EvalRhsWordToParts(op.arg_word, part_vals, eval_flags)
        return True
      else:
        return False

    # Inverse of the above.
    elif tok.id in (Id.VTest_ColonPlus, Id.VTest_Plus):
      if is_falsey:
        return False
      else:
        self._EvalRhsWordToParts(op.arg_word, part_vals, eval_flags)
        return True

    # Splice and assign
    elif tok.id in (Id.VTest_ColonEquals, Id.VTest_Equals):
      if is_falsey:
        # Collect new part vals.
        assign_part_vals = []  # type: List[part_value_t]
        self._EvalRhsWordToParts(op.arg_word, assign_part_vals, eval_flags)
        # Append them to out param AND return them.
        part_vals.extend(assign_part_vals)

        if vtest_place.name is None:
          # TODO: error context
          e_die("Can't assign to special variable")
        else:
          # NOTE: This decays arrays too!  'shopt -s strict_array' could
          # avoid it.
          rhs_str = _DecayPartValuesToString(assign_part_vals,
                                             self.splitter.GetJoinChar())
          if vtest_place.index is None:  # using None when no index
            lval = lvalue.Named(vtest_place.name)  # type: lvalue_t
          else:
            var_name = vtest_place.name
            var_index = vtest_place.index
            UP_var_index = var_index

            with tagswitch(var_index) as case:
              if case(a_index_e.Int):
                var_index = cast(a_index__Int, UP_var_index)
                lval = lvalue.Indexed(var_name, var_index.i)
              elif case(a_index_e.Str):
                var_index = cast(a_index__Str, UP_var_index)
                lval = lvalue.Keyed(var_name, var_index.s)
              else: 
                raise AssertionError()

          state.OshLanguageSetValue(self.mem, lval, value.Str(rhs_str))
        return True

      else:
        return False

    elif tok.id in (Id.VTest_ColonQMark, Id.VTest_QMark):
      if is_falsey:
        # The arg is the error mesage
        error_part_vals = []  # type: List[part_value_t]
        self._EvalRhsWordToParts(op.arg_word, error_part_vals, eval_flags)
        error_str = _DecayPartValuesToString(error_part_vals,
                                             self.splitter.GetJoinChar())
        e_die("unset variable %r" % error_str, blame_token)

      else:
        return False

    else:
      raise NotImplementedError(tok.id)

  def _Length(self, val, token):
    # type: (value_t, Token) -> value_t
    """Returns the length of the value, for ${#var}"""
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
        except error.Strict as e:
          # Add this here so we don't have to add it so far down the stack.
          # TODO: It's better to show BOTH this CODE an the actual DATA
          # somehow.
          e.location = token

          if self.exec_opts.strict_word_eval():
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

  def _Keys(self, val, token):
    # type: (value_t, Token) -> value_t
    """Return keys of a container, for ${!array[@]}"""

    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.MaybeStrArray):
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

        # BUG: Keys aren't ordered according to insertion!
        return value.MaybeStrArray(val.d.keys())

      else:
        raise AssertionError()

  def _EvalVarRef(self, val, token, quoted, vsub_state, vtest_place):
    # type: (value_t, Token, bool, VarSubState, VTestPlace) -> value_t
    """Handles indirect expansion like ${!var} and ${!a[0]}."""
    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.Undef):
        return value.Undef()  # ${!undef} is just weird bash behavior

      elif case(value_e.Str):
        val = cast(value__Str, UP_val)
        bvs_part = self.unsafe_arith.ParseVarRef(val.s, token)
        if not self.exec_opts.eval_unsafe_arith() and bvs_part.bracket_op:
          e_die('a[i] not allowed without shopt -s eval_unsafe_arith', token)
        return self._VarRefValue(bvs_part, quoted, vsub_state, vtest_place)

      elif case(value_e.MaybeStrArray):  # caught earlier but OK
        e_die('Indirect expansion of array')

      elif case(value_e.AssocArray):  # caught earlier but OK
        e_die('Indirect expansion of assoc array')

      else:
        raise NotImplementedError(val.tag_())

  def _ApplyUnarySuffixOp(self, val, op):
    # type: (value_t, suffix_op__Unary) -> value_t
    assert val.tag_() != value_e.Undef

    op_kind = consts.GetKind(op.tok.id)

    if op_kind == Kind.VOp1:
      # NOTE: glob syntax is supported in ^ ^^ , ,, !  As well as % %% # ##.
      # Detect has_extglob so that DoUnarySuffixOp doesn't use the fast
      # shortcut for constant strings.
      arg_val, has_extglob = self.EvalWordToPattern(op.arg_word)
      assert arg_val.tag_() == value_e.Str

      UP_val = val
      with tagswitch(val) as case:
        if case(value_e.Str):
          val = cast(value__Str, UP_val)
          s = string_ops.DoUnarySuffixOp(val.s, op, arg_val.s, has_extglob)
          #log('%r %r -> %r', val.s, arg_val.s, s)
          new_val = value.Str(s) # type: value_t

        elif case(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          # ${a[@]#prefix} is VECTORIZED on arrays.  Oil should have this too.
          strs = []  # type: List[str]
          for s in val.strs:
            if s is not None:
              strs.append(string_ops.DoUnarySuffixOp(s, op, arg_val.s, has_extglob))
          new_val = value.MaybeStrArray(strs)

        elif case(value_e.AssocArray):
          val = cast(value__AssocArray, UP_val)
          strs = []
          for s in val.d.values():
            strs.append(string_ops.DoUnarySuffixOp(s, op, arg_val.s, has_extglob))
          new_val = value.MaybeStrArray(strs)

        else:
          raise AssertionError(val.tag_())

    else:
      raise AssertionError(Kind_str(op_kind))

    return new_val

  def _PatSub(self, val, op):
    # type: (value_t, suffix_op__PatSub) -> value_t

    pat_val, has_extglob = self.EvalWordToPattern(op.pat)
    # Extended globs aren't supported because we only translate * ? etc. to
    # ERE.  I don't think there's a straightforward translation from !(*.py) to
    # ERE!  You would need an engine that supports negation?  (Derivatives?)
    if has_extglob:
      e_die('extended globs not supported in ${x//GLOB/}', loc.Word(op.pat))

    if op.replace:
      replace_val = self.EvalRhsWord(op.replace)
      # Can't have an array, so must be a string
      assert replace_val.tag_() == value_e.Str, replace_val
      replace_str = cast(value__Str, replace_val).s
    else:
      replace_str = ''

    # note: doesn't support self.exec_opts.extglob()!
    regex, warnings = glob_.GlobToERE(pat_val.s)
    if len(warnings):
      # TODO:
      # - Add 'shopt -s strict_glob' mode and expose warnings.
      #   "Glob is not in CANONICAL FORM".
      # - Propagate location info back to the 'op.pat' word.
      pass
    replacer = string_ops.GlobReplacer(regex, replace_str, op.slash_tok)

    with tagswitch(val) as case2:
      if case2(value_e.Str):
        str_val = cast(value__Str, val)
        s = replacer.Replace(str_val.s, op)
        val = value.Str(s)

      elif case2(value_e.MaybeStrArray):
        array_val = cast(value__MaybeStrArray, val)
        strs = []  # type: List[str]
        for s in array_val.strs:
          if s is not None:
            strs.append(replacer.Replace(s, op))
        val = value.MaybeStrArray(strs)

      elif case2(value_e.AssocArray):
        assoc_val = cast(value__AssocArray, val)
        strs = []
        for s in assoc_val.d.values():
          strs.append(replacer.Replace(s, op))
        val = value.MaybeStrArray(strs)

      else:
        raise AssertionError(val.tag_())
    return val

  def _Slice(self, val, op, var_name, part):
    # type: (value_t, suffix_op__Slice, Optional[str], braced_var_sub) -> value_t

    if op.begin:
      begin = self.arith_ev.EvalToInt(op.begin)
    else:
      begin = 0

    # Note: bash allows lengths to be negative (with odd semantics), but
    # we don't allow that right now.
    has_length = False
    length = -1
    if op.length:
      has_length = True
      length = self.arith_ev.EvalToInt(op.length)

    try:
      arg0_val = None  # type: value__Str
      if var_name is None: # $* or $@
        arg0_val = self.mem.GetArg0()
      val = _PerformSlice(val, begin, length, has_length, part, arg0_val)
    except error.Strict as e:
      if self.exec_opts.strict_word_eval():
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
    return val

  def _Nullary(self, val, op, var_name):
    # type: (value_t, Token, Optional[str]) -> Tuple[value__Str, bool]

    UP_val = val
    quoted2 = False
    op_id = op.id
    if op_id == Id.VOp0_P:
      with tagswitch(val) as case:
        if case(value_e.Str):
          str_val = cast(value__Str, UP_val)
          prompt = self.prompt_ev.EvalPrompt(str_val)
          # readline gets rid of these, so we should too.
          p = prompt.replace('\x01', '').replace('\x02', '')
          result = value.Str(p)
        else:
          e_die("Can't use @P on %s" % ui.ValType(val))  # TODO: location

    elif op_id == Id.VOp0_Q:
      with tagswitch(val) as case:
        if case(value_e.Str):
          str_val = cast(value__Str, UP_val)
          result = value.Str(qsn.maybe_shell_encode(str_val.s))
          # oddly, 'echo ${x@Q}' is equivalent to 'echo "${x@Q}"' in bash
          quoted2 = True
        elif case(value_e.MaybeStrArray):
          array_val = cast(value__MaybeStrArray, UP_val)
          tmp = [qsn.maybe_shell_encode(s) for s in array_val.strs]
          result = value.Str(' '.join(tmp))
        else:
          e_die("Can't use @Q on %s" % ui.ValType(val))  # TODO: location

    elif op_id == Id.VOp0_a:
      # We're ONLY simluating -a and -A, not -r -x -n for now.  See
      # spec/ble-idioms.test.sh.
      chars = []  # type: List[str]
      with tagswitch(val) as case:
        if case(value_e.MaybeStrArray):
          chars.append('a')
        elif case(value_e.AssocArray):
          chars.append('A')

      if var_name is not None:  # e.g. ${?@a} is allowed
        cell = self.mem.GetCell(var_name)
        if cell:
          if cell.readonly:
            chars.append('r')
          if cell.exported:
            chars.append('x')
          if cell.nameref:
            chars.append('n')

      result = value.Str(''.join(chars))

    else:
      e_die('Var op %r not implemented' % op.val, op)

    return result, quoted2

  def _WholeArray(self, val, part, quoted, vsub_state):
    # type: (value_t, braced_var_sub, bool, VarSubState) -> value_t
    bracket_op = cast(bracket_op__WholeArray, part.bracket_op)
    op_id = bracket_op.op_id

    if op_id == Id.Lit_At:
      vsub_state.join_array = not quoted  # ${a[@]} decays but "${a[@]}" doesn't
      UP_val = val
      with tagswitch(val) as case2:
        if case2(value_e.Undef):
          val = self._EmptyMaybeStrArrayOrError(part.token)
        elif case2(value_e.Str):
          val = cast(value__Str, UP_val)
          e_die("Can't index string with @", loc.WordPart(part))
        elif case2(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          # TODO: Is this a no-op?  Just leave 'val' alone.
          val = value.MaybeStrArray(val.strs)

    elif op_id == Id.Arith_Star:
      vsub_state.join_array = True  # both ${a[*]} and "${a[*]}" decay
      UP_val = val
      with tagswitch(val) as case2:
        if case2(value_e.Undef):
          val = self._EmptyMaybeStrArrayOrError(part.token)
        elif case2(value_e.Str):
          val = cast(value__Str, UP_val)
          e_die("Can't index string with *", loc.WordPart(part))
        elif case2(value_e.MaybeStrArray):
          val = cast(value__MaybeStrArray, UP_val)
          # TODO: Is this a no-op?  Just leave 'val' alone.
          # ${a[*]} or "${a[*]}" :  vsub_state.join_array is always true
          val = value.MaybeStrArray(val.strs)

    else:
      raise AssertionError(op_id)  # unknown

    return val

  def _ArrayIndex(self, val, part, vtest_place):
    # type: (value_t, braced_var_sub, VTestPlace) -> value_t
    """Process a numeric array index like ${a[i+1]}"""
    bracket_op = cast(bracket_op__ArrayIndex, part.bracket_op)
    anode = bracket_op.expr

    UP_val = val
    with tagswitch(val) as case2:
      if case2(value_e.Undef):
        pass  # it will be checked later

      elif case2(value_e.Str):
        # Bash treats any string as an array, so we can't add our own
        # behavior here without making valid OSH invalid bash.
        e_die("Can't index string %r with integer" % part.token.val,
              part.token)

      elif case2(value_e.MaybeStrArray):
        array_val = cast(value__MaybeStrArray, UP_val)
        index = self.arith_ev.EvalToInt(anode)
        vtest_place.index = a_index.Int(index)

        s = GetArrayItem(array_val.strs, index)

        if s is None:
          val = value.Undef()
        else:
          val = value.Str(s)

      elif case2(value_e.AssocArray):
        assoc_val = cast(value__AssocArray, UP_val)
        key = self.arith_ev.EvalWordToString(anode)
        vtest_place.index = a_index.Str(key)  # out param
        s = assoc_val.d.get(key)

        if s is None:
          val = value.Undef()
        else:
          val = value.Str(s)

      else:
        raise AssertionError(val.tag_())

    return val

  def _EvalDoubleQuoted(self, parts, part_vals):
    # type: (List[word_part_t], List[part_value_t]) -> None
    """Evaluate parts of a DoubleQuoted part.

    Args:
      part_vals: output param to append to.
    """
    # Example of returning array:
    # $ a=(1 2); b=(3); $ c=(4 5)
    # $ argv "${a[@]}${b[@]}${c[@]}"
    # ['1', '234', '5']
    #
    # Example of multiple parts
    # $ argv "${a[@]}${undef[@]:-${c[@]}}"
    # ['1', '24', '5']

    # Special case for "".  The parser outputs (DoubleQuoted []), instead
    # of (DoubleQuoted [Literal '']).  This is better but it means we
    # have to check for it.
    if len(parts) == 0:
      v = part_value.String('', True, False)
      part_vals.append(v)
      return

    for p in parts:
      self._EvalWordPart(p, part_vals, QUOTED)

  def EvalDoubleQuotedToString(self, dq_part):
    # type: (double_quoted) -> str
    """For double quoted strings in Oil expressions.

    Example: var x = "$foo-${foo}"
    """
    part_vals = []  # type: List[part_value_t]
    self._EvalDoubleQuoted(dq_part.parts, part_vals)
    return self._ConcatPartVals(part_vals, dq_part.left.span_id)

  def _DecayArray(self, val):
    # type: (value__MaybeStrArray) -> value__Str
    """Decay $* to a string."""
    assert val.tag_() == value_e.MaybeStrArray, val
    sep = self.splitter.GetJoinChar()
    tmp = [s for s in val.strs if s is not None]
    return value.Str(sep.join(tmp))

  def _EmptyStrOrError(self, val, token):
    # type: (value_t, Token) -> value_t
    if val.tag_() != value_e.Undef:
      return val

    if not self.exec_opts.nounset():
      return value.Str('')

    name = token.val[1:] if token.val.startswith('$') else token.val
    e_die('Undefined variable %r' % name, token)

  def _EmptyMaybeStrArrayOrError(self, token):
    # type: (Token) -> value_t
    assert token is not None
    if self.exec_opts.nounset():
      e_die('Undefined array %r' % token.val, token)
    else:
      return value.MaybeStrArray([])

  def _EvalBracketOp(self, val, part, quoted, vsub_state, vtest_place):
    # type: (value_t, braced_var_sub, bool, VarSubState, VTestPlace) -> value_t

    if part.bracket_op:
      bracket_op = part.bracket_op
      UP_bracket_op = bracket_op
      with tagswitch(bracket_op) as case:
        if case(bracket_op_e.WholeArray):
          val = self._WholeArray(val, part, quoted, vsub_state)

        elif case(bracket_op_e.ArrayIndex):
          bracket_op = cast(bracket_op__ArrayIndex, UP_bracket_op)
          val = self._ArrayIndex(val, part, vtest_place)

        else:
          raise AssertionError(bracket_op.tag_())

    else:  # no bracket op
      var_name = vtest_place.name
      if (var_name and val.tag_() in (value_e.MaybeStrArray, value_e.AssocArray) and
          not vsub_state.is_type_query):
        if ShouldArrayDecay(var_name, self.exec_opts,
                            not (part.prefix_op or part.suffix_op)):
          # for ${BASH_SOURCE}, etc.
          val = DecayArray(val)
        else:
          e_die("Array %r can't be referred to as a scalar (without @ or *)" %
                var_name, loc.WordPart(part))

    return val

  def _VarRefValue(self, part, quoted, vsub_state, vtest_place):
    # type: (braced_var_sub, bool, VarSubState, VTestPlace) -> value_t
    """Duplicates some logic from _EvalBracedVarSub, but returns a value_t."""

    # 1. Evaluate from (var_name, var_num, token Id) -> value
    if part.token.id == Id.VSub_Name:
      var_name = part.token.val
      vtest_place.name = var_name
      val = self.mem.GetValue(var_name)

    elif part.token.id == Id.VSub_Number:
      var_num = int(part.token.val)
      val = self._EvalVarNum(var_num)

    else:
      # $* decays
      val = self._EvalSpecialVar(part.token.id, quoted, vsub_state)

    # We don't need var_index because it's only for L-Values of test ops?
    val = self._EvalBracketOp(val, part, quoted, vsub_state, vtest_place)
    return val

  def _EvalBracedVarSub(self, part, part_vals, quoted):
    # type: (braced_var_sub, List[part_value_t], bool) -> None
    """
    Args:
      part_vals: output param to append to.
    """
    # We have different operators that interact in a non-obvious order.
    #
    # 1. bracket_op: value -> value, with side effect on vsub_state
    #
    # 2. prefix_op
    #    a. length  ${#x}: value -> value
    #    b. var ref ${!ref}: can expand to an array
    # 
    # 3. suffix_op:
    #    a. no operator: you have a value
    #    b. Test: value -> part_value[]
    #    c. Other Suffix: value -> value
    #
    # 4. Process vsub_state.join_array here before returning.
    #
    # These cases are hard to distinguish:
    # - ${!prefix@}   prefix query
    # - ${!array[@]}  keys
    # - ${!ref}       named reference
    # - ${!ref[0]}    named reference
    #
    # I think we need several stages:
    #
    # 1. value: name, number, special, prefix query
    # 2. bracket_op
    # 3. prefix length -- this is TERMINAL
    # 4. indirection?  Only for some of the ! cases
    # 5. string transformation suffix ops like ##
    # 6. test op
    # 7. vsub_state.join_array

    # vsub_state.join_array is for joining "${a[*]}" and unquoted ${a[@]} AFTER
    # suffix ops are applied.  If we take the length with a prefix op, the
    # distinction is ignored.

    var_name = None  # type: str
    vtest_place = VTestPlace(var_name, None)  # For ${foo=default}
    vsub_state = VarSubState()  # for $*, ${a[*]}, etc.

    # 1. Evaluate from (var_name, var_num, token Id) -> value
    if part.token.id == Id.VSub_Name:
      # Handle ${!prefix@} first, since that looks at names and not values
      # Do NOT handle ${!A[@]@a} here!
      if (part.prefix_op is not None and 
          part.bracket_op is None and
          part.suffix_op is not None and
          part.suffix_op.tag_() == suffix_op_e.Nullary):
        suffix_op_ = cast(Token, part.suffix_op)
        # ${!x@} but not ${!x@P}
        if consts.GetKind(suffix_op_.id) == Kind.VOp3:
          names = self.mem.VarNamesStartingWith(part.token.val)
          names.sort()

          suffix_op_ = cast(Token, part.suffix_op)
          if quoted and suffix_op_.id == Id.VOp3_At:
            part_vals.append(part_value.Array(names))
          else:
            sep = self.splitter.GetJoinChar()
            part_vals.append(part_value.String(sep.join(names), quoted, True))
          return  # EARLY RETURN

      var_name = part.token.val
      vtest_place.name = var_name

      # TODO: LINENO can use its own span_id!
      val = self.mem.GetValue(var_name)

    elif part.token.id == Id.VSub_Number:
      var_num = int(part.token.val)
      val = self._EvalVarNum(var_num)
    else:
      # $* decays
      val = self._EvalSpecialVar(part.token.id, quoted, vsub_state)

    # Type query ${array@a} is a STRING, not an array
    # NOTE: ${array@Q} is ${array[0]@Q} in bash, which is different than
    # ${array[@]@Q}
    # TODO: An IR for ${} might simplify these lengthy conditions
    suffix_op = part.suffix_op
    if (suffix_op and suffix_op.tag_() == suffix_op_e.Nullary and 
        cast(Token, suffix_op).id == Id.VOp0_a):
      vsub_state.is_type_query = True

    # 2. Bracket Op
    val = self._EvalBracketOp(val, part, quoted, vsub_state, vtest_place)

    # Do the _EmptyStrOrError up front here, EXCEPT in the case of Kind.VTest
    suffix_is_test = False
    UP_op = suffix_op
    if suffix_op is not None and suffix_op.tag_() == suffix_op_e.Unary:
      suffix_op = cast(suffix_op__Unary, UP_op)
      if consts.GetKind(suffix_op.tok.id) == Kind.VTest:
        suffix_is_test = True

    if part.prefix_op:
      if part.prefix_op.id == Id.VSub_Pound:  # ${#var} for length
        if not suffix_is_test:  # undef -> '' BEFORE length
          val = self._EmptyStrOrError(val, part.token)

        val = self._Length(val, part.token)
        part_val = _ValueToPartValue(val, False)  # assume it's not quoted
        part_vals.append(part_val)
        return  # EARLY EXIT: nothing else can come after length

      elif part.prefix_op.id == Id.VSub_Bang:
        if part.bracket_op and part.bracket_op.tag_() == bracket_op_e.WholeArray:
          if suffix_is_test:
            # ${!a[@]-'default'} is a non-fatal runtime error in bash.  Here
            # it's fatal.
            tok = cast(suffix_op__Unary, UP_op).tok
            e_die('Test operation not allowed with ${!array[@]}', tok)

          # ${!array[@]} to get indices/keys
          val = self._Keys(val, part.token)
          # already set vsub_State.join_array ABOVE
        else:
          # Process ${!ref}.  SURPRISE: ${!a[0]} is an indirect expansion unlike
          # ${!a[@]} !
          # ${!ref} can expand into an array if ref='array[@]'

          # Clear it now that we have a var ref
          vtest_place.name = None
          vtest_place.index = None

          val = self._EvalVarRef(val, part.token, quoted, vsub_state, vtest_place)

          if not suffix_is_test:  # undef -> '' AFTER indirection
            val = self._EmptyStrOrError(val, part.token)

      else:
        raise AssertionError(part.prefix_op)

    else:
      if not suffix_is_test:  # undef -> '' if no prefix op
        val = self._EmptyStrOrError(val, part.token)

    quoted2 = False  # another bit for @Q
    if suffix_op:
      op = suffix_op  # could get rid of this alias

      with tagswitch(suffix_op) as case:
        if case(suffix_op_e.Nullary):
          op = cast(Token, UP_op)
          val, quoted2 = self._Nullary(val, op, var_name)

        elif case(suffix_op_e.Unary):
          op = cast(suffix_op__Unary, UP_op)
          if consts.GetKind(op.tok.id) == Kind.VTest:
            if self._ApplyTestOp(val, op, quoted, part_vals, vtest_place,
                                 part.token):
              # e.g. to evaluate ${undef:-'default'}, we already appended
              # what we need
              return

          else:
            # Other suffix: value -> value
            val = self._ApplyUnarySuffixOp(val, op)

        elif case(suffix_op_e.PatSub):  # PatSub, vectorized
          op = cast(suffix_op__PatSub, UP_op)
          val = self._PatSub(val, op)

        elif case(suffix_op_e.Slice):
          op = cast(suffix_op__Slice, UP_op)
          val = self._Slice(val, op, var_name, part)

        elif case(suffix_op_e.Static):
          op = cast(suffix_op__Static, UP_op)
          e_die('Not implemented', op.tok)

        else:
          raise AssertionError()

    # After applying suffixes, process join_array here.
    UP_val = val
    if val.tag_() == value_e.MaybeStrArray:
      array_val = cast(value__MaybeStrArray, UP_val)
      if vsub_state.join_array:
        val = self._DecayArray(array_val)
      else:
        val = array_val

    # For example, ${a} evaluates to value.Str(), but we want a
    # part_value.String().
    part_val = _ValueToPartValue(val, quoted or quoted2)
    part_vals.append(part_val)

  def _ConcatPartVals(self, part_vals, span_id):
    # type: (List[part_value_t], int) -> str
    """Helper."""
    strs = []  # type: List[str]
    for part_val in part_vals:
      UP_part_val = part_val
      with tagswitch(part_val) as case:
        if case(part_value_e.String):
          part_val = cast(part_value__String, UP_part_val)
          s = part_val.s

        elif case(part_value_e.Array):
          part_val = cast(part_value__Array, UP_part_val)
          if self.exec_opts.strict_array():
            # Examples: echo f > "$@"; local foo="$@"
            e_die("Illegal array word part (strict_array)", loc.Span(span_id))
          else:
            # It appears to not respect IFS
            # TODO: eliminate double join()?
            tmp = [s for s in part_val.strs if s is not None]
            s = ' '.join(tmp)

        else:
          raise AssertionError()

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
    return self._ConcatPartVals(part_vals, part.left.span_id)

  def _EvalSimpleVarSub(self, token, part_vals, quoted):
    # type: (Token, List[part_value_t], bool) -> None

    vsub_state = VarSubState()

    # 1. Evaluate from (var_name, var_num, Token) -> defined, value
    if token.id == Id.VSub_DollarName:
      var_name = token.val[1:]

      # TODO: Special case for LINENO
      val = self.mem.GetValue(var_name)
      if val.tag_() in (value_e.MaybeStrArray, value_e.AssocArray):
        if ShouldArrayDecay(var_name, self.exec_opts):
          # for $BASH_SOURCE, etc.
          val = DecayArray(val)
        else:
          e_die("Array %r can't be referred to as a scalar (without @ or *)" %
                var_name, token)

    elif token.id == Id.VSub_Number:
      var_num = int(token.val[1:])
      val = self._EvalVarNum(var_num)
    else:
      val = self._EvalSpecialVar(token.id, quoted, vsub_state)

    #log('SIMPLE %s', part)
    val = self._EmptyStrOrError(val, token)
    UP_val = val
    if val.tag_() == value_e.MaybeStrArray:
      array_val = cast(value__MaybeStrArray, UP_val)
      if vsub_state.join_array:
        val = self._DecayArray(array_val)
      else:
        val = array_val

    v = _ValueToPartValue(val, quoted)
    part_vals.append(v)

  def EvalSimpleVarSubToString(self, tok):
    # type: (Token) -> str
    """For double quoted strings in Oil expressions.

    Example: var x = "$foo-${foo}"
    """
    part_vals = []  # type: List[part_value_t]
    self._EvalSimpleVarSub(tok, part_vals, False)
    return self._ConcatPartVals(part_vals, tok.span_id)

  def _EvalExtGlob(self, part, part_vals):
    # type: (word_part__ExtGlob, List[part_value_t]) -> None
    """Evaluate @($x|'foo'|$(hostname)) and flatten it"""
    op = part.op
    if op.id == Id.ExtGlob_Comma:
      op_str = '@('
    else:
      op_str = op.val
    # Do NOT split these.
    part_vals.append(part_value.String(op_str, False, False))

    for i, w in enumerate(part.arms):
      if i != 0:
        part_vals.append(part_value.String('|', False, False))  # separator
      # FLATTEN the tree of extglob "arms".
      self._EvalWordToParts(w, part_vals, EXTGLOB_NESTED)
    part_vals.append(part_value.String(')', False, False))  # closing )

  def _TranslateExtGlob(self, part_vals, w, glob_parts, fnmatch_parts):
    # type: (List[part_value_t], compound_word, List[str], List[str]) -> None
    """Translate a flattened WORD with an ExtGlob part to string patterns.
    
    We need both glob and fnmatch patterns.  _EvalExtGlob does the flattening.
    """
    for i, part_val in enumerate(part_vals):
      UP_part_val = part_val
      with tagswitch(part_val) as case:
        if case(part_value_e.String):
          part_val = cast(part_value__String, UP_part_val)
          if part_val.quoted and not self.exec_opts.noglob():
            s = glob_.GlobEscape(part_val.s)
          else:
            # e.g. the @( and | in @(foo|bar) aren't quoted
            s = part_val.s
          glob_parts.append(s)
          fnmatch_parts.append(s)  # from _EvalExtGlob()

        elif case(part_value_e.Array):
          # Disallow array
          e_die("Extended globs and arrays can't appear in the same word",
                loc.Word(w))

        elif case(part_value_e.ExtGlob):
          part_val = cast(part_value__ExtGlob, UP_part_val)
          # keep appending fnmatch_parts, but repplace glob_parts with '*'
          self._TranslateExtGlob(part_val.part_vals, w, [], fnmatch_parts)
          glob_parts.append('*')

        else:
          raise AssertionError()

  def _EvalWordPart(self, part, part_vals, flags):
    # type: (word_part_t, List[part_value_t], int) -> None
    """Evaluate a word part.

    Called by _EvalWordToParts, EvalWordToString, and _EvalDoubleQuoted.

    Args:
      part: What to evaluate
      part_vals: Output parameter.
      quoted: was the part quoted like "$x"
      is_subst: do_split

    Returns:
      None
    """
    quoted = bool(flags & QUOTED)
    is_subst = bool(flags & IS_SUBST)

    UP_part = part
    with tagswitch(part) as case:
      if case(word_part_e.ShArrayLiteral):
        part = cast(sh_array_literal, UP_part)
        e_die("Unexpected array literal", loc.WordPart(part))
      elif case(word_part_e.AssocArrayLiteral):
        part = cast(word_part__AssocArrayLiteral, UP_part)
        e_die("Unexpected associative array literal", loc.WordPart(part))

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
        s = word_compile.EvalSingleQuoted(part)
        v = part_value.String(s, True, False)
        part_vals.append(v)

      elif case(word_part_e.DoubleQuoted):
        part = cast(double_quoted, UP_part)
        self._EvalDoubleQuoted(part.parts, part_vals)

      elif case(word_part_e.CommandSub):
        part = cast(command_sub, UP_part)
        id_ = part.left_token.id
        if id_ in (Id.Left_DollarParen, Id.Left_AtParen, Id.Left_Backtick):
          sv = self._EvalCommandSub(part, quoted)  # type: part_value_t

        elif id_ in (Id.Left_ProcSubIn, Id.Left_ProcSubOut):
          sv = self._EvalProcessSub(part)

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
        s = self.tilde_ev.Eval(part.token)
        v = part_value.String(s, True, False)  # NOT split even when unquoted!
        part_vals.append(v)

      elif case(word_part_e.ArithSub):
        part = cast(word_part__ArithSub, UP_part)
        num = self.arith_ev.EvalToInt(part.anode)
        v = part_value.String(str(num), quoted, not quoted)
        part_vals.append(v)

      elif case(word_part_e.ExtGlob):
        part = cast(word_part__ExtGlob, UP_part)
        #if not self.exec_opts.extglob():
        #  die()  # disallow at runtime?  Don't just decay

        # Create a node to hold the flattened tree.  The caller decides whether
        # to pass it to fnmatch() or replace it with '*' and pass it to glob().
        v2 = part_value.ExtGlob()
        self._EvalExtGlob(part, v2.part_vals)  # flattens tree
        part_vals.append(v2)

      elif case(word_part_e.Splice):
        part = cast(word_part__Splice, UP_part)
        var_name = part.name.val[1:]
        val = self.mem.GetValue(var_name)

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
              items = self.expr_ev.SpliceValue(val, part)
            else:
              raise AssertionError()

          else:
            e_die("Can't splice %r" % var_name, loc.WordPart(part))

        part_vals.append(part_value.Array(items))

      elif case(word_part_e.FuncCall):
        part = cast(word_part__FuncCall, UP_part)
        if mylib.PYTHON:
          part_val = self.expr_ev.EvalInlineFunc(part)
          part_vals.append(part_val)

      elif case(word_part_e.ExprSub):
        part = cast(word_part__ExprSub, UP_part)
        if mylib.PYTHON:
          part_val = self.expr_ev.EvalExprSub(part)
          part_vals.append(part_val)

      else:
        raise AssertionError(part.tag_())

  def _EvalRhsWordToParts(self, w, part_vals, eval_flags=0):
    # type: (rhs_word_t, List[part_value_t], int) -> None
    quoted = bool(eval_flags & QUOTED)

    UP_w = w
    with tagswitch(w) as case:
      if case(rhs_word_e.Empty):
        part_vals.append(part_value.String('', quoted, not quoted))

      elif case(rhs_word_e.Compound):
        w = cast(compound_word, UP_w)
        self._EvalWordToParts(w, part_vals, eval_flags=eval_flags)

      else:
        raise AssertionError()

  def _EvalWordToParts(self, w, part_vals, eval_flags=0):
    # type: (compound_word, List[part_value_t], int) -> None
    """Helper for EvalRhsWord, EvalWordSequence, etc.

    Returns:
      Appends to part_vals.  Note that this is a TREE.
    """
    # Does the word have an extended glob?  This is a special case because
    # of the way we use glob() and then fnmatch(..., FNM_EXTMATCH) to
    # implement extended globs.  It's hard to carry that extra information
    # all the way past the word splitting stage.

    # OSH semantic limitations: If a word has an extended glob part, then
    # 1. It can't have an array
    # 2. Word splitting of unquoted words isn't respected

    word_part_vals = []  # type: List[part_value_t]
    has_extglob = False
    for p in w.parts:
      if p.tag_() == word_part_e.ExtGlob:
        has_extglob = True
      self._EvalWordPart(p, word_part_vals, eval_flags)

    # Caller REQUESTED extglob evaluation, AND we parsed word_part.ExtGlob()
    if has_extglob:
      if bool(eval_flags & EXTGLOB_FILES):
        # Treat the WHOLE word as a pattern.  We need to TWO VARIANTS of the
        # word because of the way we use libc:
        # 1. With '*' for extglob parts
        # 2. With _EvalExtGlob() for extglob parts

        glob_parts = []  # type: List[str]
        fnmatch_parts = []  # type: List[str]
        self._TranslateExtGlob(word_part_vals, w, glob_parts, fnmatch_parts)

        #log('word_part_vals %s', word_part_vals)
        glob_pat = ''.join(glob_parts)
        fnmatch_pat = ''.join(fnmatch_parts)
        #log("glob %s fnmatch %s", glob_pat, fnmatch_pat)

        results = []  # type: List[str]
        n = self.globber.ExpandExtended(glob_pat, fnmatch_pat, results)
        if n < 0:
          span_id = word_.LeftMostSpanForWord(w)
          raise error.FailGlob(
              'Extended glob %r matched no files' % fnmatch_pat,
              loc.Span(span_id))

        part_vals.append(part_value.Array(results))
      elif bool(eval_flags & EXTGLOB_NESTED):
        # We only glob at the TOP level of @(nested|@(pattern))
        part_vals.extend(word_part_vals)
      else:
        # e.g. simple_word_eval, assignment builtin
        e_die('Extended glob not allowed in this word', loc.Word())
    else:
      part_vals.extend(word_part_vals)

  def _PartValsToString(self, part_vals, w, eval_flags, strs):
    # type: (List[part_value_t], compound_word, int, List[str]) -> None
    """Helper for EvalWordToString, similar to _ConcatPartVals() above.

    Note: arg 'w' could just be a span ID
    """
    for part_val in part_vals:
      UP_part_val = part_val
      with tagswitch(part_val) as case:
        if case(part_value_e.String):
          part_val = cast(part_value__String, UP_part_val)
          s = part_val.s
          if part_val.quoted:
            if eval_flags & QUOTE_FNMATCH:
              # [[ foo == */"*".py ]] or case (*.py) or ${x%*.py} or ${x//*.py/}
              s = glob_.GlobEscape(s)
            elif eval_flags & QUOTE_ERE:
              s = glob_.ExtendedRegexEscape(s)
          strs.append(s)

        elif case(part_value_e.Array):
          part_val = cast(part_value__Array, UP_part_val)
          if self.exec_opts.strict_array():
            # Examples: echo f > "$@"; local foo="$@"

            # TODO: This attributes too coarsely, to the word rather than the
            # parts.  Problem: the word is a TREE of parts, but we only have a
            # flat list of part_vals.  The only case where we really get arrays
            # is "$@", "${a[@]}", "${a[@]//pat/replace}", etc.
            e_die("This word should yield a string, but it contains an array",
                  loc.Word(w))

            # TODO: Maybe add detail like this.
            #e_die('RHS of assignment should only have strings.  '
            #      'To assign arrays, use b=( "${a[@]}" )')
          else:
            # It appears to not respect IFS
            tmp = [s for s in part_val.strs if s is not None]
            s = ' '.join(tmp)  # TODO: eliminate double join()?
            strs.append(s)

        elif case(part_value_e.ExtGlob):
          part_val = cast(part_value__ExtGlob, UP_part_val)

          # Extended globs are only allowed where we expect them!
          if not bool(eval_flags & QUOTE_FNMATCH):
            e_die('extended glob not allowed in this word', loc.Word(w))

          # recursive call
          self._PartValsToString(part_val.part_vals, w, eval_flags, strs)

        else:
          raise AssertionError()

  def EvalWordToString(self, UP_w, eval_flags=0):
    # type: (word_t, int) -> value__Str
    """Given a word, return a string.

    Flags can contain a quoting algorithm.
    """
    assert UP_w.tag_() == word_e.Compound, UP_w
    w = cast(compound_word, UP_w)

    part_vals = []  # type: List[part_value_t]
    for p in w.parts:
      # this doesn't use eval_flags, which is slightly confusing
      self._EvalWordPart(p, part_vals, 0)

    strs = []  # type: List[str]
    self._PartValsToString(part_vals, w, eval_flags, strs)
    return value.Str(''.join(strs))

  def EvalWordToPattern(self, UP_w):
    # type: (rhs_word_t) -> Tuple[value__Str, bool]
    """Like EvalWordToString, but returns whether we got ExtGlob."""
    if UP_w.tag_() == rhs_word_e.Empty:
      return value.Str(''), False

    assert UP_w.tag_() == rhs_word_e.Compound, UP_w
    w = cast(compound_word, UP_w)

    has_extglob = False
    part_vals = []  # type: List[part_value_t]
    for p in w.parts:
      # this doesn't use eval_flags, which is slightly confusing
      self._EvalWordPart(p, part_vals, 0)
      if p.tag_() == word_part_e.ExtGlob:
        has_extglob = True

    strs = []  # type: List[str]
    self._PartValsToString(part_vals, w, QUOTE_FNMATCH, strs)
    return value.Str(''.join(strs)), has_extglob

  def EvalForPlugin(self, w):
    # type: (compound_word) -> value__Str
    """Wrapper around EvalWordToString that prevents errors.
    
    Runtime errors like $(( 1 / 0 )) and mutating $? like $(exit 42) are
    handled here.
    """
    with state.ctx_Registers(self.mem):  # to "sandbox" $? and $PIPESTATUS
      try:
        val = self.EvalWordToString(w)
      except error.FatalRuntime as e:
        val = value.Str('<Runtime error: %s>' % e.UserErrorString())

      except (IOError, OSError) as e:
        val = value.Str('<I/O error: %s>' % pyutil.strerror(e))

      except KeyboardInterrupt:
        val = value.Str('<Ctrl-C>')

    return val

  def EvalRhsWord(self, UP_w):
    # type: (rhs_word_t) -> value_t
    """Used for RHS of assignment.  There is no splitting.
    """
    if UP_w.tag_() == rhs_word_e.Empty:
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
        return value.MaybeStrArray(strs)

      if tag == word_part_e.AssocArrayLiteral:
        part0 = cast(word_part__AssocArrayLiteral, UP_part0)
        d = NewDict()  # type: Dict[str, str]
        n = len(part0.pairs)
        for pair in part0.pairs:
          k = self.EvalWordToString(pair.key)
          v = self.EvalWordToString(pair.value)
          d[k.s] = v.s
        return value.AssocArray(d)

    # If RHS doesn't look like a=( ... ), then it must be a string.
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

    will_glob = not self.exec_opts.noglob()

    # Array of strings, some of which are BOTH IFS-escaped and GLOB escaped!
    frags = []  # type: List[str]
    for frag, quoted, do_split in frame:
      if will_glob and quoted:
        frag = glob_.GlobEscape(frag)
      else:
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
      if glob_.LooksLikeGlob(a):
        n = self.globber.Expand(a, argv)
        if n < 0:
          # TODO: location info, with span IDs carried through the frame
          raise error.FailGlob('Pattern %r matched no files' % a,
                               loc.Missing())
      else:
        argv.append(glob_.GlobUnescape(a))

  def _EvalWordToArgv(self, w):
    # type: (compound_word) -> List[str]
    """Helper for _EvalAssignBuiltin.

    Splitting and globbing are disabled for assignment builtins.

    Example: declare -"${a[@]}" b=(1 2)
    where a is [x b=a d=a]
    """
    part_vals = []  # type: List[part_value_t]
    self._EvalWordToParts(w, part_vals, 0)  # not double quoted
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

    eval_to_pairs = True  # except for -f and -F
    started_pairs = False

    flags = [arg0]  # initial flags like -p, and -f -F name1 name2
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
            e_die('LHS array not allowed in assignment builtin', loc.Word(w))

          tok_val = left_token.val
          if tok_val[-2] == '+':
            var_name = tok_val[:-2]
            append = True
          else:
            var_name = tok_val[:-1]
            append = False

          if part_offset == len(w.parts):
            rhs = rhs_word.Empty()  # type: rhs_word_t
          else:
            # tmp is for intersection of C++/MyPy type systems
            tmp = compound_word(w.parts[part_offset:])
            word_.TildeDetectAssign(tmp)
            rhs = tmp

          with state.ctx_AssignBuiltin(self.mutable_opts):
            right = self.EvalRhsWord(rhs)

          arg2 = assign_arg(var_name, right, append, word_spid)

          assign_args.append(arg2)

        else:  # e.g. export $dynamic
          argv = self._EvalWordToArgv(w)
          for arg in argv:
            arg2 = _SplitAssignArg(arg, word_spid)
            assign_args.append(arg2)

      else:
        argv = self._EvalWordToArgv(w)
        for arg in argv:
          if arg.startswith('-') or arg.startswith('+'):  # e.g. declare -r +r
            flags.append(arg)
            flag_spids.append(word_spid)

            # Shortcut that relies on -f and -F always meaning "function" for
            # all assignment builtins
            if 'f' in arg or 'F' in arg:
              eval_to_pairs = False

          else:  # e.g. export $dynamic 
            if eval_to_pairs:
              arg2 = _SplitAssignArg(arg, word_spid)
              assign_args.append(arg2)
              started_pairs = True
            else:
              flags.append(arg)

    return cmd_value.Assign(builtin_id, flags, flag_spids, assign_args)

  def SimpleEvalWordSequence2(self, words, allow_assign):
    # type: (List[compound_word], bool) -> cmd_value_t
    """Simple word evaluation for Oil."""
    strs = []  # type: List[str]
    spids = []  # type: List[int]

    n = 0
    for i, w in enumerate(words):
      word_spid = word_.LeftMostSpanForWord(w)

      # No globbing in the first arg for command.Simple.
      if i == 0 and allow_assign:
        strs0 = self._EvalWordToArgv(w)  # respects strict-array
        if len(strs0) == 1:
          arg0 = strs0[0]
          builtin_id = consts.LookupAssignBuiltin(arg0)
          if builtin_id != consts.NO_INDEX:
            # Same logic as legacy word eval, with no splitting
            return self._EvalAssignBuiltin(builtin_id, arg0, words)

        strs.extend(strs0)
        for _ in strs0:
          spids.append(word_spid)
        continue

      if glob_.LooksLikeStaticGlob(w):
        val = self.EvalWordToString(w)  # respects strict-array
        num_appended = self.globber.Expand(val.s, strs)
        if num_appended < 0:
          raise error.FailGlob('Pattern %r matched no files' % val.s,
                               loc.Span(word_spid))
        for _ in xrange(num_appended):
          spids.append(word_spid)
        continue

      part_vals = []  # type: List[part_value_t]
      self._EvalWordToParts(w, part_vals, 0)  # not quoted

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
    if self.exec_opts.simple_word_eval():
      return self.SimpleEvalWordSequence2(words, allow_assign)

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
      self._EvalWordToParts(w, part_vals, EXTGLOB_FILES)

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
            builtin_id = consts.LookupAssignBuiltin(val0.s)
            if builtin_id != consts.NO_INDEX:
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


class NormalWordEvaluator(AbstractWordEvaluator):

  def __init__(self, mem, exec_opts, mutable_opts, splitter, errfmt):
    # type: (Mem, optview.Exec, state.MutableOpts, SplitContext, ErrorFormatter) -> None
    AbstractWordEvaluator.__init__(self, mem, exec_opts, mutable_opts, splitter, errfmt)
    self.shell_ex = None  # type: _Executor

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.arith_ev is not None
    # Disabled for pure OSH
    #assert self.expr_ev is not None
    assert self.shell_ex is not None
    assert self.prompt_ev is not None

  def _EvalCommandSub(self, cs_part, quoted):
    # type: (command_sub, bool) -> part_value_t
    stdout = self.shell_ex.RunCommandSub(cs_part)
    if cs_part.left_token.id == Id.Left_AtParen:
      strs = self.splitter.SplitForWordEval(stdout)
      return part_value.Array(strs)
    else:
      return part_value.String(stdout, quoted, not quoted)

  def _EvalProcessSub(self, cs_part):
    # type: (command_sub) -> part_value__String
    dev_path = self.shell_ex.RunProcessSub(cs_part)
    # pretend it's quoted; no split or glob
    return part_value.String(dev_path, True, False)


_DUMMY = '__NO_COMMAND_SUB__'

class CompletionWordEvaluator(AbstractWordEvaluator):
  """An evaluator that has no access to an executor.

  NOTE: core/completion.py doesn't actually try to use these strings to
  complete.  If you have something like 'echo $(echo hi)/f<TAB>', it sees the
  inner command as the last one, and knows that it is not at the end of the
  line.
  """
  def CheckCircularDeps(self):
    # type: () -> None
    assert self.prompt_ev is not None
    assert self.arith_ev is not None
    assert self.expr_ev is not None

  def _EvalCommandSub(self, cs_part, quoted):
    # type: (command_sub, bool) -> part_value_t
    if cs_part.left_token.id == Id.Left_AtParen:
      return part_value.Array([_DUMMY])
    else:
      return part_value.String(_DUMMY, quoted, not quoted)

  def _EvalProcessSub(self, cs_part):
    # type: (command_sub) -> part_value__String
    # pretend it's quoted; no split or glob
    return part_value.String('__NO_PROCESS_SUB__', True, False)
