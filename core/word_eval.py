#!/usr/bin/python
"""
word_eval.py - Evaluator for the word language.
"""

import glob
import os
import pwd
import re

from core import arith_eval  # ArithEval
try:
  from core import libc
except ImportError:
  from core import fake_libc as libc
from core.word_node import CompoundWord
from core.id_kind import Id
from core.value import Value


# Glob Helpers for WordParts.
# ! : - are metachars within character classes
GLOB_META_CHARS = r'\*?[]-:!'

def _GlobEscape(s):
  """
  For SingleQuotedPart, DoubleQuotedPart, and EscapedLiteralPart
  """
  escaped = ''
  for c in s:
    if c in GLOB_META_CHARS:
      escaped += '\\'
    escaped += c
  return escaped


def _GlobUnescape(s):  # used by cmd_exec
  """
  If there is no glob match, just unescape the string.
  """
  unescaped = ''
  i = 0
  n = len(s)
  while i < n:
    c = s[i]
    if c == '\\':
      assert i != n - 1, 'There should be no trailing single backslash!'
      i += 1
      c2 = s[i]
      if c2 in GLOB_META_CHARS:
        unescaped += c2
      else:
        raise AssertionError("Unexpected escaped character %r" % c2)
    else:
      unescaped += c
    i += 1
  return unescaped


def _GetIfs(mem):
  defined, val = mem.Get('IFS')
  if defined:
    is_str, ifs = val.AsString()
    assert is_str  # should have never been set as array
  else:
    ifs = ' \t\n'  # default for sh; default for oil is ''
  return ifs


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
  if not ifs:
    return [s]  # no splitting

  # print("IFS SPLIT %r %r" % (s, ifs))
  if ifs == ' \t\n':
    # Split by whitespace, and empty strings removed
    parts = _Split(s, ifs)
    return [p for p in parts if p]

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
  parts = regex.split(s)

  # Ignore at beginning and end.
  if not parts[0]:
    del parts[0]
  if parts and not parts[-1]:
    del parts[-1]

  return parts


def _AppendArray(strs, array, glob_escape=False):
  """
  Append 'array' to existing 'strs'.  The first one is joined.
  """
  empty = True
  for i, s in enumerate(array):
    if s:
      empty = False

    if glob_escape:
      s = _GlobEscape(s)

    if i == 0:
      strs[-1] += s
    else:
      strs.append(s)
  return empty


class _Evaluator(object):
  """Abstract base class."""

  def __init__(self, mem, exec_opts):
    self.mem = mem
    self.exec_opts = exec_opts
    self.error_stack = []

  def _AddErrorContext(self, msg, *args):
    if msg:
      msg = msg % args
    self.error_stack.append(msg)

  def Error(self):
    return self.error_stack

  def SetRegexMatches(self, matches):
    """For ~= to set the BASH_REMATCH array."""
    self.mem

  def EvalCommandSub(self, node):
    """
    Args:
      node: COMMAND_SUB node

    Returns:
       bool ok, Value v
    """
    raise NotImplementedError

  def EvalArithSub(self, anode):
    i = arith_eval.ArithEval(anode, self)
    #s = Eval
    return True, Value.FromString(str(i))

  def _EvalVar(self, name, quoted=False):
    """Evaluates the given variable in the current scope.

    Returns:
       bool ok, Value v
    """
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
    if name in ('@', '*'):
      if name == '@' and quoted:  # "$@" evaluates to an array
        argv = self.mem.GetArgv()
        val = Value.FromArray(argv)
        #print('$@', val)
        return True, val
      else:  # $@ $* "$*"
        argv = self.mem.GetArgv()
        val = Value.FromString(ifs[0].join(argv))
        return True, val

    elif name == '?':
      # TODO: Have to parse status somewhere.
      # External commands need WIFEXITED test.  What about subshells?
      return True, Value.FromString(str(self.mem.last_status))

    elif name == '#':
      argv = self.mem.GetArgv()
      s = str(len(argv))
      return True, Value.FromString(s)

    # TODO: $0 $1 ...

    else:
      # VarSubPart is for $foo, without qualifiers.
      defined, val = self.mem.Get(name)
      return defined, val

      if defined:
        # If there are no modifiers like a[@], add implicit a[0], as long as
        # exec option bash_array is set.
        #
        # TODO: $array is an error.  Only an explicit ${array[0]} or
        # ${array[@]} is valid.  This is compatible with bash, and makes it
        # easier to read and catch bugs.  We know the type at compile
        # time.  It makes it easier to apply VarOps with unsurprising
        # semantics.

        if self.exec_opts.bash_array:
          val = val.EvalToFirst()
        return True, val
      else:
        # TODO: MOVE down to EvalVarSub().  Test ops will change this.
        if self.exec_opts.nounset:
          # stack will unwind
          token = None
          # TODO: Need to have the ast for varsub.  VarSubPart should have a
          # token?
          #tb = self.mem.GetTraceback(token)
          self._AddErrorContext("Unset variable %s" % name)
          return False, None
        else:
          return True, Value.FromString('')

  def EvalVarSub(self, part, quoted=False):
    """
    Args:
      name: name of the variable to evaluate
      ops: list of VarOp to execute
      quoted: whether the var sub was double quoted

    """
    name = part.name
    ops = part.transform_ops  # TODO: fix

    # Possibilities: Array OR Index; then Test OR Transform

    # So instead of a list of ops, it should be optional IndexOp, optional
    # TestOp, optional TransformOp.

    # empty=''
    # $unset -> ''  EMPTY_UNQUOTED
    # ${unset:-foo} -> foo
    # ${unset-foo} -> foo

    # $empty -> ''
    # ${empty:-foo} -> foo
    # ${empty-foo} -> ''

    defined, val = self._EvalVar(name, quoted=quoted)
    #print('@@@', defined, val)

    array_ok = (name == '@')  # Don't need any op for array $@
    index_error = False  # test_op can suppress this

    if defined and part.bracket_op:
      vtype = part.bracket_op.vtype

      if vtype == Id.Arith_At:
        if val.IsArray():
          array_ok = True
        else:
          self._AddErrorContext("Can't index non-array with @")
          return False, None

      elif vtype == Id.Arith_Star:
        if val.IsArray():
          array_ok = True
        else:
          self._AddErrorContext("Can't index non-array with *")
          return False, None

      elif vtype == Id.VOp2_LBracket:
        array_ok = True
        is_array, a = val.AsArray()
        if is_array:
          anode = part.bracket_op.index_expr
          # TODO: This should propagate errors
          index = arith_eval.ArithEval(anode, self)
          ok = True
          if not ok:
            self._AddErrorContext(
                'Error evaluating arith sub in index expression')
            return False, None
          try:
            s = a[index]
          except IndexError:
            index_error = True
            defined = False
            val = None
          else:
            val = Value.FromString(s)

        else:  # it's a string
          raise NotImplementedError("String indexing not implemented")
      else:
        raise AssertionError(vtype)

    if defined and val.IsArray():
      if not array_ok:
        self._AddErrorContext(
            "Array was referenced without explicit index, e.g. ${a[@]} "
            "or ${a[0]}")
        return False, None

    # if the op does NOT have colon
    #use_default = not defined

    if part.test_op:
      vtype = part.test_op.vtype

      # TODO: Change this to a bit test.
      if vtype in (Id.VTest_ColonHyphen, Id.VTest_ColonEquals,
          Id.VTest_ColonQMark, Id.VTest_ColonPlus):
        is_falsey = not defined or val.IsEmptyString()
      else:
        is_falsey = not defined

      #print('!!',vtype, is_falsey)

      if vtype in (Id.VTest_ColonHyphen, Id.VTest_Hyphen):
        if is_falsey:
          argv = []
          ok, val2 = self.EvalCompoundWord(part.test_op.arg_word)
          if not ok:
            return False, None
          val2.AppendTo(argv)
          # TODO: This is roundabout
          val = Value.FromArray(argv)

          defined = True  # now we have a variable
          #print("DEFAULT", val)

      # TODO:
      # +  -- inverted test -- assign to default
      # ?  -- error
      # =  -- side effect assignment

      else:
        raise NotImplementedError(vtype)

    if not defined:
      # TODO: MOVE down to EvalVarSub().  Test ops will change this.
      if self.exec_opts.nounset:
        # stack will unwind
        token = None
        # TODO: Need to have the ast for varsub.  VarSubPart should have a
        # token?
        #tb = self.mem.GetTraceback(token)
        self._AddErrorContext("Unset variable %s" % name)
        return False, None
      else:
        print("UNDEFINED")
        # TODO: Isn't this where we do EMPTY_UNQUOTED?
        return True, Value.FromString('')

    for op in part.transform_ops:
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

      if op.vtype == VS_POUND:
        # LENGTH
        if val.IsArray():
          #print("ARRAY LENGTH", len(val.a))
          length = len(val.a)
        else:
          #print("STRING LENGTH", len(val.s))
          length = len(val.s)
        val = Value.FromString(str(length))

      # prefix strip
      elif op.vtype == Id.VOp1_DPound:
        pass
      elif op.vtype == Id.VOp1_Pound:
        pass

      # suffix strip
      elif op.vtype == Id.VOp1_Percent:
        print(op.words)
        argv = []
        for w in op.words:
          ok, val2 = self.EvalCompoundWord(w)
          if not ok:
            return False, None
          val2.AppendTo(argv)

        # TODO: Evaluate words, and add the SPACE VALUES, getting a single
        # string
        # And then test if it's a literal or glob.
        suffix = argv[0]

        if val.IsArray():
          # TODO: Vectorize it
          raise NotImplementedError
        else:
          s = val.s
          if s.endswith(suffix):
            s = s[:-len(suffix)]
            val = Value.FromString(s)

      elif op.vtype == Id.VOp1_DPercent:
        pass

      # Patsub, vectorized
      elif op.vtype == Id.VOp2_Slash:
        pass

      # Either string slicing or array slicing.  However string slicing has a
      # unicode problem?  TODO: Test bash out.  We need utf-8 parsing in C++?
      #
      # Or maybe have a different operator for byte slice and char slice.
      elif op.vtype == Id.VOp2_Colon:
        pass

      else:
        raise NotImplementedError(op)

    return True, val

  def EvalCompoundWord(self, word, ifs='', do_glob=False, elide_empty=True):
    """CompoundWord.Eval().

    This is used in the following contexts:
    - Evaluating redirect words: no glob and no word splitting
    - Right hand side of assignments -- no globbing
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

    Returns:
      Value -- empty unquoted, string, or array
    """
    assert isinstance(word, CompoundWord), "Exected CompoundWord, got %s" % word
    # assume we elide, unless we get something "significant"
    is_empty_unquoted = True
    ev = self

    strs = ['']
    for p in word.parts:
      ok, val = p.Eval(ev, quoted=False)  # NOT quoted
      if not ok:
        return False, Value.FromString('')
      assert isinstance(val, Value), val
      is_str, s = val.AsString()
      #print('-VAL', val, is_str)

      glob_escape = do_glob and not p.GlobsAreExpanded()

      if is_str:
        if p.IsSubst():  # Split substitutions
          # NOTE: Splitting is the same whether we are glob escaping or not
          split_parts = _IfsSplit(s, ifs)
          empty = _AppendArray(strs, split_parts, glob_escape=glob_escape)
          if not empty:
            is_empty_unquoted = False
        else:  # Don't split
          # Any non-subst parts, even '', means we don't elide.
          is_empty_unquoted = False
          if glob_escape:
            s = _GlobEscape(s)
          strs[-1] += s

      else:  # The result of a DoubleQuotedPart can be an array.
        #print('ARRAY', val.a)
        is_empty_unquoted = False
        # No glob escape because callee (e.g. DoubleQuotedPart) is responsible
        _AppendArray(strs, val.a, glob_escape=glob_escape)

    if elide_empty and is_empty_unquoted:
      val = Value.EmptyUnquoted()
    elif len(strs) == 1:
      val = Value.FromString(strs[0])
    else:
      val = Value.FromArray(strs)
    return True, val

  def ArithEvalWord(self, word):
    """Evaluate with the rules of $(( )).

    Dumb stuff like $(( $(echo 1)$(echo 2) + 1 ))  =>  13  is possible.

    0xAB -- hex constant
    010 -- octable constant
    64#z -- arbitary base constant
    bare word: vairable
    quoted word: string
    """
    ok, val = self.EvalCompoundWord(word, elide_empty=False)
    if not ok:
      return False, 0
    is_str, s = val.AsString()
    if not is_str:
      # TODO: Error message: expected string but got integer
      return False, 0

    if s.startswith('0x'):
      try:
        integer = int(s, 16)
      except ValueError:
        # TODO: Show line number
        print('Invalid hex constant %r' % s)
        return False, 0
      return True, integer

    if s.startswith('0'):
      try:
        integer = int(s, 8)
      except ValueError:
        # TODO: Show line number
        print('Invalid octal constant %r' % s)
        return False, 0
      return True, integer

    if '#' in s:
      b, digits = s.split('#', 1)
      try:
        base = int(b)
      except ValueError:
        print('Invalid base for numeric constant %r' % b)
        return False, 0

      integer = 0
      n = 1
      for char in digits:
        if 'a' <= char and char <= 'z':
          digit = ord(char) - ord('a') + 10
        elif 'A' <= char and char <= 'Z':
          digit = ord(char) - ord('A') + 36
        elif char == '@':  # horrible syntax
          digit = 62
        elif char == '_':
          digit = 63
        elif char.isdigit():
          digit = int(char)
        else:
          print('Invalid digits for numeric constant %r' % digits)
          return False, 0

        integer += digit * n
        n *= base
      return True, integer

    # Plain integer
    try:
      integer = int(s)
    except ValueError:
      print("%r does not look like an integer" % s)
      return False, 0
    return True, integer

  def BoolEvalWord(self, word, do_glob=False):
    """Evaluate with the rules of [[."""
    return self.EvalCompoundWord(word, do_glob=do_glob, elide_empty=False)

  def EvalTildeSub(self, prefix):
    """Evaluates ~ and ~user.

    Args:
      prefix: The tilde prefix (possibly empty)
    """
    if prefix == '':
      # First look up the HOME var, and then env var
      defined, val = self.mem.Get('HOME')
      if defined:
        return True, val

      # If no env, fall back on /etc/passwd
      uid = os.getuid()
      try:
        e = pwd.getpwuid(uid)
      except KeyError:
        s = '~' + prefix
      else:
        s = e.pw_dir

      return True, Value.FromString(s)

    # http://linux.die.net/man/3/getpwnam
    try:
      e = pwd.getpwnam(prefix)
    except KeyError:
      s = '~' + prefix
    else:
      s = e.pw_dir

    return True, Value.FromString(s)

  def EvalArrayLiteralPart(self, part):
    #print(self.words, '!!!')
    array = []
    for w in part.words:

      # - perform splitting when necessary?
      # set IFS here?
      ok, val = self.EvalCompoundWord(w)

      if not ok:
        # TODO: show errors?
        return False, None
      # NOTE: For now, we enforce homogeneous arrays of strings.  This is for
      # the shell / proc dialect.  For func dialect, we can have heterogeneous
      # arrays.
      is_str, s = val.AsString()
      if is_str:
        array.append(s)
      else:
        # TODO:
        # - interpolate array into array
        raise AssertionError('Expected string')

    return True, Value.FromArray(array)

  def EvalDoubleQuotedPart(self, part):
    # NOTE: quoted arg isn't used
    strs = ['']
    for p in part.parts:
      ok, val = p.Eval(self, quoted=True)
      if not ok:
        return False, Value.FromString('')  # ERROR

      assert isinstance(val, Value), val
      is_str, s = val.AsString()
      if is_str:
        strs[-1] += s
      else:
        _AppendArray(strs, val.a)  # top level escape

    # TODO: Fix bug.  "$@" could have only one entry, but we still want it to
    # be an array!
    if len(strs) == 1:
      val = Value.FromString(strs[0])
    else:
      val = Value.FromArray(strs)
    return True, val

  def _ExpandGlobs(self, argv):
    result = []
    for arg in argv:
      # TODO: Only try to glob if there are any glob metacharacters.
      try:
        #g = glob.glob(arg)
        g = libc.glob(arg)
      except Exception as e:
        # - [C\-D] is invalid in Python?  Regex compilation error.
        # - [:punct:] not supported
        print("Error expanding glob %r: %s" % (arg, e))
        raise
      #print('G', arg, g)

      if g:
        result.extend(g)
      else:
        u = _GlobUnescape(arg)
        result.append(u)
    return result

  def EvalWords(self, words):
    """Turns a list of Words into a list of strings.

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

    argv = []
    ifs = _GetIfs(self.mem)

    # NOTE: -f sets noglob
    do_glob = not self.exec_opts.noglob

    argv = []
    for w in words:
      ok, val = self.EvalCompoundWord(w, ifs=ifs, do_glob=do_glob)

      if not ok:
        self._AddErrorContext('Error evaluating word %s', w)
        return None
      val.AppendTo(argv)

    if do_glob:
      # NOTE: failglob could cause failure?  Do other shells have it?
      argv = self._ExpandGlobs(argv)
    return argv

  def EvalEnv(self, more_env):
    result = {}
    for name, expr in more_env:
      ok, val = self.EvalCompoundWord(expr)
      # What happens here?  Undefined variable?
      if not ok:
        self._AddErrorContext("Error evaluating expression %s = %s", name,
            expr)
        return None
      is_str, s = val.AsString()
      if not is_str:
        self._AddErrorContext("Env vars should be strings, got %s = %s", name,
            val)
        return None

      # Set each var so the next one can reference it.  Example:
      # FOO=1 BAR=$FOO ls /
      pairs = [(name, val)]
      self.mem.SetLocal(pairs, 0)

      result[name] = s
    return result


class NormalEvaluator(_Evaluator):
  """The Executor uses this to evaluate words."""

  def __init__(self, mem, exec_opts, ex):
    _Evaluator.__init__(self, mem, exec_opts)
    self.ex = ex

  def EvalCommandSub(self, node):
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

    ok = True

    # I think $() does a strip basically?
    # argv $(echo ' hi')$(echo bye) -> hibye
    s = ''.join(stdout).strip()
    return ok, Value.FromString(s)


class CompletionEvaluator(_Evaluator):
  """For completion.

  We are disabling command substitution for now.

  TODO: Also disable side effects!  Like ${a:=b} rather than ${a:-b}
  And also $(( a+=1 ))
  """
  def __init__(self, mem, exec_opts):
    _Evaluator.__init__(self, mem, exec_opts)

  def EvalCommandSub(self, node):
    # Just  return a dummy string?
    return True, Value.FromString('__COMMAND_SUB_NOT_EXECUTED__')
