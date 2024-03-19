"""
word.py - Utility functions for words, e.g. treating them as "tokens".
"""

from _devbuild.gen.id_kind_asdl import Id, Kind, Id_t, Kind_t
from _devbuild.gen.syntax_asdl import (
    Token,
    CompoundWord,
    DoubleQuoted,
    SingleQuoted,
    word,
    word_e,
    word_t,
    word_str,
    word_part,
    word_part_t,
    word_part_e,
    AssocPair,
)
from frontend import consts
from frontend import lexer
from mycpp import mylib
from mycpp.mylib import tagswitch, log

from typing import Tuple, Optional, List, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from osh.word_parse import WordParser

_ = log


def LiteralId(p):
    # type: (word_part_t) -> Id_t
    """If the WordPart consists of a single literal token, return its Id.

    Used for Id.KW_For, or Id.RBrace, etc.
    """
    UP_part = p
    if p.tag() == word_part_e.Literal:
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

        elif case(word_part_e.BashAssocLiteral):
            return False, '', False

        elif case(word_part_e.Literal):
            tok = cast(Token, UP_part)
            # Weird performance issue: if we change this to lexer.LazyStr(),
            # the parser slows down, e.g. on configure-coreutils from 805 B
            # irefs to ~830 B.  The real issue is that we should avoid calling
            # this from CommandParser - for the Hay node.
            return True, lexer.TokenVal(tok), False
            #return True, lexer.LazyStr(tok), False

        elif case(word_part_e.EscapedLiteral):
            part = cast(word_part.EscapedLiteral, UP_part)
            if mylib.PYTHON:
                val = lexer.TokenVal(part.token)
                assert len(val) == 2, val  # e.g. \*
                assert val[0] == '\\'
            s = lexer.TokenSliceLeft(part.token, 1)
            return True, s, True

        elif case(word_part_e.SingleQuoted):
            part = cast(SingleQuoted, UP_part)
            return True, part.sval, True

        elif case(word_part_e.DoubleQuoted):
            part = cast(DoubleQuoted, UP_part)
            strs = []  # type: List[str]
            for p in part.parts:
                ok, s, _ = _EvalWordPart(p)
                if not ok:
                    return False, '', True
                strs.append(s)

            return True, ''.join(strs), True  # At least one part was quoted!

        elif case(word_part_e.CommandSub, word_part_e.SimpleVarSub,
                  word_part_e.BracedVarSub, word_part_e.TildeSub,
                  word_part_e.ArithSub, word_part_e.ExtGlob,
                  word_part_e.Splice, word_part_e.ExprSub):
            return False, '', False

        else:
            raise AssertionError(part.tag())


def FastStrEval(w):
    # type: (CompoundWord) -> Optional[str]
    """
    Detects common case 

    (1) CompoundWord([LiteralPart(Id.LitChars)])
        For echo -e, test x -lt 0, etc.
    (2) single quoted word like 'foo'

    Other patterns we could detect are:
    (1) "foo"
    (2) "$var" and "${var}" - I think these are very common in OSH code (but not YSH)
        - I think val_ops.Stringify() can handle all the errors
    """
    if len(w.parts) != 1:
        return None

    part0 = w.parts[0]
    UP_part0 = part0
    with tagswitch(part0) as case:
        if case(word_part_e.Literal):
            part0 = cast(Token, UP_part0)

            if part0.id in (Id.Lit_Chars, Id.Lit_LBracket, Id.Lit_RBracket):
                # Could add more tokens in this case
                #   e.g. + is Lit_Other, and it's a Token in 'expr'
                #   Right now it's Lit_Chars (e.g. ls -l) and [ and ] because I
                #   know those are common
                #   { } are not as common
                return lexer.LazyStr(part0)

            else:
                # e.g. Id.Lit_Star needs to be glob expanded
                # TODO: Consider moving Id.Lit_Star etc. to Kind.MaybeGlob?
                return None

        elif case(word_part_e.SingleQuoted):
            part0 = cast(SingleQuoted, UP_part0)
            # TODO: SingleQuoted should have lazy (str? sval) field
            # This would only affect multi-line strings though?
            return part0.sval

        else:
            # e.g. DoubleQuoted can't be optimized to a string, because it
            # might have "$@" and such
            return None


def StaticEval(UP_w):
    # type: (word_t) -> Tuple[bool, str, bool]
    """Evaluate a Compound at PARSE TIME."""
    quoted = False

    # e.g. for ( instead of for (( is a token word
    if UP_w.tag() != word_e.Compound:
        return False, '', quoted

    w = cast(CompoundWord, UP_w)

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
    # type: (word_t) -> Optional[CompoundWord]
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
    # BracedTree can't be tilde expanded
    if UP_w.tag() != word_e.Compound:
        return None

    w = cast(CompoundWord, UP_w)
    return TildeDetect2(w)


def TildeDetect2(w):
    # type: (CompoundWord) -> Optional[CompoundWord]
    """If tilde sub is detected, returns a new CompoundWord.

    Accepts CompoundWord, not word_t.  After brace expansion, we know we have a
    List[CompoundWord].

    Tilde detection:

    YES:
        ~       ~/   
        ~bob    ~bob/

    NO:
        ~bob#    ~bob#/
        ~bob$x
        ~$x

    Pattern to match (all must be word_part_e.Literal):

        Lit_Tilde Lit_Chars? (Lit_Slash | %end)
    """
    if len(w.parts) == 0:  # ${a-} has no parts
        return None

    part0 = w.parts[0]
    id0 = LiteralId(part0)
    if id0 != Id.Lit_Tilde:
        return None  # $x is not TildeSub

    tok0 = cast(Token, part0)

    new_parts = []  # type: List[word_part_t]

    if len(w.parts) == 1:  # ~
        new_parts.append(word_part.TildeSub(tok0, None, None))
        return CompoundWord(new_parts)

    id1 = LiteralId(w.parts[1])
    if id1 == Id.Lit_Slash:  # ~/
        new_parts.append(word_part.TildeSub(tok0, None, None))
        new_parts.extend(w.parts[1:])
        return CompoundWord(new_parts)

    if id1 != Id.Lit_Chars:
        return None  # ~$x is not TildeSub

    tok1 = cast(Token, w.parts[1])

    if len(w.parts) == 2:  # ~foo
        new_parts.append(word_part.TildeSub(tok0, tok1, lexer.TokenVal(tok1)))
        return CompoundWord(new_parts)

    id2 = LiteralId(w.parts[2])
    if id2 != Id.Lit_Slash:  # ~foo$x is not TildeSub
        return None

    new_parts.append(word_part.TildeSub(tok0, tok1, lexer.TokenVal(tok1)))
    new_parts.extend(w.parts[2:])
    return CompoundWord(new_parts)


def TildeDetectAssign(w):
    # type: (CompoundWord) -> None
    """Detects multiple tilde sub, like a=~:~/src:~bob

    MUTATES its argument.

    Pattern for to match (all must be word_part_e.Literal):

        Lit_Tilde Lit_Chars? (Lit_Slash | Lit_Colon | %end)
    """
    parts = w.parts

    # Bail out EARLY if there are no ~ at all
    has_tilde = False
    for part in parts:
        if LiteralId(part) == Id.Lit_Tilde:
            has_tilde = True
            break
    if not has_tilde:
        return  # Avoid further work and allocations

    # Avoid IndexError, since we have to look ahead up to 2 tokens
    parts.append(None)
    parts.append(None)

    new_parts = []  # type: List[word_part_t]

    tilde_could_be_next = True  # true at first, and true after :

    i = 0
    n = len(parts)

    while i < n:
        part0 = parts[i]
        if part0 is None:
            break

        #log('i = %d', i)
        #log('part0 %s', part0)

        # Skip tilde in middle of word, like a=foo~bar
        if tilde_could_be_next and LiteralId(part0) == Id.Lit_Tilde:
            # If ~ ends the string, we have
            part1 = parts[i + 1]
            part2 = parts[i + 2]

            tok0 = cast(Token, part0)

            if part1 is None:  # x=foo:~
                new_parts.append(word_part.TildeSub(tok0, None, None))
                break  # at end

            id1 = LiteralId(part1)

            if id1 in (Id.Lit_Slash, Id.Lit_Colon):  # x=foo:~/ or x=foo:~:
                new_parts.append(word_part.TildeSub(tok0, None, None))
                new_parts.append(part1)
                i += 2
                continue

            if id1 != Id.Lit_Chars:
                new_parts.append(part0)  # unchanged
                new_parts.append(part1)  # ...
                i += 2
                continue  # x=foo:~$x is not tilde sub

            tok1 = cast(Token, part1)

            if part2 is None:  # x=foo:~foo
                # consume both
                new_parts.append(
                    word_part.TildeSub(tok0, tok1, lexer.TokenVal(tok1)))
                break  # at end

            id2 = LiteralId(part2)
            if id2 not in (Id.Lit_Slash, Id.Lit_Colon):  # x=foo:~foo$x
                new_parts.append(part0)  # unchanged
                new_parts.append(part1)  # ...
                new_parts.append(part2)  # ...
                i += 3
                continue

            new_parts.append(
                word_part.TildeSub(tok0, tok1, lexer.TokenVal(tok1)))
            new_parts.append(part2)
            i += 3

            tilde_could_be_next = (id2 == Id.Lit_Colon)

        else:
            new_parts.append(part0)
            i += 1

            tilde_could_be_next = (LiteralId(part0) == Id.Lit_Colon)

    parts.pop()
    parts.pop()

    # Mutate argument
    w.parts = new_parts


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
    # type: (CompoundWord) -> bool
    """Used in cmd_parse."""
    for part in w.parts:
        if part.tag() == word_part_e.ShArrayLiteral:
            return True
    return False


def ShFunctionName(w):
    # type: (CompoundWord) -> str
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
    confused between array assignments foo=(1 2) and function calls foo(1, 2).
    """
    if UP_w.tag() != word_e.Compound:
        return None

    w = cast(CompoundWord, UP_w)
    if len(w.parts) != 1:
        return None

    UP_part0 = w.parts[0]
    if LiteralId(UP_part0) != Id.Lit_ArithVarLike:
        return None

    return cast(Token, UP_part0)


def IsVarLike(w):
    # type: (CompoundWord) -> bool
    """Tests whether a word looks like FOO=bar.

    This is a quick test for the command parser to distinguish:

    func() { echo hi; }
    func=(1 2 3)
    """
    if len(w.parts) == 0:
        return False

    return LiteralId(w.parts[0]) == Id.Lit_VarLike


def DetectShAssignment(w):
    # type: (CompoundWord) -> Tuple[Optional[Token], Optional[Token], int]
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
    id0 = LiteralId(UP_part0)
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
            if LiteralId(UP_part) == Id.Lit_ArrayLhsClose:
                tok_close = cast(Token, UP_part)
                return tok0, tok_close, i + 1

    # Nothing detected.  Could be 'foobar' or a[x+1+2/' without the closing ].
    return no_token, no_token, 0


def DetectAssocPair(w):
    # type: (CompoundWord) -> Optional[AssocPair]
    """Like DetectShAssignment, but for A=(['k']=v ['k2']=v)

    The key and the value are both strings.  So we just pick out
    word_part. Unlike a[k]=v, A=([k]=v) is NOT ambiguous, because the
    [k] syntax is only used for associative array literals, as opposed
    to indexed array literals.
    """
    parts = w.parts
    if LiteralId(parts[0]) != Id.Lit_LBracket:
        return None

    n = len(parts)
    for i in xrange(n):
        id_ = LiteralId(parts[i])
        if id_ == Id.Lit_ArrayLhsClose:  # ]=
            # e.g. if we have [$x$y]=$a$b
            key = CompoundWord(parts[1:i])  # $x$y
            value = CompoundWord(parts[i + 1:])  # $a$b from

            # Type-annotated intermediate value for mycpp translation
            return AssocPair(key, value)

    return None


def IsControlFlow(w):
    # type: (CompoundWord) -> Tuple[Kind_t, Optional[Token]]
    """Tests if a word is a control flow word."""
    no_token = None  # type: Optional[Token]

    if len(w.parts) != 1:
        return Kind.Undefined, no_token

    UP_part0 = w.parts[0]
    token_type = LiteralId(UP_part0)
    if token_type == Id.Undefined_Tok:
        return Kind.Undefined, no_token

    token_kind = consts.GetKind(token_type)
    if token_kind == Kind.ControlFlow:
        return token_kind, cast(Token, UP_part0)

    return Kind.Undefined, no_token


def LiteralToken(UP_w):
    # type: (word_t) -> Optional[Token]
    """If a word consists of a literal token, return it.

    Otherwise return None.
    """
    # We're casting here because this function is called by the CommandParser for
    # var, setvar, '...', etc.  It's easier to cast in one place.
    assert UP_w.tag() == word_e.Compound, UP_w
    w = cast(CompoundWord, UP_w)

    if len(w.parts) != 1:
        return None

    part0 = w.parts[0]
    if part0.tag() == word_part_e.Literal:
        return cast(Token, part0)

    return None


def BraceToken(UP_w):
    # type: (word_t) -> Optional[Token]
    """If a word has Id.Lit_LBrace or Lit_RBrace, return a Token.

    This is a special case for osh/cmd_parse.py

    The WordParser changes Id.Op_LBrace from ExprParser into Id.Lit_LBrace, so we
    may get a token, not a word.
    """
    with tagswitch(UP_w) as case:
        if case(word_e.Operator):
            tok = cast(Token, UP_w)
            assert tok.id in (Id.Lit_LBrace, Id.Lit_RBrace), tok
            return tok

        elif case(word_e.Compound):
            w = cast(CompoundWord, UP_w)
            return LiteralToken(w)

        else:
            raise AssertionError()


def AsKeywordToken(UP_w):
    # type: (word_t) -> Token
    """Given a word that IS A CompoundWord containing just a keyword, return
    the single token at the start."""
    assert UP_w.tag() == word_e.Compound, UP_w
    w = cast(CompoundWord, UP_w)

    part = w.parts[0]
    assert part.tag() == word_part_e.Literal, part
    tok = cast(Token, part)
    assert consts.GetKind(tok.id) == Kind.KW, tok
    return tok


def AsOperatorToken(word):
    # type: (word_t) -> Token
    """For a word that IS an operator (word.Token), return that token.

    This must only be called on a word which is known to be an operator
    (word.Token).
    """
    assert word.tag() == word_e.Operator, word
    return cast(Token, word)


#
# Polymorphic between Token and Compound
#


def ArithId(w):
    # type: (word_t) -> Id_t
    if w.tag() == word_e.Operator:
        tok = cast(Token, w)
        return tok.id

    assert isinstance(w, CompoundWord)
    return Id.Word_Compound


def BoolId(w):
    # type: (word_t) -> Id_t
    UP_w = w
    with tagswitch(w) as case:
        if case(word_e.String):  # for test/[
            w = cast(word.String, UP_w)
            return w.id

        elif case(word_e.Operator):
            tok = cast(Token, UP_w)
            return tok.id

        elif case(word_e.Compound):
            w = cast(CompoundWord, UP_w)

            if len(w.parts) != 1:
                return Id.Word_Compound

            token_type = LiteralId(w.parts[0])
            if token_type == Id.Undefined_Tok:
                return Id.Word_Compound  # It's a regular word

            # This is outside the BoolUnary/BoolBinary namespace, but works the same.
            if token_type in (Id.KW_Bang, Id.Lit_DRightBracket):
                return token_type  # special boolean "tokens"

            token_kind = consts.GetKind(token_type)
            if token_kind in (Kind.BoolUnary, Kind.BoolBinary):
                return token_type  # boolean operators

            return Id.Word_Compound

        else:
            # I think Empty never happens in this context?
            raise AssertionError(w.tag())


def CommandId(w):
    # type: (word_t) -> Id_t
    UP_w = w
    with tagswitch(w) as case:
        if case(word_e.Operator):
            tok = cast(Token, UP_w)
            return tok.id

        elif case(word_e.Compound):
            w = cast(CompoundWord, UP_w)

            # Has to be a single literal part
            if len(w.parts) != 1:
                return Id.Word_Compound

            token_type = LiteralId(w.parts[0])
            if token_type == Id.Undefined_Tok:
                return Id.Word_Compound

            elif token_type in (Id.Lit_LBrace, Id.Lit_RBrace, Id.Lit_Equals,
                                Id.ControlFlow_Return):
                # OSH and YSH recognize:  {  }
                # YSH recognizes:         =  return
                return token_type

            token_kind = consts.GetKind(token_type)
            if token_kind == Kind.KW:
                return token_type

            return Id.Word_Compound

        else:
            raise AssertionError(w.tag())


def CommandKind(w):
    # type: (word_t) -> Kind_t
    """The CommandKind is for coarse-grained decisions in the CommandParser."""
    if w.tag() == word_e.Operator:
        tok = cast(Token, w)
        return consts.GetKind(tok.id)

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


# Doesn't translate with mycpp because of dynamic %
def ErrorWord(error_str):
    # type: (str) -> CompoundWord
    t = lexer.DummyToken(Id.Lit_Chars, error_str)
    return CompoundWord([t])


def Pretty(w):
    # type: (word_t) -> str
    """Return a string to display to the user."""
    UP_w = w
    if w.tag() == word_e.String:
        w = cast(word.String, UP_w)
        if w.id == Id.Eof_Real:
            return 'EOF'
        else:
            return repr(w.s)
    else:
        return word_str(w.tag())  # tag name


class ctx_EmitDocToken(object):
    """For doc comments."""

    def __init__(self, w_parser):
        # type: (WordParser) -> None
        w_parser.EmitDocToken(True)
        self.w_parser = w_parser

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.w_parser.EmitDocToken(False)


class ctx_Multiline(object):
    """For multiline commands."""

    def __init__(self, w_parser):
        # type: (WordParser) -> None
        w_parser.Multiline(True)
        self.w_parser = w_parser

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.w_parser.Multiline(False)
