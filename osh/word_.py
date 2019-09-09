"""
word.py - Utility functions for words, e.g. treating them as "tokens".
"""

from _devbuild.gen.id_kind_asdl import (Id, Kind, Id_t, Kind_t)
from _devbuild.gen.syntax_asdl import (
    token,
    word_part, word_part_t, word_part_e,
    word_part__ArrayLiteral, word_part__AssocArrayLiteral,
    word_part__Literal, word_part__EscapedLiteral,
    word_part__SingleQuoted, word_part__DoubleQuoted,
    word_part__SimpleVarSub, word_part__BracedVarSub, word_part__TildeSub,
    word_part__CommandSub, word_part__ArithSub, word_part__BracedTuple,
    word_part__ExtGlob, word_part__Splice, word_part__FuncCall,

    word, word_t, 
    word__Compound, word__Token, word__Empty, word__BracedTree,
    word__String,

    lhs_expr__LhsName,
)
from asdl import const
from core import util
from core.meta import LookupKind

from typing import Tuple, Optional, List, TYPE_CHECKING
if TYPE_CHECKING:
  from core.util import _ErrorWithLocation

p_die = util.p_die


def _LiteralId(p):
  # type: (word_part_t) -> Id_t
  """
  If the WordPart consists of a single literal token, return its Id.  Used for
  Id.KW_For, or Id.RBrace, etc.
  """
  if isinstance(p, word_part__Literal):
    return p.token.id
  else:
    return Id.Undefined_Tok  # unequal to any other Id


def _EvalWordPart(part):
  # type: (word_part_t) -> Tuple[bool, str, bool]
  """Evaluate a WordPart at PARSE TIME.

  Used for:

  1. here doc delimiters
  2. function names
  3. for loop variable names
  4. Compiling constant regex words at parse time
  5. a special case for ${a////c} to see if we got a leading slash in the
  pattern.

  Returns:
    3-tuple of
      ok: bool, success.  If there are parts that can't be statically
        evaluated, then we return false.
      value: a string (not Value)
      quoted: whether any part of the word was quoted
  """
  if isinstance(part, word_part__ArrayLiteral):
    # Array literals aren't good for any of our use cases.  TODO: Rename
    # EvalWordToString?
    return False, '', False

  elif isinstance(part, word_part__AssocArrayLiteral):
    return False, '', False

  elif isinstance(part, word_part__Literal):
    return True, part.token.val, False

  elif isinstance(part, word_part__EscapedLiteral):
    val = part.token.val
    assert len(val) == 2, val  # e.g. \*
    assert val[0] == '\\'
    s = val[1]
    return True, s, True

  elif isinstance(part, word_part__SingleQuoted):
    s = ''.join(t.val for t in part.tokens)
    return True, s, True

  elif isinstance(part, word_part__DoubleQuoted):
    ret = ''
    for p in part.parts:
      ok, s, _ = _EvalWordPart(p)
      if not ok:
        return False, '', True
      ret += s

    return True, ret, True  # At least one part was quoted!

  elif part.tag in (
      word_part_e.CommandSub, word_part_e.SimpleVarSub,
      word_part_e.BracedVarSub, word_part_e.TildeSub,
      word_part_e.ArithSub, word_part_e.ExtGlob,
      word_part_e.Splice):
    return False, '', False

  else:
    raise AssertionError(part.__class__.__name__)


def StaticEval(w):
  # type: (word_t) -> Tuple[bool, str, bool]
  """Evaluate a Compound at PARSE TIME."""
  ret = ''
  quoted = False

  # e.g. for ( instead of for (( is a token word
  if not isinstance(w, word__Compound):
    return False, ret, quoted

  for part in w.parts:
    ok, s, q = _EvalWordPart(part)
    if not ok:
      return False, '', quoted
    if q:
      quoted = True  # at least one part was quoted
    ret += s
  return True, ret, quoted


def LeftMostSpanForPart(part):
  # type: (word_part_t) -> int
  # TODO: Write unit tests in ui.py for error values

  if isinstance(part, word_part__ArrayLiteral):
    return part.spids[0]  # ( location

  elif isinstance(part, word_part__AssocArrayLiteral):
    return part.spids[0]  # ( location

  elif isinstance(part, word_part__Literal):
    # Just use the token
    return part.token.span_id

  elif isinstance(part, word_part__EscapedLiteral):
    return part.token.span_id

  elif isinstance(part, word_part__SingleQuoted):
    return part.spids[0]  # single quote location

  elif isinstance(part, word_part__DoubleQuoted):
    return part.spids[0]  # double quote location

  elif isinstance(part, word_part__SimpleVarSub):
    return part.token.span_id

  elif isinstance(part, word_part__BracedVarSub):
    return part.spids[0]

  elif isinstance(part, word_part__CommandSub):
    return part.spids[0]

  elif isinstance(part, word_part__TildeSub):
    return part.token.span_id

  elif isinstance(part, word_part__ArithSub):
    # begin, end
    return part.spids[0]

  elif isinstance(part, word_part__ExtGlob):
    # This is the smae as part.op.span_id, but we want to be consistent with
    # left/right.  Not sure I want to add a right token just for the spid.
    return part.spids[0]
    #return part.op.span_id  # e.g. @( is the left-most token

  elif isinstance(part, word_part__BracedTuple):
    return const.NO_INTEGER

  elif isinstance(part, word_part__Splice):
    return part.name.span_id

  elif isinstance(part, word_part__FuncCall):
    return part.name.span_id  # @f(x) or $f(x)

  else:
    raise AssertionError(part.__class__.__name__)


def _RightMostSpanForPart(part):
  # type: (word_part_t) -> int
  # TODO: Write unit tests in ui.py for error values

  if isinstance(part, word_part__ArrayLiteral):
    # TODO: Return )
    return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif isinstance(part, word_part__Literal):
    # Just use the token
    return part.token.span_id

  elif isinstance(part, word_part__EscapedLiteral):
    return part.token.span_id

  elif isinstance(part, word_part__SingleQuoted):
    return part.spids[1]  # right '

  elif isinstance(part, word_part__DoubleQuoted):
    return part.spids[1]  # right "

  elif isinstance(part, word_part__SimpleVarSub):
    return part.token.span_id

  elif isinstance(part, word_part__BracedVarSub):
    spid = part.spids[1]  # right }
    assert spid != const.NO_INTEGER
    return spid

  elif isinstance(part, word_part__CommandSub):
    return part.spids[1]

  elif isinstance(part, word_part__TildeSub):
    return const.NO_INTEGER

  elif isinstance(part, word_part__ArithSub):
    return part.spids[1]

  elif isinstance(part, word_part__ExtGlob):
    return part.spids[1]

  else:
    raise AssertionError(part.tag)


def LeftMostSpanForWord(w):
  # type: (word_t) -> int
  if isinstance(w, word__Compound):
    if w.parts:
      return LeftMostSpanForPart(w.parts[0])
    else:
      # This is possible for empty brace sub alternative {a,b,}
      return const.NO_INTEGER

  elif isinstance(w, word__Token):
    return w.token.span_id

  elif isinstance(w, word__Empty):
    return const.NO_INTEGER

  elif isinstance(w, word__BracedTree):
    # This should always have one part?
    return LeftMostSpanForPart(w.parts[0])

  elif isinstance(w, word__String):
    return w.spids[0]  # See _StringWordEmitter in osh/builtin_bracket.py

  else:
    raise AssertionError(w)


def RightMostSpanForWord(w):
  # type: (word_t) -> int
  """Needed for here doc delimiters."""
  if isinstance(w, word__Compound):
    if len(w.parts) == 0:
      # TODO: Use Empty instead
      raise AssertionError("Compound shouldn't be empty")
    else:
      end = w.parts[-1]
      return _RightMostSpanForPart(end)

  elif isinstance(w, word__Empty):
    return const.NO_INTEGER

  assert isinstance(w, word__Token)
  return w.token.span_id


# From bash, general.c, unquoted_tilde_word():
# POSIX.2, 3.6.1:  A tilde-prefix consists of an unquoted tilde character at
# the beginning of the word, followed by all of the characters preceding the
# first unquoted slash in the word, or all the characters in the word if there
# is no slash...If none of the characters in the tilde-prefix are quoted, the
# characters in the tilde-prefix following the tilde shell be treated as a
# possible login name. 
#define TILDE_END(c)    ((c) == '\0' || (c) == '/' || (c) == ':')
#
# So an unquoted tilde can ALWAYS start a new lex mode?  You respect quotes and
# substitutions.
#
# We only detect ~Lit_Chars and split.  So we might as well just write a regex.

def TildeDetect(w):
  # type: (word_t) -> Optional[word_t]
  """Detect tilde expansion in a word.

  It might begin with  Literal that needs to be turned into a TildeSub.
  (It depends on whether the second token begins with slash).

  If so, it return a new word.  Otherwise return None.

  NOTE:
  - The regex for Lit_TildeLike could be expanded.  Right now it's
    conservative, like Lit_Chars without the /.
  - It's possible to write this in a mutating style, since only the first token
    is changed.  But note that we CANNOT know this during lexing.
  """
  # NOTE: BracedTree, Empty, etc. can't be tilde expanded
  if not isinstance(w, word__Compound):
    return None

  assert w.parts, w

  part0 = w.parts[0]
  if _LiteralId(part0) != Id.Lit_TildeLike:
    return None
  assert isinstance(part0, word_part__Literal)  # for MyPy

  if len(w.parts) == 1:  # can't be zero
    tilde_part = word_part.TildeSub(part0.token)
    return word.Compound([tilde_part])

  part1 = w.parts[1]
  # NOTE: We could inspect the raw tokens.
  if _LiteralId(part1) == Id.Lit_Chars:
    assert isinstance(part1, word_part__Literal)  # for MyPy
    if part1.token.val.startswith('/'):
      tilde_part_ = word_part.TildeSub(part0.token)  # type: word_part_t
      return word.Compound([tilde_part_] + w.parts[1:])

  # It could be something like '~foo:bar', which doesn't have a slash.
  return None


def TildeDetectAll(words):
  # type: (List[word_t]) -> List[word_t]
  out = []
  for w in words:
    t = TildeDetect(w)
    if t:
      out.append(t)
    else:
      out.append(w)
  return out


def HasArrayPart(w):
  # type: (word_t) -> bool
  """Used in cmd_parse."""
  assert isinstance(w, word__Compound)

  for part in w.parts:
    if isinstance(part, word_part__ArrayLiteral):
      return True
  return False


def AsFuncName(w):
  # type: (word__Compound) -> str
  """
  Returns a valid function name, or the empty string.

  TODO: Maybe use this regex to validate:

  FUNCTION_NAME_RE = r'[^{}\[\]=]*'
  
  Bash is very lenient, but that would disallow confusing characters, for
  better error messages on a[x]=(), etc.
  """
  assert isinstance(w, word__Compound)

  ok, s, quoted = StaticEval(w)
  # Function names should not have quotes
  if not ok or quoted:
    return ''
  return s


def LooksLikeArithVar(w):
  # type: (word_t) -> Optional[token]
  """Return a token if this word looks like an arith var.

  NOTE: This can't be combined with DetectAssignment because VarLike and
  ArithVarLike must be different tokens.  Otherwise _ReadCompoundWord will be
  confused between array assigments foo=(1 2) and function calls foo(1, 2).
  """
  if not isinstance(w, word__Compound):
    return None

  if len(w.parts) != 1:
    return None

  part0 = w.parts[0]
  if _LiteralId(part0) != Id.Lit_ArithVarLike:
    return None
  assert isinstance(part0, word_part__Literal)  # for MyPy

  return part0.token


def IsVarLike(w):
  # type: (word__Compound) -> bool
  """Tests whether a word looks like FOO=bar.

  This is a quick test for the command parser to distinguish:
  
  func() { echo hi; }
  func=(1 2 3)
  """
  assert isinstance(w, word__Compound)
  if len(w.parts) == 0:
    return False

  part0 = w.parts[0]
  return _LiteralId(w.parts[0]) == Id.Lit_VarLike


def DetectAssignment(w):
  # type: (word_t) -> Tuple[Optional[token], Optional[token], int]
  """Detects whether a word looks like FOO=bar or FOO[x]=bar.

  Returns:
    left_token or None   # Lit_VarLike, Lit_ArrayLhsOpen, or None if it's not an
                         # assignment
    close_token,         # Lit_ArrayLhsClose if it was detected, or None
    part_offset          # where to start the value word, 0 if not an assignment

  Cases:

  s=1
  s+=1
  s[x]=1
  s[x]+=1

  a=()
  a+=()
  a[x]=(
  a[x]+=()  # We parse this (as bash does), but it's never valid because arrays
            # can't be nested.
  """
  assert isinstance(w, word__Compound)
  n = len(w.parts)
  if n == 0:
    return None, None, 0

  part0 = w.parts[0]
  id0 = _LiteralId(part0)
  if id0 == Id.Lit_VarLike:
    assert isinstance(part0, word_part__Literal)  # for MyPy
    return part0.token, None, 1  # everything after first token is the value

  if id0 == Id.Lit_ArrayLhsOpen:
    assert isinstance(part0, word_part__Literal)  # for MyPy

    # NOTE that a[]=x should be an error.  We don't want to silently decay.
    if n < 2:
      return None, None, 0
    for i in xrange(1, n):
      part = w.parts[i]
      if _LiteralId(part) == Id.Lit_ArrayLhsClose:
        assert isinstance(part, word_part__Literal)  # for MyPy
        return part0.token, part.token, i+1

  # Nothing detected.  Could be 'foobar' or a[x+1+2/' without the closing ].
  return None, None, 0


def DetectAssocPair(w):
  # type: (word__Compound) -> Optional[Tuple[word__Compound, word__Compound]]
  """
  Like DetectAssignment, but for A=(['k']=v ['k2']=v)

  The key and the value are both strings.  So we just pick out word_part.
  Unlike a[k]=v, A=([k]=v) is NOT ambiguous, because the [k] syntax is only used
  for associative array literals, as opposed to indexed array literals.
  """
  parts = w.parts
  if _LiteralId(parts[0]) != Id.Lit_LBracket:
    return None

  n = len(parts)
  for i in xrange(n):
    id_ = _LiteralId(parts[i])
    if id_ == Id.Lit_ArrayLhsClose: # ]=
      # e.g. if we have [$x$y]=$a$b
      key = word.Compound(parts[1:i])  # $x$y 
      value = word.Compound(parts[i+1:])  # $a$b from
      return key, value

  return None


def KeywordToken(w):
  # type: (word_t) -> Tuple[Kind_t, Optional[token]]
  """Tests if a word is an assignment or control flow word.

  Returns:
    kind, token
  """
  assert isinstance(w, word__Compound)

  err = (Kind.Undefined, None)
  if len(w.parts) != 1:
    return err

  part0 = w.parts[0]
  token_type = _LiteralId(part0)
  if token_type == Id.Undefined_Tok:
    return err

  assert isinstance(part0, word_part__Literal)  # for MyPy

  token_kind = LookupKind(token_type)
  if token_kind == Kind.ControlFlow:
    return token_kind, part0.token

  return err


def LiteralToken(w):
  # type: (word_t) -> Optional[token]
  """If a word consists of a literal token, return it.
  
  Otherwise return None.
  """
  assert isinstance(w, word__Compound)

  if len(w.parts) != 1:
    return None

  part0 = w.parts[0]
  if isinstance(part0, word_part__Literal):
    return part0.token

  return None


#
# Polymorphic between Token and Compound
#

def ArithId(node):
  # type: (word_t) -> Id_t
  if isinstance(node, word__Token):
    return node.token.id

  assert isinstance(node, word__Compound)
  return Id.Word_Compound


def BoolId(node):
  # type: (word_t) -> Id_t
  if isinstance(node, word__String):  # for test/[
    return node.id

  if isinstance(node, word__Token):
    return node.token.id

  # NOTE: I think Empty never happens in this context?
  assert isinstance(node, word__Compound)

  if len(node.parts) != 1:
    return Id.Word_Compound

  token_type = _LiteralId(node.parts[0])
  if token_type == Id.Undefined_Tok:
    return Id.Word_Compound  # It's a regular word

  # This is outside the BoolUnary/BoolBinary namespace, but works the same.
  if token_type in (Id.KW_Bang, Id.Lit_DRightBracket):
    return token_type  # special boolean "tokens"

  token_kind = LookupKind(token_type)
  if token_kind in (Kind.BoolUnary, Kind.BoolBinary):
    return token_type  # boolean operators

  return Id.Word_Compound


def CommandId(node):
  # type: (word_t) -> Id_t
  if isinstance(node, word__Token):
    return node.token.id

  # Assume it's a Compound
  assert isinstance(node, word__Compound)

  # Has to be a single literal part
  if len(node.parts) != 1:
    return Id.Word_Compound

  token_type = _LiteralId(node.parts[0])
  if token_type == Id.Undefined_Tok:
    return Id.Word_Compound

  elif token_type in (Id.Lit_LBrace, Id.Lit_RBrace, Id.ControlFlow_Return):
    # Return is for special processing
    return token_type

  token_kind = LookupKind(token_type)
  if token_kind == Kind.KW:
    return token_type

  return Id.Word_Compound


def CommandKind(w):
  # type: (word_t) -> Kind_t
  """The CommandKind is for coarse-grained decisions in the CommandParser."""
  if isinstance(w, word__Token):
    return LookupKind(w.token.id)

  # NOTE: This is a bit inconsistent with CommandId, because we never return
  # Kind.KW (or Kind.Lit).  But the CommandParser is easier to write this way.
  return Kind.Word


# Stubs for converting RHS of assignment to expression mode.
# For osh2oil.py
def IsVarSub(w):
  # type: (word_t) -> bool
  # Return whether it's any var sub, or a double quoted one
  return False


def SpanForLhsExpr(node):
  # type: (lhs_expr__LhsName) -> int
  if node.spids:
    return node.spids[0]
  else:
    return const.NO_INTEGER  
  # TODO: LhsIndexedName needs span_id.
  #if isinstance(node, lhs_expr__LhsName):
  #elif isinstance(node, lhs_expr__LhsIndexedName):


def SpanIdFromError(error):
  # type: (_ErrorWithLocation) -> int
  #print(parse_error)
  if error.span_id != const.NO_INTEGER:
    return error.span_id
  if error.token:
    return error.token.span_id
  if error.part:
    return LeftMostSpanForPart(error.part)
  if error.word:
    return LeftMostSpanForWord(error.word)

  return const.NO_INTEGER


def ErrorWord(fmt, err):
  # type: (str, _ErrorWithLocation) -> word__Compound
  error_str = fmt % err.UserErrorString()
  t = token(Id.Lit_Chars, error_str, const.NO_INTEGER)
  return word.Compound([word_part.Literal(t)])


def Pretty(w):
  # type: (word_t) -> str
  """Return a string to display to the user."""
  if isinstance(w, word__String):
    if w.id == Id.Eof_Real:
      return 'EOF'
    else:
      return repr(w.s)
  else:
    return str(w)
