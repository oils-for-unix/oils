"""
word_eval.py - Evaluator for the word language.
"""

import glob
import re

from core import braces
from core import expr_eval  # ArithEval
from core.glob_ import Globber, GlobEscape
from core.id_kind import Id, Kind, IdName, LookupKind
from core import util
from core import runtime
from osh import ast_ as ast

bracket_op_e = ast.bracket_op_e
part_value_e = runtime.part_value_e
value_e = runtime.value_e
arg_value_e = runtime.arg_value_e
word_part_e = ast.word_part_e
log = util.log


def _ValueToPartValue(val, quoted):
  """Helper for VarSub evaluation."""
  assert isinstance(val, runtime.value), val
  if val.tag == value_e.Undef:
    return runtime.UndefPartValue()

  elif val.tag == value_e.Str:
    return runtime.StringPartValue(val.s, not quoted, not quoted)

  elif val.tag == value_e.StrArray:
    return runtime.ArrayPartValue(val.strs)

  else:
    raise AssertionError


def _GetIfs(mem):
  """
  Used for splitting words in Splitter, and joining $* in _WordPartEvaluator.
  """
  val = mem.Get('IFS')
  if val.tag == value_e.Undef:
    return ' \t\n'  # default for sh; default for oil is ''
  elif val.tag == value_e.Str:
    return val.s
  else:
    # TODO: Raise proper error
    raise AssertionError("IFS shouldn't be an array")


def _Split(s, ifs):
  """Helper function for IFS split."""
  parts = ['']
  for c in s:
    if c in ifs:
      parts.append('')
    else:
      parts[-1] += c
  return parts


def _IfsSplit(s, ifs):
  """
  http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_06_05
  https://www.gnu.org/software/bash/manual/bashref.html#Word-Splitting

  Summary:
  1. ' \t\n' is special.  Whitespace is trimmed off the front and back.
  2. if IFS is '', no field splitting is performed.
  3. Otherwise, suppose IFS = ' ,\t'.  Then IFS whitespace is space or comma.
    a.  IFS whitespace isgnored at beginning and end.
    b. any other IFS char delimits the field, along with adjacent IFS
       whitespace.
    c. IFS whitespace shall delimit a field.

  # Can we do this be regex or something?  Use regex match?
  """
  # TODO: test undef
  if not ifs:
    return [s]  # no splitting

  # print("IFS SPLIT %r %r" % (s, ifs))
  if ifs == ' \t\n':
    # Split by whitespace, and empty strings removed
    frags = _Split(s, ifs)
    return [f for f in frags if f]

  # Detect IFS whitespace
  ifs_whitespace = ''
  ifs_other = ''
  for c in ifs:
    if c in ' \t\n':
      ifs_whitespace += c
    else:
      ifs_other += c

  # hack to make an RE

  # Hm this escapes \t as \\\t?  I guess that works.
  ws_re = re.escape(ifs_whitespace)

  other_re = re.escape(ifs_other)
  #print('chars', repr(ifs_whitespace), repr(ifs_other))
  #print('RE', repr(ws_re), repr(other_re))

  # ifs_ws | ifs_ws* non_ws_ifs ifs_ws*
  if ifs_whitespace and ifs_other:
    pat = '[%s]+|[%s]*[%s][%s]*' % (ws_re, ws_re, other_re, ws_re)
  elif ifs_whitespace:
    pat = '[%s]*[%s][%s]*' % (ws_re, other_re, ws_re)
  elif ifs_other:
    pat = '[%s]' % other_re
  else:
    raise AssertionError

  #print('PAT', repr(pat))
  regex = re.compile(pat)
  frags = regex.split(s)
  return frags


def _SplitPartsIntoFragments(part_vals, ifs):
  """
  part_value[] -> part_value[]
  Depends on no_glob
  """
  # Every part yields a single fragment array.
  frag_arrays = []
  for p in part_vals:
    if p.tag == part_value_e.StringPartValue:
      #log("SPLITTING %s", p)
      if p.do_split_elide:
        frags = _IfsSplit(p.s, ifs)
        do_glob = bool(p.do_glob)  # TODO: initialize
        res = [runtime.fragment(f, True, do_glob) for f in frags]
      else:
        # Example: 'a b' and "a b" don't need to be split.
        do_elide = bool(p.do_split_elide)
        do_glob = bool(p.do_glob)  # TODO: initialize
        res = [runtime.fragment(p.s, do_elide, do_glob)]
    elif p.tag == part_value_e.ArrayPartValue:
      # "$@" and "${a[@]}" don't need to be split or globbed
      res = [runtime.fragment(f, False, False) for f in p.strs]
    else:
      raise AssertionError(p.tag)

    frag_arrays.append(res)

  return frag_arrays


def _Reframe(frag_arrays):
  """
  frag_arrays -> frag_arrays

  Example:
  [a b][c][d e] -> [a] [bcd] [e]
  """
  res = [[]]
  for frag_array in frag_arrays:
    if len(frag_array) == 1:
      frag = frag_array[0]
      res[-1].append(frag)
    else:
      for i, frag in enumerate(frag_array):
        if i == 0:
          res[-1].append(frag)
        else:
          res.append([frag])  # singleton frag
  return res


def _JoinElideEscape(frag_arrays, glob_escape=False):
  """Join parts without globbing or eliding.

  Returns:
    arg_value[]
  """
  args = []
  for frag_array in frag_arrays:
    if glob_escape:
      #log('frag_array: %s', frag_array)
      escaped_frags = []
      any_glob = False
      for frag in frag_array:
        if frag.do_glob:  # *.py should be literal
          escaped_frags.append(frag.s)
          any_glob = True
        else:
          # "*.py" should be glob-escaped to \*.py
          escaped_frags.append(GlobEscape(frag.s))

      arg_str = ''.join(escaped_frags)
      #log('ARG STR %s', arg_str)
      if any_glob:
        arg = runtime.GlobArg(arg_str)
      else:
        # e.g. 'foo'"${var}" shouldn't be globbed
        # TODO: combine with below:
        arg = runtime.ConstArg(''.join(frag.s for frag in frag_array))
    else:
      arg = runtime.ConstArg(''.join(frag.s for frag in frag_array))

    # Elide $a$b, but not $a"$b" or $a''
    # NOTE: Does this depend on IFS?
    if not arg.s and all(frag.do_elide for frag in frag_array):
      continue

    args.append(arg)

  return args


class _EvalError(RuntimeError):
  pass

# Eval is for ${a-} and ${a+}, Error is for ${a?}, and Assign is for ${a=}

Effect = util.Enum('Effect', 'Eval Error Assign NoOp'.split())


class _WordPartEvaluator:
  """Abstract base class."""

  def __init__(self, mem, exec_opts, word_ev):
    self.mem = mem  # for $HOME, $1, etc.
    self.exec_opts = exec_opts  # for nounset
    self.word_ev = word_ev  # for arith words, var op words

  def _EvalCommandSub(self, part, quoted):
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
      val = self.mem.Get('HOME')
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
    argv = self.mem.GetArgv()
    assert var_num >= 0

    if var_num == 0:
      return runtime.Str(self.mem.GetArgv0())
    else:
      index = var_num - 1
      if index < len(argv):
        return runtime.Str(str(argv[index]))
      else:
        # NOTE: This is not a fatal error.
        #self._AddErrorContext(
        #    'argv has %d entries; %d is out of range', len(argv), var_num)
        return runtime.Undef()

  def _EvalSpecialVar(self, op_id, quoted):
    # $@ is special -- it need to know whether it is in a double quoted
    # context.
    #
    # - If it's $@ in a double quoted context, return an ARRAY.
    # - If it's $@ in a normal context, return a STRING, which then will be
    # subject to splitting.

    # https://www.gnu.org/software/bash/manual/bashref.html#Special-Parameters
    # http://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_05_02
    # "When the expansion occurs within a double-quoted string (see
    # Double-Quotes), it shall expand to a single field with the value of
    # each parameter separated by the first character of the IFS variable, or
    # by a <space> if IFS is unset. If IFS is set to a null string, this is
    # not equivalent to unsetting it; its first character does not exist, so
    # the parameter values are concatenated."
    ifs = _GetIfs(self.mem)
    sep = ifs[0] if ifs else ''

    # GetArgv.  And then look at whether we're in a double quoted context or
    # not.
    if op_id in (Id.VSub_At, Id.VSub_Star):
      if op_id == Id.VSub_At and quoted:  # "$@" evaluates to an array
        argv = self.mem.GetArgv()
        val = runtime.StrArray(argv)
        #print('$@', val)
        return val
      else:  # $@ $* "$*"
        argv = self.mem.GetArgv()
        val = runtime.Str(ifs[0].join(argv))
        return val

    elif op_id == Id.VSub_QMark:  # $?
      # TODO: Have to parse status somewhere.
      # External commands need WIFEXITED test.  What about subshells?
      return runtime.Str(str(self.mem.last_status))

    elif op_id == Id.VSub_Pound:  # $#
      argv = self.mem.GetArgv()
      s = str(len(argv))
      return runtime.Str(s)

    else:
      raise NotImplementedError(op_id)

  def _ApplyBracketOp(self, val, bracket_op, quoted):
    """
    Returns:
      part_value
    """
    assert isinstance(val, runtime.value), val
    assert val.tag == value_e.StrArray

    if bracket_op.tag == bracket_op_e.WholeArray:
      op_id = bracket_op.op_id

      joined = runtime.StringPartValue(' '.join(s for s in val.strs),
                                       not quoted, not quoted)
      if op_id == Id.Lit_At:
        #log("PART %s %s", part, val)
        if val.tag == value_e.StrArray:
          if quoted: # "${a[@]}"
            return runtime.ArrayPartValue(val.strs)
          else:      #  ${a[@]}
            return joined
        else:
          raise AssertionError("Can't index non-array with @")

      elif op_id == Id.Arith_Star:
        if val.tag == value_e.StrArray:
          return joined
        else:
          raise AssertionError("Can't index non-array with *")

      else:
        raise AssertionError(op_id)  # unknown

    elif bracket_op.tag == bracket_op_e.ArrayIndex:
      anode = bracket_op.expr
      # TODO: This should propagate errors
      arith_ev = expr_eval.ArithEvaluator(self.mem, self.word_ev)
      ok = arith_ev.Eval(anode)
      if not ok:
        self._AddErrorContext(
            'Error evaluating arith sub in index expression')
        return False, None
      index = arith_ev.Result()

      try:
        s = val.strs[index]
      except IndexError:
        return runtime.UndefPartValue()
      else:
        return runtime.StringPartValue(s, not quoted, not quoted)

    else:
      raise AssertionError(bracket_op.tag)

  def _ApplyTestOp(self, part_val, op):
    """
    Returns:
      value, Effect

      ${a:-} returns part_value[]
      ${a:+} returns part_value[]
      ${a:?error} returns error word?
      ${a:=} returns part_value[] but also needs self.mem for side effects.

      So I guess it should return part_value[], and then a flag for raising an
      error, and then a flag for assigning it?
      The original BracedVarSub will have the name.
    """
    undefined = (part_val.tag == part_value_e.UndefPartValue)

    # TODO: Change this to a bit test.
    if op.op_id in (
        Id.VTest_ColonHyphen, Id.VTest_ColonEquals, Id.VTest_ColonQMark,
        Id.VTest_ColonPlus):
      is_falsey = (
          undefined or (part_val.tag == value_e.Str and part_val.s == ''))
    else:
      is_falsey = undefined

    #print('!!',id, is_falsey)
    if op.op_id in (Id.VTest_ColonHyphen, Id.VTest_Hyphen):
      if is_falsey:
        ok, val = self.word_ev.EvalWordToAny(op.arg_word)
        if not ok:
          raise AssertionError
        # NOTE: Pretending it's QUOTED
        return _ValueToPartValue(val, quoted=True), Effect.Eval
      else:
        return None, Effect.NoOp

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
    if op_id == Id.VSub_Pound:  # LENGTH
      if val.tag == value_e.StrArray:
        length = len(val.strs)
      else:
        length = len(val.s)
      return runtime.Str(str(length))
    else:
      raise NotImplementedError(op_id)

  def _ApplySuffixOp(self, defined, val, part):
    # if the op does NOT have colon
    #use_default = not defined
    # NOTE: You could have both prefix and suffix
    if part.suffix_op and LookupKind(part.suffix_op.op_id) in (
        Kind.VOp1, Kind.VOp2):
      op = part.suffix_op

      # NOTES:
      # - These are VECTORIZED on arrays
      #   - I want to allow this with my shell dialect: @{files|slice 1
      #   2|upper} does the same thing to all of them.
      # - How to do longest and shortest possible match?  bash and mksh both
      #   call fnmatch() in a loop, with possible short-circuit optimizations.
      #   - TODO: Write a test program to show quadratic behavior?
      #   - original AT&T ksh has special glob routines that returned the match
      #   positions.
      #   Implementation:
      #   - Test if it is a LITERAL or a Glob.  Then do a plain string
      #   operation.
      #   - If it's a glob, do the quadratic algorithm.
      #   - NOTE: bash also has an optimization where it extracts the LITERAL
      #   parts of the string, and does a prematch.  If none of them match,
      #   then it SKIPs the quadratic algorithm.
      #   - The real solution is to compile a glob to RE2, but I want to avoid
      #   that dependency right now... libc regex is good for a bunch of
      #   things.
      # - Bash has WIDE CHAR support for this.  With wchar_t.
      #   - All sorts of functions like xdupmbstowcs
      #
      # And then pat_subst() does some special cases.  Geez.

      # prefix strip
      if op.op_id == Id.VOp1_DPound:
        pass
      elif op.op_id == Id.VOp1_Pound:
        pass

      # suffix strip
      elif op.op_id == Id.VOp1_Percent:
        print(op.words)
        argv = []
        for w in op.words:
          val2 = self._EvalParts(w)
          val2.AppendTo(argv)

        # TODO: Evaluate words, and add the SPACE VALUES, getting a single
        # string.  And then test if it's a literal or glob.
        suffix = argv[0]

        if val.IsArray():
          # TODO: Vectorize it
          raise NotImplementedError
        else:
          s = val.s
          if s.endswith(suffix):
            s = s[:-len(suffix)]
            val = runtime.StringPartValue(s)

      elif op.op_id == Id.VOp1_DPercent:
        pass

      # Patsub, vectorized
      elif op.op_id == Id.VOp2_Slash:
        pass

      # Either string slicing or array slicing.  However string slicing has a
      # unicode problem?  TODO: Test bash out.  We need utf-8 parsing in C++?
      #
      # Or maybe have a different operator for byte slice and char slice.
      elif op.op_id == Id.VOp2_Colon:
        pass

      else:
        raise NotImplementedError(op)

    return defined, val

  def _EvalDoubleQuotedPart(self, part):
    # Example of returning array:
    # $ a=(1 2); b=(3); $ c=(4 5)
    # $ argv "${a[@]}${b[@]}${c[@]}"
    # ['1', '234', '5']

    strs = ['']  # TODO: Use fragment style?
    for p in part.parts:
      part_val = self._EvalWordPart(p, quoted=True)
      assert isinstance(part_val, runtime.part_value), (p, part_val)
      if part_val.tag == part_value_e.StringPartValue:
        strs[-1] += part_val.s
      else:
        for i, s in enumerate(part_val.strs):
          if i == 0:
            strs[-1] += s
          else:
            strs.append(s)

    if len(strs) == 1:
      val = runtime.StringPartValue(strs[0], False, False)
    else:
      val = runtime.ArrayPartValue(strs)
    return val

  def _EmptyStringPartOrError(self, part_val, quoted):
    assert isinstance(part_val, runtime.part_value), part_val
    if part_val.tag == value_e.Undef:
      if self.exec_opts.nounset:
        # stack will unwind
        token = None
        # TODO: Print the name.  Need to have the ast for varsub.  BracedVarSub
        # should have a token?
        #tb = self.mem.GetTraceback(token)
        self._AddErrorContext('Undefined variable')
        raise _EvalError()
      else:
        return runtime.StringPartValue('', not quoted, not quoted)
    else:
      return part_val

  def _EvalWordPart(self, part, quoted=False):
    """Evaluate a word part.

    Returns:
      part_value

    Raises:
      _EvalError
    """
    if part.tag == word_part_e.ArrayLiteralPart:
      raise AssertionError(
          'Array literal should have been handled at word level')

    elif part.tag == word_part_e.LiteralPart:
      s = part.token.val
      do_split_elide = False
      do_glob = True
      return runtime.StringPartValue(s, do_split_elide, do_glob)

    elif part.tag == word_part_e.EscapedLiteralPart:
      val = part.token.val
      assert len(val) == 2, val  # e.g. \*
      assert val[0] == '\\'
      s = val[1]
      return runtime.StringPartValue(s, False, False)

    elif part.tag == word_part_e.SingleQuotedPart:
      s = ''.join(t.val for t in part.tokens)
      return runtime.StringPartValue(s, False, False)

    elif part.tag == word_part_e.DoubleQuotedPart:
      return self._EvalDoubleQuotedPart(part)

    elif part.tag == word_part_e.CommandSubPart:
      # TODO: If token is Id.Left_ProcSubIn or Id.Left_ProcSubOut, we have to
      # supply something like /dev/fd/63.
      return self._EvalCommandSub(part.command_list, quoted)

    elif part.tag == word_part_e.SimpleVarSub:
      # 1. Evaluate from (var_name, var_num, token) -> defined, value
      if part.token.id == Id.VSub_Name:
        var_name = part.token.val[1:]
        val = self.mem.Get(var_name)
      elif part.token.id == Id.VSub_Number:
        var_num = int(part.token.val[1:])
        val = self._EvalVarNum(var_num)
      else:
        val = self._EvalSpecialVar(part.token.id, quoted)

      part_val = _ValueToPartValue(val, quoted)
      part_val = self._EmptyStringPartOrError(part_val, quoted)
      return part_val

    elif part.tag == word_part_e.BracedVarSub:
      # 1. Evaluate from (var_name, var_num, token) -> defined, value
      if part.token.id == Id.VSub_Name:
        var_name = part.token.val
        val = self.mem.Get(var_name)
        log('EVAL NAME %s -> %s', var_name, val)

      elif part.token.id == Id.VSub_Number:
        var_num = int(part.token.val)
        val = self._EvalVarNum(var_num)
      else:
        val = self._EvalSpecialVar(part.token.id, quoted)

      # Later this could be part_val, if you implemented named references.
      if part.prefix_op:
        val = self._ApplyPrefixOp(val, part.prefix_op)
        # return part_val
        # TODO: check if undefined

      # The bracket_op changes it to part_val.
      # That means the that test ops and suffix need to work on part_val:
      # ${a[2]%6}
      # ${a[2]:-undefined}
      #
      # Prefix ops need to work on val:
      # ${!a[*]} is still the length of the array, not of the string.

      #log("VAL %s", val)
      if part.bracket_op:
        if val.tag == value_e.Undef:
          part_val = runtime.UndefPartValue()
        elif val.tag == value_e.Str:
          raise AssertionError("Can't apply bracket op to string")
        elif val.tag == value_e.StrArray:
          part_val = self._ApplyBracketOp(val, part.bracket_op, quoted)
      else:
        if val.tag == value_e.Undef:
          part_val = runtime.UndefPartValue()
        elif val.tag == value_e.Str:
          part_val = runtime.StringPartValue(val.s, not quoted, not quoted)
        elif val.tag == value_e.StrArray:
          part_val = runtime.ArrayPartValue(val.strs)

      did_suffix = False
      if part.suffix_op and LookupKind(part.suffix_op.op_id) == Kind.VTest:
        new_part_val, effect = self._ApplyTestOp(part_val, part.suffix_op)
        did_suffix = True

        if effect == Effect.Eval:
          defined = True
          part_val = new_part_val

        elif effect == Effect.Error:
          raise NotImplementedError

        elif effect == Effect.Assign:
          raise NotImplementedError

        else:
          pass  # do nothing, may still be undefined

      part_val = self._EmptyStringPartOrError(part_val, quoted)

      if part.suffix_op and not did_suffix:
        part_val = self._ApplySuffixOp(part_val, part)

      #print('APPLY OPS', var_name, '->', defined, val)
      return part_val

    elif part.tag == word_part_e.TildeSubPart:
      # We never parse a quoted string into a TildeSubPart.
      assert not quoted
      s = self._EvalTildeSub(part.prefix)
      return runtime.StringPartValue(s, False, False)

    elif part.tag == word_part_e.ArithSubPart:
      arith_ev = expr_eval.ArithEvaluator(self.mem, self.word_ev)
      if arith_ev.Eval(part.anode):
        num = arith_ev.Result()
        return runtime.StringPartValue(str(num), True, True)
      else:
        self.error_stack.extend(arith_ev.Error())
        raise _EvalError()

    else:
      raise AssertionError(part.tag)


class _WordEvaluator:
  """Abstract base class for word evaluators.

  Public entry points:
    EvalWordToString
    EvalWordToAny
    EvalWordSequence
    Error
  """
  def __init__(self, mem, exec_opts, part_ev):
    self.mem = mem
    self.exec_opts = exec_opts

    self.part_ev = part_ev
    self.globber = Globber(exec_opts)

    self.error_stack = []

  def _AddErrorContext(self, msg, *args):
    if msg:
      msg = msg % args
    self.error_stack.append(msg)

  def Error(self):
    return self.error_stack

  def _EvalParts(self, word):
    """Evaluate a word.

    This is used in the following contexts:
    - Regular commands via _EvalWordSequence(): WITH globbing and word splitting
    - Evaluating redirect words: no globbing or word splitting
    - Right hand side of assignments and environments -- no globbing or word
      splitting
    - [[ context
      - no word splitting
      - but do_glob=True when on RHS of ==
        - we will later use in fnmatch (not glob())
      - elide_empty=False

    Args:
      w: word to evaluate
      ifs: None if we don't want any word splitting.  Or a bunch of
        characters.
      do_glob: Whether we are performing globs AFTER this.  This means that
        quoted literal glob metacharacters need to start with \.  e.g. "*" and
        '*' turn into \*.  But other metacharacters must be left alone.
      elide_empty: whether empty words turn into EmptyUnquoted

    Returns:
      part_value[]
    """
    assert isinstance(word, ast.CompoundWord), \
        "Expected CompoundWord, got %s" % word

    part_vals = []
    for p in word.parts:
      v = self.part_ev._EvalWordPart(p, quoted=False)  # may raise
      part_vals.append(v)
    return part_vals

  def EvalWordToString(self, word, do_fnmatch=False):
    """
    Used for redirect arg, ControlFlow arg, ArithWord, BoolWord, etc.

    do_fnmatch is true for case $pat and RHS of [[ == ]].

    pat="*.py"
    case $x in
      $pat) echo 'matches glob pattern' ;;
      "$pat") echo 'equal to glob string' ;;  // must be glob escaped
    esac
    """
    strs = []
    part_vals = []
    for part in word.parts:
      part_val = self.part_ev._EvalWordPart(part, quoted=False)  # may raise
      if part_val.tag != part_value_e.StringPartValue:
        # TODO: Better error message
        self._AddErrorContext("Only string parts are allowed", word=word)
        return False, None
      part_vals.append(part_val)
      if do_fnmatch:
        if part_val.do_glob:
          strs.append(part_val.s)
        else:
          strs.append(GlobEscape(part_val.s))
      else:
        strs.append(part_val.s)

    return True, runtime.Str(''.join(strs))

  def EvalWordToAny(self, word, glob_escape=False):
    """
    Used for RHS of assignment

    Also used for default value?  e.g. "${a:-"a" "b"}" and so forth.

    Returns:
      arg_value
      Or maybe just string?  Whatever would go in ConstArg and GlobArg.
      But you don't need to distinguish it later.
      You could also have EvalWord and EvalGlobWord methods or EvalPatternWord
    """
    try:
      # Special case for a=(1 2).  ArrayLiteralPart won't appear in words that
      # don't look like assignments.
      if (len(word.parts) == 1 and 
          word.parts[0].tag == word_part_e.ArrayLiteralPart):
        array_words = word.parts[0].words
        words = braces.BraceExpandWords(array_words)
        strs = self._EvalWordSequence(words)
        #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
        return True, runtime.StrArray(strs)

      part_vals = self._EvalParts(word)
      #log('part_vals %s', part_vals)

      # Instead of splitting, do a trivial transformation to frag array.
      # Example:
      # foo="-$@-${a[@]}-" requires fragment, reframe, and simple join
      frag_arrays = []
      for p in part_vals:
        if p.tag == part_value_e.StringPartValue:
          frag_arrays.append([runtime.fragment(p.s, False, False)])
        elif p.tag == part_value_e.ArrayPartValue:
          frag_arrays.append(
              [runtime.fragment(s, False, False) for s in p.strs])
        else:
          raise AssertionError

      frag_arrays = _Reframe(frag_arrays)
      #log('frag_arrays %s', frag_arrays)

      # Simple join
      args = []
      for frag_array in frag_arrays:
        args.append(''.join(frag.s for frag in frag_array))

      # Example:
      # a=(1 2)
      # b=$a  # one word
      # c="${a[@]}"  # two words
      if len(args) == 1:
        val = runtime.Str(args[0])
      else:
        # NOTE: For bash compatibility, could have an option to join them here.
        # foo="-$@-${a[@]}-"  -- join with IFS again, like "$*" ?
        # Or maybe do that in cmd_exec in assignment.
        val = runtime.StrArray(args)

      return True, val
    except _EvalError:
      return False, None

  def _EvalWordAndReframe(self, word):
    """Helper for _EvalWordSequence.
    
    Used in command, array, and foreach context.

    Args:
      word: CompoundWord
    Returns:
      val: runtime.value
    """
    part_vals = self._EvalParts(word)
    #log('After _EvalParts %s', part_vals)
    ifs = _GetIfs(self.mem)
    frag_arrays = _SplitPartsIntoFragments(part_vals, ifs)
    #log('After split %s', frag_arrays)
    frag_arrays = _Reframe(frag_arrays)

    # TODO: Loop over each one, only glob it if it's a GlobArg.
    #argv = self.globber.Glob(arg_vals)

    glob_escape = not self.exec_opts.noglob
    args = _JoinElideEscape(frag_arrays, glob_escape=glob_escape)
    #log('After _JoinElideEscape %s', frag_arrays)
    return args

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
      args = self._EvalWordAndReframe(w)
      #log('A %s', args)
      for arg in args:
        if arg.tag == arg_value_e.ConstArg:
          argv.append(arg.s)
        elif arg.tag == arg_value_e.GlobArg:
          results = self.globber.Expand(arg.s)
          #log('Glob Expand %s to %s', arg.s, results)
          argv.extend(results)
        else:
          raise AssertionError(arg.tag)

    #log('ARGV %s', argv)
    return argv

  def EvalWordSequence(self, words):
    try:
      return self._EvalWordSequence(words)
    except _EvalError:
      return None


class _NormalPartEvaluator(_WordPartEvaluator):
  """The Executor uses this to evaluate words."""

  def __init__(self, mem, exec_opts, ex, word_ev):
    _WordPartEvaluator.__init__(self, mem, exec_opts, word_ev)
    self.ex = ex

  def _EvalCommandSub(self, node, quoted):
    p = self.ex._GetProcessForNode(node)
    # NOTE: We could do an optimization for pipelines.  Pick the last
    # process element, and do pi.procs[-1].CaptureOutput()
    stdout = []
    p.CaptureOutput(stdout)
    status = p.Run()

    # Runtime errors:
    # what if the command sub was "echo foo > $@".  That is invalid.  Then
    # Return false here.  How do we get that value from the Process then?  Do
    # we use a special return value?

    # I think $() does a strip basically?
    # argv $(echo ' hi')$(echo bye) -> hibye
    s = ''.join(stdout).strip()
    return runtime.StringPartValue(s, not quoted, not quoted)


class NormalWordEvaluator(_WordEvaluator):

  def __init__(self, mem, exec_opts, ex):
    part_ev = _NormalPartEvaluator(mem, exec_opts, ex, self)
    _WordEvaluator.__init__(self, mem, exec_opts, part_ev)


class _CompletionPartEvaluator(_WordPartEvaluator):
  """For completion.

  We are disabling command substitution for now.

  TODO: Also disable side effects!  Like ${a:=b} rather than ${a:-b}
  And also $(( a+=1 ))

  TODO: Unify with static_eval?  Completion allows more stuff like var names,
  and maybe words within arrays as well.
  """
  def __init__(self, mem, exec_opts, word_ev):
    _WordPartEvaluator.__init__(self, mem, exec_opts, word_ev)

  def _EvalCommandSub(self, node, quoted):
    # Just  return a dummy string?
    return runtime.StringPartValue(
        '__COMMAND_SUB_NOT_EXECUTED__', not quoted, not quoted)


class CompletionWordEvaluator(_WordEvaluator):

  def __init__(self, mem, exec_opts):
    part_ev = _CompletionPartEvaluator(mem, exec_opts, self)
    _WordEvaluator.__init__(self, mem, exec_opts, part_ev)
