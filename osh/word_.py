"""
word.py - Utility functions for words, e.g. treating them as "tokens".
"""

from _devbuild.gen.id_kind_asdl import Id, Kind, Id_t, Kind_t
from _devbuild.gen.syntax_asdl import (
    Token, compound_word, 
    double_quoted, single_quoted, simple_var_sub, braced_var_sub, command_sub,
    sh_array_literal,
    word_part, word_part_t, word_part_e,
    word_part__AssocArrayLiteral,
    word_part__EscapedLiteral,
    word_part__TildeSub,
    word_part__ArithSub, word_part__ExtGlob,
    word_part__Splice, word_part__FuncCall, word_part__ExprSub,

    word_e, word_t, word__BracedTree, word__String,

    sh_lhs_expr__Name,
)
from asdl import runtime
from core.util import log
from frontend import lookup
from mycpp import mylib
from mycpp.mylib import tagswitch

from typing import Tuple, Optional, List, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from core.error import _ErrorWithLocation

_ = log


def _LiteralId(p):
  # type: (word_part_t) -> Id_t
  """
  If the WordPart consists of a single literal token, return its Id.  Used for
  Id.KW_For, or Id.RBrace, etc.
  """
  UP_part = p
  if p.tag_() == word_part_e.Literal:
    return cast(Token, UP_part).id
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
  UP_part = part
  with tagswitch(part) as case:
    if case(word_part_e.ShArrayLiteral):
      # Array literals aren't good for any of our use cases.  TODO: Rename
      # EvalWordToString?
      return False, '', False

    elif case(word_part_e.AssocArrayLiteral):
      return False, '', False

    elif case(word_part_e.Literal):
      tok = cast(Token, UP_part)
      return True, tok.val, False

    elif case(word_part_e.EscapedLiteral):
      part = cast(word_part__EscapedLiteral, UP_part)
      val = part.token.val
      assert len(val) == 2, val  # e.g. \*
      assert val[0] == '\\'
      s = val[1]
      return True, s, True

    elif case(word_part_e.SingleQuoted):
      part = cast(single_quoted, UP_part)
      tmp = [t.val for t in part.tokens]  # on its own line for mycpp
      s = ''.join(tmp)
      return True, s, True

    elif case(word_part_e.DoubleQuoted):
      part = cast(double_quoted, UP_part)
      strs = []  # type: List[str]
      for p in part.parts:
        ok, s, _ = _EvalWordPart(p)
        if not ok:
          return False, '', True
        strs.append(s)

      return True, ''.join(strs), True  # At least one part was quoted!

    elif case(
        word_part_e.CommandSub, word_part_e.SimpleVarSub,
        word_part_e.BracedVarSub, word_part_e.TildeSub, word_part_e.ArithSub,
        word_part_e.ExtGlob, word_part_e.Splice):
      return False, '', False

    else:
      raise AssertionError(part.tag_())


def StaticEval(UP_w):
  # type: (word_t) -> Tuple[bool, str, bool]
  """Evaluate a Compound at PARSE TIME."""
  quoted = False

  # e.g. for ( instead of for (( is a token word
  if UP_w.tag_() != word_e.Compound:
    return False, '', quoted

  w = cast(compound_word, UP_w)

  strs = []  # type: List[str]
  for part in w.parts:
    ok, s, q = _EvalWordPart(part)
    if not ok:
      return False, '', quoted
    if q:
      quoted = True  # at least one part was quoted
    strs.append(s)
  #log('StaticEval parts %s', w.parts)
  return True, ''.join(strs), quoted


def LeftMostSpanForPart(part):
  # type: (word_part_t) -> int
  UP_part = part
  with tagswitch(part) as case:
    if case(word_part_e.ShArrayLiteral):
      part = cast(sh_array_literal, UP_part)
      return part.left.span_id  # ( location

    elif case(word_part_e.AssocArrayLiteral):
      part = cast(word_part__AssocArrayLiteral, UP_part)
      return part.left.span_id  # ( location

    elif case(word_part_e.Literal):
      tok = cast(Token, UP_part)
      return tok.span_id

    elif case(word_part_e.EscapedLiteral):
      part = cast(word_part__EscapedLiteral, UP_part)
      return part.token.span_id

    elif case(word_part_e.SingleQuoted):
      part = cast(single_quoted, UP_part)
      return part.left.span_id  # single quote location

    elif case(word_part_e.DoubleQuoted):
      part = cast(double_quoted, UP_part)
      return part.left.span_id  # double quote location

    elif case(word_part_e.SimpleVarSub):
      part = cast(simple_var_sub, UP_part)
      return part.token.span_id

    elif case(word_part_e.BracedVarSub):
      part = cast(braced_var_sub, UP_part)
      return part.spids[0]

    elif case(word_part_e.CommandSub):
      part = cast(command_sub, UP_part)
      return part.spids[0]

    elif case(word_part_e.TildeSub):
      part = cast(word_part__TildeSub, UP_part)
      return part.token.span_id

    elif case(word_part_e.ArithSub):
      part = cast(word_part__ArithSub, UP_part)
      # begin, end
      return part.spids[0]

    elif case(word_part_e.ExtGlob):
      part = cast(word_part__ExtGlob, UP_part)
      # This is the smae as part.op.span_id, but we want to be consistent with
      # left/right.  Not sure I want to add a right token just for the spid.
      return part.spids[0]
      #return part.op.span_id  # e.g. @( is the left-most token

    elif case(word_part_e.BracedTuple):
      return runtime.NO_SPID

    elif case(word_part_e.Splice):
      part = cast(word_part__Splice, UP_part)
      return part.name.span_id

    elif case(word_part_e.FuncCall):
      part = cast(word_part__FuncCall, UP_part)
      return part.name.span_id  # @f(x) or $f(x)

    elif case(word_part_e.ExprSub):
      part = cast(word_part__ExprSub, UP_part)
      return part.left.span_id  # $[

    else:
      raise AssertionError(part.tag_())


def _RightMostSpanForPart(part):
  # type: (word_part_t) -> int
  UP_part = part
  with tagswitch(part) as case:
    if case(word_part_e.ShArrayLiteral):
      part = cast(sh_array_literal, UP_part)
      # TODO: Return )
      return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

    elif case(word_part_e.Literal):
      # Just use the token
      tok = cast(Token, UP_part)
      return tok.span_id

    elif case(word_part_e.EscapedLiteral):
      part = cast(word_part__EscapedLiteral, UP_part)
      return part.token.span_id

    elif case(word_part_e.SingleQuoted):
      part = cast(single_quoted, UP_part)
      return part.spids[1]  # right '

    elif case(word_part_e.DoubleQuoted):
      part = cast(double_quoted, UP_part)
      return part.spids[1]  # right "

    elif case(word_part_e.SimpleVarSub):
      part = cast(simple_var_sub, UP_part)
      return part.token.span_id

    elif case(word_part_e.BracedVarSub):
      part = cast(braced_var_sub, UP_part)
      spid = part.spids[1]  # right }
      assert spid != runtime.NO_SPID
      return spid

    elif case(word_part_e.CommandSub):
      part = cast(command_sub, UP_part)
      return part.spids[1]

    elif case(word_part_e.TildeSub):
      return runtime.NO_SPID

    elif case(word_part_e.ArithSub):
      part = cast(word_part__ArithSub, UP_part)
      return part.spids[1]

    elif case(word_part_e.ExtGlob):
      part = cast(word_part__ExtGlob, UP_part)
      return part.spids[1]

    # TODO: Do Splice and FuncCall need it?
    else:
      raise AssertionError(part.tag_())


def LeftMostSpanForWord(w):
  # type: (word_t) -> int
  UP_w = w
  with tagswitch(w) as case:
    if case(word_e.Compound):
      w = cast(compound_word, UP_w)
      if len(w.parts):
        return LeftMostSpanForPart(w.parts[0])
      else:
        # This is possible for empty brace sub alternative {a,b,}
        return runtime.NO_SPID

    elif case(word_e.Token):
      tok = cast(Token, UP_w)
      return tok.span_id

    elif case(word_e.Empty):
      return runtime.NO_SPID

    elif case(word_e.BracedTree):
      w = cast(word__BracedTree, UP_w)
      # This should always have one part?
      return LeftMostSpanForPart(w.parts[0])

    elif case(word_e.String):
      w = cast(word__String, UP_w)
      return w.span_id  # See _StringWordEmitter in osh/builtin_bracket.py

    else:
      raise AssertionError(w.tag_())


def RightMostSpanForWord(w):
  # type: (word_t) -> int
  """Needed for here doc delimiters."""
  UP_w = w
  with tagswitch(w) as case:
    if case(word_e.Compound):
      w = cast(compound_word, UP_w)
      if len(w.parts) == 0:
        # TODO: Use Empty instead
        raise AssertionError("Compound shouldn't be empty")
      else:
        end = w.parts[-1]
        return _RightMostSpanForPart(end)

    elif case(word_e.Empty):
      return runtime.NO_SPID

    elif case(word_e.Token):
      tok = cast(Token, UP_w)
      return tok.span_id

    else:
      raise AssertionError(w.tag_())


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

def TildeDetect(UP_w):
  # type: (word_t) -> Optional[compound_word]
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
  if UP_w.tag_() != word_e.Compound:
    return None

  w = cast(compound_word, UP_w)
  assert w.parts, w

  UP_part0 = w.parts[0]
  if _LiteralId(UP_part0) != Id.Lit_TildeLike:
    return None
  tok0 = cast(Token, UP_part0)

  if len(w.parts) == 1:  # can't be zero
    tilde_part = word_part.TildeSub(tok0)
    return compound_word([tilde_part])

  UP_part1 = w.parts[1]
  # NOTE: We could inspect the raw tokens.
  if _LiteralId(UP_part1) == Id.Lit_Chars:
    tok = cast(Token, UP_part1)
    if tok.val.startswith('/'):
      tilde_part_ = word_part.TildeSub(tok0)  # type: word_part_t

      parts = [tilde_part_]
      parts.extend(w.parts[1:])
      return compound_word(parts)

  # It could be something like '~foo:bar', which doesn't have a slash.
  return None


def TildeDetectAll(words):
  # type: (List[word_t]) -> List[word_t]
  out = []  # type: List[word_t]
  for w in words:
    t = TildeDetect(w)
    if t:
      out.append(t)
    else:
      out.append(w)
  return out


def HasArrayPart(w):
  # type: (compound_word) -> bool
  """Used in cmd_parse."""
  for part in w.parts:
    if part.tag_() == word_part_e.ShArrayLiteral:
      return True
  return False


def ShFunctionName(w):
  # type: (compound_word) -> str
  """Returns a valid shell function name, or the empty string.

  TODO: Maybe use this regex to validate:

  FUNCTION_NAME_RE = r'[^{}\[\]=]*'
  
  Bash is very lenient, but that would disallow confusing characters, for
  better error messages on a[x]=(), etc.
  """
  ok, s, quoted = StaticEval(w)
  # Function names should not have quotes
  if not ok or quoted:
    return ''
  return s


def LooksLikeArithVar(UP_w):
  # type: (word_t) -> Optional[Token]
  """Return a token if this word looks like an arith var.

  NOTE: This can't be combined with DetectShAssignment because VarLike and
  ArithVarLike must be different tokens.  Otherwise _ReadCompoundWord will be
  confused between array assigments foo=(1 2) and function calls foo(1, 2).
  """
  if UP_w.tag_() != word_e.Compound:
    return None

  w = cast(compound_word, UP_w)
  if len(w.parts) != 1:
    return None

  UP_part0 = w.parts[0]
  if _LiteralId(UP_part0) != Id.Lit_ArithVarLike:
    return None

  return cast(Token, UP_part0)


def IsVarLike(w):
  # type: (compound_word) -> bool
  """Tests whether a word looks like FOO=bar.

  This is a quick test for the command parser to distinguish:
  
  func() { echo hi; }
  func=(1 2 3)
  """
  if len(w.parts) == 0:
    return False

  return _LiteralId(w.parts[0]) == Id.Lit_VarLike


def DetectShAssignment(w):
  # type: (compound_word) -> Tuple[Optional[Token], Optional[Token], int]
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
  no_token = None  # type: Optional[Token]

  n = len(w.parts)
  if n == 0:
    return no_token, no_token, 0

  UP_part0 = w.parts[0]
  id0 = _LiteralId(UP_part0)
  if id0 == Id.Lit_VarLike:
    tok = cast(Token, UP_part0)
    return tok, no_token, 1  # everything after first token is the value

  if id0 == Id.Lit_ArrayLhsOpen:
    tok0 = cast(Token, UP_part0)
    # NOTE that a[]=x should be an error.  We don't want to silently decay.
    if n < 2:
      return no_token, no_token, 0
    for i in xrange(1, n):
      UP_part = w.parts[i]
      if _LiteralId(UP_part) == Id.Lit_ArrayLhsClose:
        tok_close = cast(Token, UP_part)
        return tok0, tok_close, i+1

  # Nothing detected.  Could be 'foobar' or a[x+1+2/' without the closing ].
  return no_token, no_token, 0


def DetectAssocPair(w):
  # type: (compound_word) -> Optional[Tuple[compound_word, compound_word]]
  """
  Like DetectShAssignment, but for A=(['k']=v ['k2']=v)

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
      key = compound_word(parts[1:i])  # $x$y 
      value = compound_word(parts[i+1:])  # $a$b from

      # Type-annotated intermediate value for mycpp translation
      ret = key, value  # type: Optional[Tuple[compound_word, compound_word]]
      return ret

  return None


def KeywordToken(w):
  # type: (compound_word) -> Tuple[Kind_t, Optional[Token]]
  """Tests if a word is an assignment or control flow word."""
  no_token = None  # type: Optional[Token]

  if len(w.parts) != 1:
    return Kind.Undefined, no_token

  UP_part0 = w.parts[0]
  token_type = _LiteralId(UP_part0)
  if token_type == Id.Undefined_Tok:
    return Kind.Undefined, no_token

  token_kind = lookup.LookupKind(token_type)
  if token_kind == Kind.ControlFlow:
    return token_kind, cast(Token, UP_part0)

  return Kind.Undefined, no_token


def LiteralToken(UP_w):
  # type: (word_t) -> Optional[Token]
  """If a word consists of a literal token, return it.
  
  Otherwise return None.
  """
  assert UP_w.tag_() == word_e.Compound
  w = cast(compound_word, UP_w)

  if len(w.parts) != 1:
    return None

  part0 = w.parts[0]
  if part0.tag_() == word_part_e.Literal:
    return cast(Token, part0)

  return None


#
# Polymorphic between Token and Compound
#

def ArithId(w):
  # type: (word_t) -> Id_t
  if w.tag_() == word_e.Token:
    tok = cast(Token, w)
    return tok.id

  assert isinstance(w, compound_word)
  return Id.Word_Compound


def BoolId(w):
  # type: (word_t) -> Id_t
  UP_w = w
  with tagswitch(w) as case:
    if case(word_e.String):  # for test/[
      w = cast(word__String, UP_w)
      return w.id

    elif case(word_e.Token):
      tok = cast(Token, UP_w)
      return tok.id

    elif case(word_e.Compound):
      w = cast(compound_word, UP_w)

      if len(w.parts) != 1:
        return Id.Word_Compound

      token_type = _LiteralId(w.parts[0])
      if token_type == Id.Undefined_Tok:
        return Id.Word_Compound  # It's a regular word

      # This is outside the BoolUnary/BoolBinary namespace, but works the same.
      if token_type in (Id.KW_Bang, Id.Lit_DRightBracket):
        return token_type  # special boolean "tokens"

      token_kind = lookup.LookupKind(token_type)
      if token_kind in (Kind.BoolUnary, Kind.BoolBinary):
        return token_type  # boolean operators

      return Id.Word_Compound

    else:
      # I think Empty never happens in this context?
      raise AssertionError(w.tag_())


def CommandId(w):
  # type: (word_t) -> Id_t
  UP_w = w
  with tagswitch(w) as case:
    if case(word_e.Token):
      tok = cast(Token, UP_w)
      return tok.id

    elif case(word_e.Compound):
      w = cast(compound_word, UP_w)

      # Has to be a single literal part
      if len(w.parts) != 1:
        return Id.Word_Compound

      token_type = _LiteralId(w.parts[0])
      if token_type == Id.Undefined_Tok:
        return Id.Word_Compound

      elif token_type in (
          Id.Lit_LBrace, Id.Lit_RBrace, Id.Lit_Equals, Id.ControlFlow_Return):
        # OSH and Oil recognize:  { }
        # Oil recognizes:         = return
        return token_type

      token_kind = lookup.LookupKind(token_type)
      if token_kind == Kind.KW:
        return token_type

      return Id.Word_Compound

    else:
      raise AssertionError(w.tag_())


def CommandKind(w):
  # type: (word_t) -> Kind_t
  """The CommandKind is for coarse-grained decisions in the CommandParser."""
  if w.tag_() == word_e.Token:
    tok = cast(Token, w)
    return lookup.LookupKind(tok.id)

  # NOTE: This is a bit inconsistent with CommandId, because we never
  # return Kind.KW (or Kind.Lit).  But the CommandParser is easier to write
  # this way.
  return Kind.Word


# Stubs for converting RHS of assignment to expression mode.
# For osh2oil.py
def IsVarSub(w):
  # type: (word_t) -> bool
  """Return whether it's any var sub, or a double quoted one."""
  return False


def SpanForLhsExpr(node):
  # type: (sh_lhs_expr__Name) -> int
  if len(node.spids):
    return node.spids[0]
  else:
    return runtime.NO_SPID  
  # TODO: IndexedName needs span_id.
  #if isinstance(node, sh_lhs_expr__Name):
  #elif isinstance(node, sh_lhs_expr__IndexedName):


def SpanIdFromError(error):
  # type: (_ErrorWithLocation) -> int
  if error.span_id != runtime.NO_SPID:
    return error.span_id
  if error.token:
    return error.token.span_id
  if error.part:
    return LeftMostSpanForPart(error.part)
  if error.word:
    return LeftMostSpanForWord(error.word)

  return runtime.NO_SPID


if mylib.PYTHON:
  # Doesn't translate with mycpp because of dynamic %
  def ErrorWord(fmt, err):
    # type: (str, _ErrorWithLocation) -> compound_word
    error_str = fmt % err.UserErrorString()
    t = Token(Id.Lit_Chars, runtime.NO_SPID, error_str)
    return compound_word([t])


def Pretty(w):
  # type: (word_t) -> str
  """Return a string to display to the user."""
  UP_w = w
  if w.tag_() == word_e.String:
    w = cast(word__String, UP_w)
    if w.id == Id.Eof_Real:
      return 'EOF'
    else:
      return repr(w.s)
  else:
    # internal representation
    return str(w)
