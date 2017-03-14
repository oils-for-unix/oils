"""
word.py -- Functions for using words as "tokens".
"""

import sys

from osh import ast_ as ast
from core.id_kind import Id, Kind, LookupKind

word_e = ast.word_e
word_part_e = ast.word_part_e


def _LiteralPartId(p):
  """
  If the WordPart consists of a single literal token, return its Id.  Used for
  Id.KW_For, or Id.RBrace, etc.
  """
  if p.tag == word_part_e.LiteralPart:
    return p.token.id
  else:
    return Id.Undefined_Tok  # unequal to any other Id


def _EvalWordPart(part):
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
  if part.tag == word_part_e.ArrayLiteralPart:
    # Array literals aren't good for any of our use cases.  TODO: Rename
    # EvalWordToString?
    return False, '', False

  elif part.tag == word_part_e.LiteralPart:
    return True, part.token.val, False

  elif part.tag == word_part_e.EscapedLiteralPart:
    val = part.token.val
    assert len(val) == 2, val  # e.g. \*
    assert val[0] == '\\'
    s = val[1]
    return True, s, True

  elif part.tag == word_part_e.SingleQuotedPart:
    s = ''.join(t.val for t in part.tokens)
    return True, s, True

  elif part.tag == word_part_e.DoubleQuotedPart:
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
      word_part_e.ArithSubPart):
    return False, '', False

  else:
    raise AssertionError(part.tag)


def StaticEval(w):
  """Evaluate a CompoundWord at PARSE TIME.
  """
  ret = ''
  quoted = False
  for part in w.parts:
    ok, s, q = _EvalWordPart(part)
    if not ok:
      return False, '', quoted
    if q:
      quoted = True  # at least one part was quoted
    ret += s
  return True, ret, quoted


def _LeftMostSpanForPart(part):
  # TODO: Write unit tests in ui.py for error values

  #from core.id_kind import IdName
  #print(IdName(part.id))

  if part.tag == word_part_e.ArrayLiteralPart:
    return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif part.tag == word_part_e.LiteralPart:
    # Just use the token
    return part.token.span_id

  elif part.tag == word_part_e.EscapedLiteralPart:
    return part.token.span_id

  elif part.tag == word_part_e.SingleQuotedPart:
    if part.tokens:
      return part.tokens[0].span_id
    else:
      return -1

  elif part.tag == word_part_e.DoubleQuotedPart:
    if part.parts:
      return _LeftMostSpanForPart(part.parts[0])
    else:
      # We need the double quote location
      return -1

  elif part.tag == word_part_e.SimpleVarSub:
    return part.token.span_id

  elif part.tag == word_part_e.BracedVarSub:
    return part.spids[0]

  elif part.tag == word_part_e.CommandSubPart:
    return part.spids[0]

  elif part.tag == word_part_e.TildeSubPart:
    return -1

  elif part.tag == word_part_e.ArithSubPart:
    # begin, end
    return part.spids[0]

  else:
    raise AssertionError(part.tag)


def _RightMostSpanForPart(part):
  # TODO: Write unit tests in ui.py for error values

  #from core.id_kind import IdName
  #print(IdName(part.id))

  if part.tag == word_part_e.ArrayLiteralPart:
    # TODO: Return )
    return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif part.tag == word_part_e.LiteralPart:
    # Just use the token
    return part.token.span_id

  elif part.tag == word_part_e.EscapedLiteralPart:
    return part.token.span_id

  elif part.tag == word_part_e.SingleQuotedPart:
    if part.tokens:
      return part.tokens[-1].span_id
    else:
      return -1

  elif part.tag == word_part_e.DoubleQuotedPart:
    if part.parts:
      return _LeftMostSpanForPart(part.parts[-1])
    else:
      # We need the double quote location
      return -1

  elif part.tag == word_part_e.SimpleVarSub:
    return part.token.span_id

  elif part.tag == word_part_e.BracedVarSub:
    spid = part.spids[0]
    assert spid != -1
    return spid

  elif part.tag == word_part_e.CommandSubPart:
    return part.spids[1]

  elif part.tag == word_part_e.TildeSubPart:
    return -1

  elif part.tag == word_part_e.ArithSubPart:
    return -1

  else:
    raise AssertionError(part.tag)


def LeftMostSpanForWord(w):
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
  if w.tag == word_e.CompoundWord:
    if len(w.parts) == 0:
      return -1
    elif len(w.parts) == 1:
      return _LeftMostSpanForPart(w.parts[0])
    else:
      begin = w.parts[0]
      # TODO: We need to combine LineSpan()?  If they're both on the same line,
      # return them both.  If they're not, then just use "begin"?
      return _LeftMostSpanForPart(begin)

  # It's a TokenWord?
  return w.token.span_id


# This is needed for DoWord I guess?  IT makes it easier to write the fixer.
def UNUSED_RightMostSpanForWord(w):
  # TODO: Really we should use par
  if w.tag == word_e.CompoundWord:
    if len(w.parts) == 0:
      return -1
    elif len(w.parts) == 1:
      return _RightMostSpanForPart(w.parts[0])
    else:
      end = w.parts[-1]
      return _RightMostSpanForPart(end)

  # It's a TokenWord?
  return w.token.span_id


def TildeDetect(word):
  """Detect tilde expansion.

  If it needs to include a TildeSubPart, return a new word.  Otherwise return
  None.

  NOTE: This algorithm would be a simpler if
  1. We could assume some regex for user names.
  2. We didn't need to do brace expansion first, like {~foo,~bar}
  OR
  - If Lit_Slash were special (it is in the VAROP states, but not OUTER
  state).  We could introduce another lexer mode after you hit Lit_Tilde?

  So we have to scan all LiteralPart instances until they contain a '/'.

  http://unix.stackexchange.com/questions/157426/what-is-the-regex-to-validate-linux-users
  "It is usually recommended to only use usernames that begin with a lower
  case letter or an underscore, followed by lower case letters, digits,
  underscores, or dashes. They can end with a dollar sign. In regular
  expression terms: [a-z_][a-z0-9_-]*[$]?

  On Debian, the only constraints are that usernames must neither start with
  a dash ('-') nor contain a colon (':') or a whitespace (space: ' ', end
  of line: '\n', tabulation: '\t', etc.). Note that using a slash ('/') may
  break the default algorithm for the definition of the user's home
  directory.
  """
  if not word.parts:
    return None
  part0 = word.parts[0]
  if _LiteralPartId(part0) != Id.Lit_Tilde:
    return None

  prefix = ''
  found_slash = False
  # search for the next /
  for i in range(1, len(word.parts)):
    # Not a literal part, and we did NOT find a slash.  So there is no
    # TildeSub applied.  This would be something like ~X$var, ~$var,
    # ~$(echo), etc..  The slash is necessary.
    if word.parts[i].tag != word_part_e.LiteralPart:
      return None
    val = word.parts[i].token.val
    p = val.find('/')

    if p == -1:  # no slash yet
      prefix += val

    elif p >= 0:
      # e.g. for ~foo!bar/baz, extract "bar"
      # NOTE: requires downcast to LiteralPart
      pre, post = val[:p], val[p:]
      prefix += pre
      tilde_part = ast.TildeSubPart(prefix)
      # TODO: Need a span_id here.  Or use different algorithm.
      #print('SPLITTING %s p = %d' % (word.parts[i], p), file=sys.stderr)
      remainder_part = ast.LiteralPart(ast.token(Id.Lit_Chars, post))
      found_slash = True
      break

  w = ast.CompoundWord()
  if found_slash:
    w.parts.append(tilde_part)
    w.parts.append(remainder_part)
    j = i + 1
    while j < len(word.parts):
      w.parts.append(word.parts[j])
      j += 1
  else:
    # The whole thing is a tilde sub, e.g. ~foo or ~foo!bar
    w.parts.append(ast.TildeSubPart(prefix))
  return w


def TildeDetectAll(words):
  out = []
  for w in words:
    t = TildeDetect(w)
    if t:
      out.append(t)
    else:
      out.append(w)
  return out


def HasArrayPart(w):
  """Used in cmd_parse."""
  assert w.tag == word_e.CompoundWord

  for part in w.parts:
    if part.tag == word_part_e.ArrayLiteralPart:
      return True
  return False


def AsFuncName(w):
  assert w.tag == word_e.CompoundWord

  ok, s, quoted = StaticEval(w)
  if not ok:
    return False, ''
  if quoted:
    # TODO: Return False with error string
    if len(self.parts) != 1:
      raise RuntimeError(
          "Function names should not have quotes, got: %s", self.parts)
  return True, s


def AsArithVarName(w):
  """Returns a string if this word looks like an arith var; otherwise False.

  NOTE: This can't be combined with LooksLikeAssignment because VarLike and
  ArithVarLike must be different tokens.  Otherwise _ReadCompoundWord will be
  confused between array assigments foo=(1 2) and function calls foo(1, 2).
  """
  assert w.tag == word_e.CompoundWord

  if len(w.parts) != 1:
    return ""

  part0 = w.parts[0]
  if _LiteralPartId(part0) != Id.Lit_ArithVarLike:
    return False

  return part0.token.val


def LooksLikeAssignment(w):
  """Tests whether a word looke like FOO=bar.

  If so, return a (string, CompoundWord) pair.  Otherwise, return False.  
  """
  assert w.tag == word_e.CompoundWord
  if len(w.parts) == 0:
    return False

  part0 = w.parts[0]
  if _LiteralPartId(part0) != Id.Lit_VarLike:
    return False

  assert part0.token.val.endswith('=')
  name = part0.token.val[:-1]

  rhs = ast.CompoundWord()
  if len(w.parts) == 1:
    # NOTE: This is necesssary so that EmptyUnquoted elision isn't
    # applied.  EMPTY= is like EMPTY=''.
    rhs.parts.append(ast.SingleQuotedPart())
  else:
    for p in w.parts[1:]:
      rhs.parts.append(p)

  return name, rhs


def KeywordToken(w):
  """Tests if a word is an assignment or control flow word.

  Returns:
    kind, token
  """
  assert w.tag == word_e.CompoundWord

  err = (Kind.Undefined, None)
  if len(w.parts) != 1:
    return err

  token_type = _LiteralPartId(w.parts[0])
  if token_type == Id.Undefined_Tok:
    return err

  token_kind = LookupKind(token_type)
  if token_kind in (Kind.Assign, Kind.ControlFlow):
    return token_kind, w.parts[0].token

  return err


#
# Polymorphic between TokenWord and CompoundWord
#

def ArithId(node):
  if node.tag == word_e.TokenWord:
    return node.token.id

  assert node.tag == word_e.CompoundWord
  return Id.Word_Compound


def BoolId(node):
  if node.tag == word_e.TokenWord:
    return node.token.id

  # Assume it's a CompoundWord
  #assert node.tag == word_e.CompoundWord

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
  if node.tag == word_e.TokenWord:
    return node.token.id

  # Assume it's a CompoundWord
  assert node.tag == word_e.CompoundWord

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
  if w.tag == word_e.TokenWord:
    return LookupKind(w.token.id)

  # NOTE: This is a bit inconsistent with CommandId, because we never retur
  # Kind.KW (or Kind.Lit).  But the CommandParser is easier to write this way.
  return Kind.Word



# Stubs for converting RHS of assignment to expression mode.
def IsVarSub(w):
  # Return whether it's any var sub, or a double quoted one
  return False
