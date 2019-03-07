"""
word.py - Utility functions for words, e.g. treating them as "tokens".
"""

from _devbuild.gen.id_kind_asdl import (Id, Kind, Id_t, Kind_t)
from _devbuild.gen.syntax_asdl import (
    token,
    word_part, word_part_t, word_part_e,
    word_part__ArrayLiteralPart, word_part__LiteralPart,
    word_part__EscapedLiteralPart, word_part__SingleQuotedPart,
    word_part__DoubleQuotedPart, word_part__SimpleVarSub,
    word_part__BracedVarSub, word_part__TildeSubPart,
    word_part__CommandSubPart, word_part__ArithSubPart,
    word_part__BracedAltPart, word_part__ExtGlobPart,

    word, word_t, 
    word__CompoundWord, word__TokenWord, word__EmptyWord, word__BracedWordTree,
    word__StringWord,

    lhs_expr__LhsName,
)
from asdl import const
from core import util
from core.meta import LookupKind

from typing import Tuple, Optional, List

p_die = util.p_die


def _LiteralPartId(p):
  # type: (word_part_t) -> Id_t
  """
  If the WordPart consists of a single literal token, return its Id.  Used for
  Id.KW_For, or Id.RBrace, etc.
  """
  if isinstance(p, word_part__LiteralPart):
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
  if isinstance(part, word_part__ArrayLiteralPart):
    # Array literals aren't good for any of our use cases.  TODO: Rename
    # EvalWordToString?
    return False, '', False

  elif isinstance(part, word_part__LiteralPart):
    return True, part.token.val, False

  elif isinstance(part, word_part__EscapedLiteralPart):
    val = part.token.val
    assert len(val) == 2, val  # e.g. \*
    assert val[0] == '\\'
    s = val[1]
    return True, s, True

  elif isinstance(part, word_part__SingleQuotedPart):
    s = ''.join(t.val for t in part.tokens)
    return True, s, True

  elif isinstance(part, word_part__DoubleQuotedPart):
    ret = ''
    for p in part.parts:
      ok, s, _ = _EvalWordPart(p)
      if not ok:
        return False, '', True
      ret += s

    return True, ret, True  # At least one part was quoted!

  elif part.tag in (
      word_part_e.CommandSubPart, word_part_e.SimpleVarSub,
      word_part_e.BracedVarSub, word_part_e.TildeSubPart,
      word_part_e.ArithSubPart, word_part_e.ExtGlobPart):
    return False, '', False

  else:
    raise AssertionError(part.__class__.__name__)


def StaticEval(w):
  # type: (word_t) -> Tuple[bool, str, bool]
  """Evaluate a CompoundWord at PARSE TIME.
  """
  ret = ''
  quoted = False

  # e.g. for ( instead of for (( is a token word
  if not isinstance(w, word__CompoundWord):
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

  if isinstance(part, word_part__ArrayLiteralPart):
    if not part.words:
      return const.NO_INTEGER
    else:
      return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif isinstance(part, word_part__LiteralPart):
    # Just use the token
    return part.token.span_id

  elif isinstance(part, word_part__EscapedLiteralPart):
    return part.token.span_id

  elif isinstance(part, word_part__SingleQuotedPart):
    return part.spids[0]  # single quote location

  elif isinstance(part, word_part__DoubleQuotedPart):
    return part.spids[0]  # double quote location

  elif isinstance(part, word_part__SimpleVarSub):
    return part.token.span_id

  elif isinstance(part, word_part__BracedVarSub):
    return part.spids[0]

  elif isinstance(part, word_part__CommandSubPart):
    return part.spids[0]

  elif isinstance(part, word_part__TildeSubPart):
    return const.NO_INTEGER

  elif isinstance(part, word_part__ArithSubPart):
    # begin, end
    return part.spids[0]

  elif isinstance(part, word_part__ExtGlobPart):
    # This is the smae as part.op.span_id, but we want to be consistent with
    # left/right.  Not sure I want to add a right token just for the spid.
    return part.spids[0]
    #return part.op.span_id  # e.g. @( is the left-most token

  elif isinstance(part, word_part__BracedAltPart):
    return const.NO_INTEGER

  else:
    raise AssertionError(part.__class__.__name__)


def _RightMostSpanForPart(part):
  # type: (word_part_t) -> int
  # TODO: Write unit tests in ui.py for error values

  if isinstance(part, word_part__ArrayLiteralPart):
    # TODO: Return )
    return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif isinstance(part, word_part__LiteralPart):
    # Just use the token
    return part.token.span_id

  elif isinstance(part, word_part__EscapedLiteralPart):
    return part.token.span_id

  elif isinstance(part, word_part__SingleQuotedPart):
    return part.spids[1]  # right '

  elif isinstance(part, word_part__DoubleQuotedPart):
    return part.spids[1]  # right "

  elif isinstance(part, word_part__SimpleVarSub):
    return part.token.span_id

  elif isinstance(part, word_part__BracedVarSub):
    spid = part.spids[1]  # right }
    assert spid != const.NO_INTEGER
    return spid

  elif isinstance(part, word_part__CommandSubPart):
    return part.spids[1]

  elif isinstance(part, word_part__TildeSubPart):
    return const.NO_INTEGER

  elif isinstance(part, word_part__ArithSubPart):
    return const.NO_INTEGER

  elif isinstance(part, word_part__ExtGlobPart):
    return part.spids[1]

  else:
    raise AssertionError(part.tag)


def LeftMostSpanForWord(w):
  # type: (word_t) -> int
  # For now it returns a LineSpan.  That's all you know how to print.
  #
  # Runtime errors may be different.
  #
  # TokenWord: just use token.line_span
  # LiteralPart: token.line_span
  # composites: just use the first part for now, but show the stack trace:
  #   $(( 1 +  + ))
  #   ^~~
  #   In arithmetic substitution
  #   $(( 1 +  + ))
  #            ^
  #            Invalid argument to + operator

  # TODO: Really we should use par
  if isinstance(w, word__CompoundWord):
    if len(w.parts) == 0:
      return const.NO_INTEGER
    else:
      begin = w.parts[0]
      # TODO: We need to combine LineSpan()?  If they're both on the same line,
      # return them both.  If they're not, then just use "begin"?
      return LeftMostSpanForPart(begin)

  elif isinstance(w, word__TokenWord):
    return w.token.span_id

  elif isinstance(w, word__EmptyWord):
    return const.NO_INTEGER

  elif isinstance(w, word__BracedWordTree):
    if len(w.parts) == 0:
      return const.NO_INTEGER
    else:
      begin = w.parts[0]
      # TODO: We need to combine LineSpan()?  If they're both on the same line,
      # return them both.  If they're not, then just use "begin"?
      return LeftMostSpanForPart(begin)

  elif isinstance(w, word__StringWord):
    # There is no place to store this now?
    return const.NO_INTEGER

  else:
    raise AssertionError(w)


def RightMostSpanForWord(w):
  # type: (word_t) -> int
  """Needed for here doc delimiters."""
  if isinstance(w, word__CompoundWord):
    if len(w.parts) == 0:
      # TODO: Use EmptyWord instead
      raise AssertionError("CompoundWord shouldn't be empty")
    else:
      end = w.parts[-1]
      return _RightMostSpanForPart(end)

  elif isinstance(w, word__EmptyWord):
    return const.NO_INTEGER

  assert isinstance(w, word__TokenWord)
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

  It might begin with  LiteralPart that needs to be turned into a TildeSubPart.
  (It depends on whether the second token begins with slash).

  If so, it return a new word.  Otherwise return None.

  NOTE:
  - The regex for Lit_TildeLike could be expanded.  Right now it's
    conservative, like Lit_Chars without the /.
  - It's possible to write this in a mutating style, since only the first token
    is changed.  But note that we CANNOT know this during lexing.
  """
  # NOTE: BracedWordTree, EmptyWord, etc. can't be tilde expanded
  if not isinstance(w, word__CompoundWord):
    return None

  assert w.parts, w

  part0 = w.parts[0]
  if _LiteralPartId(part0) != Id.Lit_TildeLike:
    return None
  assert isinstance(part0, word_part__LiteralPart)  # for MyPy

  if len(w.parts) == 1:  # can't be zero
    tilde_part = word_part.TildeSubPart(part0.token)
    return word.CompoundWord([tilde_part])

  part1 = w.parts[1]
  # NOTE: We could inspect the raw tokens.
  if _LiteralPartId(part1) == Id.Lit_Chars:
    assert isinstance(part1, word_part__LiteralPart)  # for MyPy
    if part1.token.val.startswith('/'):
      tilde_part_ = word_part.TildeSubPart(part0.token)  # type: word_part_t
      return word.CompoundWord([tilde_part_] + w.parts[1:])

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
  assert isinstance(w, word__CompoundWord)

  for part in w.parts:
    if isinstance(part, word_part__ArrayLiteralPart):
      return True
  return False


def AsFuncName(w):
  # type: (word__CompoundWord) -> Tuple[bool, str]
  assert isinstance(w, word__CompoundWord)

  ok, s, quoted = StaticEval(w)
  if not ok:
    return False, ''
  if quoted:
    # Function names should not have quotes
    if len(w.parts) != 1:
      return False, ''
  return True, s


def LooksLikeArithVar(w):
  # type: (word_t) -> Optional[token]
  """Return a token if this word looks like an arith var.

  NOTE: This can't be combined with DetectAssignment because VarLike and
  ArithVarLike must be different tokens.  Otherwise _ReadCompoundWord will be
  confused between array assigments foo=(1 2) and function calls foo(1, 2).
  """
  if not isinstance(w, word__CompoundWord):
    return None

  if len(w.parts) != 1:
    return None

  part0 = w.parts[0]
  if _LiteralPartId(part0) != Id.Lit_ArithVarLike:
    return None
  assert isinstance(part0, word_part__LiteralPart)  # for MyPy

  return part0.token


def IsVarLike(w):
  # type: (word__CompoundWord) -> bool
  """Tests whether a word looks like FOO=bar.

  This is a quick test for the command parser to distinguish:
  
  func() { echo hi; }
  func=(1 2 3)
  """
  assert isinstance(w, word__CompoundWord)
  if len(w.parts) == 0:
    return False

  part0 = w.parts[0]
  return _LiteralPartId(w.parts[0]) == Id.Lit_VarLike


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
  assert isinstance(w, word__CompoundWord)
  n = len(w.parts)
  if n == 0:
    return None, None, 0

  part0 = w.parts[0]
  id0 = _LiteralPartId(part0)
  if id0 == Id.Lit_VarLike:
    assert isinstance(part0, word_part__LiteralPart)  # for MyPy
    return part0.token, None, 1  # everything after first token is the value

  if id0 == Id.Lit_ArrayLhsOpen:
    assert isinstance(part0, word_part__LiteralPart)  # for MyPy

    # NOTE that a[]=x should be an error.  We don't want to silently decay.
    if n < 2:
      return None, None, 0
    for i in xrange(1, n):
      part = w.parts[i]
      if _LiteralPartId(part) == Id.Lit_ArrayLhsClose:
        assert isinstance(part, word_part__LiteralPart)  # for MyPy
        return part0.token, part.token, i+1

  # Nothing detected.  Could be 'foobar' or a[x+1+2/' without the closing ].
  return None, None, 0


def KeywordToken(w):
  # type: (word_t) -> Tuple[Kind_t, Optional[token]]
  """Tests if a word is an assignment or control flow word.

  Returns:
    kind, token
  """
  assert isinstance(w, word__CompoundWord)

  err = (Kind.Undefined, None)
  if len(w.parts) != 1:
    return err

  part0 = w.parts[0]
  token_type = _LiteralPartId(part0)
  if token_type == Id.Undefined_Tok:
    return err

  assert isinstance(part0, word_part__LiteralPart)  # for MyPy

  token_kind = LookupKind(token_type)
  if token_kind in (Kind.Assign, Kind.ControlFlow):
    return token_kind, part0.token

  return err


#
# Polymorphic between TokenWord and CompoundWord
#

def ArithId(node):
  # type: (word_t) -> Id_t
  if isinstance(node, word__TokenWord):
    return node.token.id

  assert isinstance(node, word__CompoundWord)
  return Id.Word_Compound


def BoolId(node):
  # type: (word_t) -> Id_t
  if isinstance(node, word__StringWord):  # for test/[
    return node.id

  if isinstance(node, word__TokenWord):
    return node.token.id

  # NOTE: I think EmptyWord never happens in this context?
  assert isinstance(node, word__CompoundWord)

  if len(node.parts) != 1:
    return Id.Word_Compound

  token_type = _LiteralPartId(node.parts[0])
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
  if isinstance(node, word__TokenWord):
    return node.token.id

  # Assume it's a CompoundWord
  assert isinstance(node, word__CompoundWord)

  # Has to be a single literal part
  if len(node.parts) != 1:
    return Id.Word_Compound

  token_type = _LiteralPartId(node.parts[0])
  if token_type == Id.Undefined_Tok:
    return Id.Word_Compound

  elif token_type in (Id.Lit_LBrace, Id.Lit_RBrace):
    return token_type

  token_kind = LookupKind(token_type)
  if token_kind == Kind.KW:
    return token_type

  return Id.Word_Compound


def CommandKind(w):
  # type: (word_t) -> Kind_t
  """The CommandKind is for coarse-grained decisions in the CommandParser."""
  if isinstance(w, word__TokenWord):
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
