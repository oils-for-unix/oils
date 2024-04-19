"""
lexer_def.py -- A lexer for both OSH and YSH.

It consists of a series of lexer modes, each with a regex -> Id mapping.

After changing this file, run:

    build/py.sh all

or at least:

    build/py.sh fastlex

Input Handling
--------------

Every line is NUL terminated:

    'one\n\0' 'last line\0'

which means that no regexes below should match \0.  The core/lexer_gen.py code
generator adds and extra rule for \0.

For example, use [^'\0]+ instead of [^']+ .

If this rule isn't followed, we would read uninitialized memory past the
sentinel.  Python's regex engine knows where the end of the input string is, so
it doesn't require need a sentinel like \0.
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t, Kind
from _devbuild.gen.types_asdl import lex_mode_e

from frontend import id_kind_def

from typing import Tuple

# Initialize spec that the lexer depends on.
ID_SPEC = id_kind_def.IdSpec({}, {})

id_kind_def.AddKinds(ID_SPEC)
id_kind_def.AddBoolKinds(ID_SPEC)  # must come second
id_kind_def.SetupTestBuiltin(ID_SPEC, {}, {}, {})


def C(pat, tok_type):
    # type: (str, Id_t) -> Tuple[bool, str, Id_t]
    """Lexer rule with a constant string, e.g. C('$*', VSub_Star)"""
    return (False, pat, tok_type)


def R(pat, tok_type):
    # type: (str, Id_t) -> Tuple[bool, str, Id_t]
    """Lexer rule with a regex string, e.g. R('\$[0-9]', VSub_Number)"""
    return (True, pat, tok_type)


# See unit tests in frontend/match_test.py.
# We need the [^\0]* because the re2c translation assumes it's anchored like $.
SHOULD_HIJACK_RE = r'#![^\0]*sh[ \t\r\n][^\0]*'

# Separates words (\r it not whitespace here)
_SIGNIFICANT_SPACE = R(r'[ \t]+', Id.WS_Space)

_BACKSLASH = [
    # To be conservative, we could deny a set of chars similar to
    # _LITERAL_WHITELIST_REGEX, rather than allowing all the operator characters
    # like \( and \;.
    #
    # strict_backslash makes this stricter.
    R(r'\\[^\n\0]', Id.Lit_EscapedChar),
    C('\\\n', Id.Ignored_LineCont),
]

# Only 4 characters are backslash escaped inside "".
# https://www.gnu.org/software/bash/manual/bash.html#Double-Quotes
_DQ_BACKSLASH = [
    R(r'\\[$`"\\]', Id.Lit_EscapedChar),
    C('\\', Id.Lit_BadBackslash),  # syntax error in YSH, but NOT in OSH
]

VAR_NAME_RE = r'[a-zA-Z_][a-zA-Z0-9_]*'

# All Kind.VSub
_VARS = [
    # Unbraced variables
    R(r'\$' + VAR_NAME_RE, Id.VSub_DollarName),
    R(r'\$[0-9]', Id.VSub_Number),
    C(r'$!', Id.VSub_Bang),
    C(r'$@', Id.VSub_At),
    C(r'$#', Id.VSub_Pound),
    C(r'$$', Id.VSub_Dollar),
    C(r'$*', Id.VSub_Star),
    C(r'$-', Id.VSub_Hyphen),
    C(r'$?', Id.VSub_QMark),
]

# Kind.Left that are valid in double-quoted modes.

_LEFT_SUBS = [
    C('`', Id.Left_Backtick),
    C('$(', Id.Left_DollarParen),
    C('${', Id.Left_DollarBrace),
    C('$((', Id.Left_DollarDParen),
    C('$[', Id.Left_DollarBracket),
]

# Additional Kind.Left that are valid in unquoted modes.
_LEFT_UNQUOTED = [
    C('"', Id.Left_DoubleQuote),
    C("'", Id.Left_SingleQuote),
    C('$"', Id.Left_DollarDoubleQuote),
    C("$'", Id.Left_DollarSingleQuote),
]

_LEFT_PROCSUB = [
    C('<(', Id.Left_ProcSubIn),
    C('>(', Id.Left_ProcSubOut),
]

# The regexes below are in Python syntax, but are translate to re2c syntax by
# frontend/lexer_gen.py.
#
# http://re2c.org/manual/syntax/syntax.html
# https://docs.python.org/2/library/re.html
#
# We use a limited set of constructs:
# - + and * for repetition
# - Character classes [] with simple ranges and negation
# - Escapes like \n \0

LEXER_DEF = {}  # TODO: Should be a list so we enforce order.

# Anything until the end of the line is a comment.  Does not match the newline
# itself.  We want to switch modes and possibly process Op_Newline for here
# docs, etc.
LEXER_DEF[lex_mode_e.Comment] = [R(r'[^\n\0]*', Id.Ignored_Comment)]

# A whitelist to make bigger Lit_Chars tokens.  We don't want one byte at a time.
#
# The shell language says that "anything other byte" is a literal character --
# for example, unquoted $ \ ! are literal, not a syntax error.
#
# That is, a literal is defined NEGATIVELY, for a single characters.  But here
# we define a SUBSET of literal chars POSITIVELY.

# The range \x80-\xff makes sure that UTF-8 sequences are a single token.
_LITERAL_WHITELIST_REGEX = r'[\x80-\xffa-zA-Z0-9_.\-]+'

_UNQUOTED = _BACKSLASH + _LEFT_SUBS + _LEFT_UNQUOTED + _LEFT_PROCSUB + _VARS + [
    # NOTE: We could add anything 128 and above to this character class?  So
    # utf-8 characters don't get split?
    R(_LITERAL_WHITELIST_REGEX, Id.Lit_Chars),
    C('~', Id.Lit_Tilde),  # for tilde sub
    C('/', Id.Lit_Slash),  # also for tilde sub
    C(':', Id.Lit_Colon),  # for special PATH=a:~foo tilde detection
    C('$', Id.Lit_Dollar),  # shopt -u parse_dollar
    C('#', Id.Lit_Pound),  # For comments
    _SIGNIFICANT_SPACE,
    C('\n', Id.Op_Newline),
    C('&', Id.Op_Amp),
    C('|', Id.Op_Pipe),
    C('|&', Id.Op_PipeAmp),
    C('&&', Id.Op_DAmp),
    C('||', Id.Op_DPipe),
    C(';', Id.Op_Semi),
    # Case terminators
    C(';;', Id.Op_DSemi),
    C(';&', Id.Op_SemiAmp),
    C(';;&', Id.Op_DSemiAmp),
    C('(', Id.Op_LParen),
    C(')', Id.Op_RParen),
    R(r'[^\0]', Id.Lit_Other),  # any other single char is a literal
]

# In ShCommand and DBracket states.
_EXTGLOB_BEGIN = [
    C(',(', Id.ExtGlob_Comma),  # YSH synonym for @(...)
    C('@(', Id.ExtGlob_At),
    C('*(', Id.ExtGlob_Star),
    C('+(', Id.ExtGlob_Plus),
    C('?(', Id.ExtGlob_QMark),
    C('!(', Id.ExtGlob_Bang),
]

KEYWORDS = [
    # NOTE: { is matched elsewhere
    C('[[', Id.KW_DLeftBracket),
    C('!', Id.KW_Bang),
    C('for', Id.KW_For),
    C('while', Id.KW_While),
    C('until', Id.KW_Until),
    C('do', Id.KW_Do),
    C('done', Id.KW_Done),
    C('in', Id.KW_In),
    C('case', Id.KW_Case),
    C('esac', Id.KW_Esac),
    C('if', Id.KW_If),
    C('fi', Id.KW_Fi),
    C('then', Id.KW_Then),
    C('else', Id.KW_Else),
    C('elif', Id.KW_Elif),
    C('function', Id.KW_Function),
    C('time', Id.KW_Time),

    # YSH
    C('const', Id.KW_Const),  # maybe remove this
    C('var', Id.KW_Var),
    C('setvar', Id.KW_SetVar),
    C('setglobal', Id.KW_SetGlobal),
    C('call', Id.KW_Call),
    C('proc', Id.KW_Proc),
    C('typed', Id.KW_Typed),
    C('func', Id.KW_Func),
]

# These are treated like builtins in bash, but keywords in OSH.  However, we
# maintain compatibility with bash for the 'type' builtin.
CONTROL_FLOW = [
    C('break', Id.ControlFlow_Break),
    C('continue', Id.ControlFlow_Continue),
    C('return', Id.ControlFlow_Return),
    C('exit', Id.ControlFlow_Exit),
]

# Used by ysh/grammar_gen.py too
EXPR_WORDS = [
    C('null', Id.Expr_Null),
    C('true', Id.Expr_True),
    C('false', Id.Expr_False),
    C('and', Id.Expr_And),
    C('or', Id.Expr_Or),
    C('not', Id.Expr_Not),
    C('for', Id.Expr_For),
    C('is', Id.Expr_Is),
    C('in', Id.Expr_In),
    C('if', Id.Expr_If),
    C('else', Id.Expr_Else),

    # Unused: could be for function literals, although we also have
    # |x| x+1 lambdas
    C('func', Id.Expr_Func),

    # / <capture d+/
    C('capture', Id.Expr_Capture),
    # / <capture d+ as date> /
    C('as', Id.Expr_As),
]

FD_VAR_NAME = r'\{' + VAR_NAME_RE + r'\}'

# file descriptors can only have two digits, like mksh
# dash/zsh/etc. can have one
FD_NUM = r'[0-9]?[0-9]?'

# These two can must be recognized in the ShCommand state, but can't nested
# within [[.
# Keywords have to be checked before _UNQUOTED so we get <KW_If "if"> instead
# of <Lit_Chars "if">.
LEXER_DEF[lex_mode_e.ShCommand] = [
    # These four are not allowed within [[, so they are in ShCommand but not
    # _UNQUOTED.

    # e.g. beginning of NAME=val, which will always be longer than
    # _LITERAL_WHITELIST_REGEX.
    R(VAR_NAME_RE + '\+?=', Id.Lit_VarLike),
    R(VAR_NAME_RE + '\[', Id.Lit_ArrayLhsOpen),
    R(r'\]\+?=', Id.Lit_ArrayLhsClose),
    C('((', Id.Op_DLeftParen),

    # For static globbing, and [] for array literals
    C('[', Id.Lit_LBracket),  # e.g. A=(['x']=1)
    C(']', Id.Lit_RBracket),  # e.g. *.[ch]
    # NOTE: Glob_Star and Glob_QMark are for dynamic parsing
    C('*', Id.Lit_Star),
    C('?', Id.Lit_QMark),
    C('###', Id.Lit_TPound),  # like Lit_Pound, for doc comments
    C('...', Id.Lit_TDot),  # ... for multiline commands

    # For brace expansion {a,b}
    C('{', Id.Lit_LBrace),
    C('}', Id.Lit_RBrace),  # Also for var sub ${a}
    C(',', Id.Lit_Comma),
    C('=', Id.Lit_Equals),  # for = f(x) and x = 1+2*3
    C('@', Id.Lit_At),  # for detecting @[, @' etc. shopt -s parse_at_all

    # @array and @func(1, c)
    R('@' + VAR_NAME_RE, Id.Lit_Splice),  # for YSH splicing
    C('@[', Id.Lit_AtLBracket),  # @[split(x)]
    C('@{.', Id.Lit_AtLBraceDot),  # for split builtin sub @{.myproc arg1}
    R(FD_NUM + r'<', Id.Redir_Less),
    R(FD_NUM + r'>', Id.Redir_Great),
    R(FD_NUM + r'<<', Id.Redir_DLess),
    R(FD_NUM + r'<<<', Id.Redir_TLess),
    R(FD_NUM + r'>>', Id.Redir_DGreat),
    R(FD_NUM + r'<<-', Id.Redir_DLessDash),
    R(FD_NUM + r'>&', Id.Redir_GreatAnd),
    R(FD_NUM + r'<&', Id.Redir_LessAnd),
    R(FD_NUM + r'<>', Id.Redir_LessGreat),
    R(FD_NUM + r'>\|', Id.Redir_Clobber),
    R(FD_VAR_NAME + r'<', Id.Redir_Less),
    R(FD_VAR_NAME + r'>', Id.Redir_Great),
    R(FD_VAR_NAME + r'<<', Id.Redir_DLess),
    R(FD_VAR_NAME + r'<<<', Id.Redir_TLess),
    R(FD_VAR_NAME + r'>>', Id.Redir_DGreat),
    R(FD_VAR_NAME + r'<<-', Id.Redir_DLessDash),
    R(FD_VAR_NAME + r'>&', Id.Redir_GreatAnd),
    R(FD_VAR_NAME + r'<&', Id.Redir_LessAnd),
    R(FD_VAR_NAME + r'<>', Id.Redir_LessGreat),
    R(FD_VAR_NAME + r'>\|', Id.Redir_Clobber),

    # No leading descriptor (2 is implied)
    C(r'&>', Id.Redir_AndGreat),
    C(r'&>>', Id.Redir_AndDGreat),
] + KEYWORDS + CONTROL_FLOW + _UNQUOTED + _EXTGLOB_BEGIN

# Preprocessing before ShCommand
LEXER_DEF[lex_mode_e.Backtick] = [
    C(r'`', Id.Backtick_Right),
    # A backslash, and then $ or ` or \
    R(r'\\[$`\\]', Id.Backtick_Quoted),
    # \" treated specially, depending on whether bacticks are double-quoted!
    R(r'\\"', Id.Backtick_DoubleQuote),
    R(r'[^`\\\0]+', Id.Backtick_Other),  # contiguous run of literals
    R(r'[^\0]', Id.Backtick_Other),  # anything else
]

# DBRACKET: can be like ShCommand, except:
# - Don't really need redirects either... Redir_Less could be Op_Less
# - Id.Op_DLeftParen can't be nested inside.
LEXER_DEF[lex_mode_e.DBracket] = [
    C(']]', Id.Lit_DRightBracket),
    # Must be KW and not Op, because we can have stuff like [[ $foo == !* ]]
    # in addition to [[ ! a && b ]]
    C('!', Id.KW_Bang),
    C('<', Id.Op_Less),
    C('>', Id.Op_Great),
] + ID_SPEC.LexerPairs(Kind.BoolUnary) + \
    ID_SPEC.LexerPairs(Kind.BoolBinary) + \
    _UNQUOTED + _EXTGLOB_BEGIN

# Inside an extended glob, most characters are literals, including spaces and
# punctuation.  We also accept \, $var, ${var}, "", etc.  They can also be
# nested, so _EXTGLOB_BEGIN appears here.
#
# Example: echo @(<> <>|&&|'foo'|$bar)
LEXER_DEF[lex_mode_e.ExtGlob] = \
    _BACKSLASH + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + _EXTGLOB_BEGIN + [
    R(r'[^\\$`"\'|)@*+!?\0]+', Id.Lit_Chars),
    C('|', Id.Op_Pipe),
    C(')', Id.Op_RParen),  # maybe be translated to Id.ExtGlob_RParen
    R(r'[^\0]', Id.Lit_Other),  # everything else is literal
]

# Notes on BASH_REGEX states
#
# From bash manual:
#
# - Any part of the pattern may be quoted to force the quoted portion to be
# matched as a string.
# - Bracket expressions in regular expressions must be treated carefully, since
# normal quoting characters lose their meanings between brackets.
# - If the pattern is stored in a shell variable, quoting the variable
# expansion forces the entire pattern to be matched as a string.
#
# Is there a re.escape function?  It's just like EscapeGlob and UnescapeGlob.
#
# TODO: For testing, write a script to extract and save regexes... and compile
# them with regcomp.  I've only seen constant regexes.
#
# bash code: ( | ) are special

LEXER_DEF[lex_mode_e.BashRegex] = _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
    # Like lex_mode_e.ShCommand
    R(_LITERAL_WHITELIST_REGEX, Id.Lit_Chars),

    # Tokens for Tilde sub.  bash weirdness: RHS of [[ x =~ ~ ]] is expanded
    C('~', Id.Lit_Tilde),
    C('/', Id.Lit_Slash),

    # Id.WS_Space delimits words.  In lex_mode_e.BashRegexFakeInner, we
    # translate them to Id.Lit_Chars.
    _SIGNIFICANT_SPACE,

    # Analogous to Id.ExtGlob_* - we need to change lexer modes when we hit this
    C('(', Id.BashRegex_LParen),

    # Not special, this is like lex_mode_e.Outer
    C(')', Id.Op_RParen),

    # Copied and adapted from _UNQUOTED
    # \n & ; < > are parse errors OUTSIDE a group   [[ s =~ ; ]]
    #            but become allowed INSIDE a group  [[ s =~ (;) ]]
    C('\n', Id.BashRegex_AllowedInParens),
    C('&', Id.BashRegex_AllowedInParens),
    C(';', Id.BashRegex_AllowedInParens),
    C('>', Id.BashRegex_AllowedInParens),
    C('<', Id.BashRegex_AllowedInParens),

    # e.g. | is Id.Lit_Other, not pipe operator
    R(r'[^\0]', Id.Lit_Other),  # like _UNQUOTED, any other byte is literal
] + _BACKSLASH  # These have to come after RegexMeta

LEXER_DEF[lex_mode_e.DQ] = _DQ_BACKSLASH + [
    C('\\\n', Id.Ignored_LineCont),
] + _LEFT_SUBS + _VARS + [
    R(r'[^$`"\0\\]+', Id.Lit_Chars),  # matches a line at most
    C('$', Id.Lit_Dollar),  # completion of var names relies on this
    # NOTE: When parsing here doc line, this token doesn't end it.
    C('"', Id.Right_DoubleQuote),
]

_VS_ARG_COMMON = [
    C('/', Id.Lit_Slash),  # for patsub (not Id.VOp2_Slash)
    C('#', Id.Lit_Pound),  # for patsub prefix (not Id.VOp1_Pound)
    C('%', Id.Lit_Percent),  # for patsdub suffix (not Id.VOp1_Percent)
    C('}', Id.Right_DollarBrace),  # For var sub "${a}"
    C('$', Id.Lit_Dollar),  # completion of var names relies on this
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VSub_ArgUnquoted] = \
  _BACKSLASH + _VS_ARG_COMMON + _LEFT_SUBS + _LEFT_UNQUOTED + _LEFT_PROCSUB + \
  _VARS + _EXTGLOB_BEGIN + [

    # Token for Tilde sub
    C('~', Id.Lit_Tilde),

    # - doesn't match ~ for tilde sub
    # - doesn't match < and > so it doesn't eat <()
    # - doesn't match  @ ! ? + * so it doesn't eat _EXTGLOB_BEGIN -- ( alone it
    #   not enough
    R(r'[^$`~/}"\'\0\\#%<>@!?+*]+', Id.Lit_Chars),
    R(r'[^\0]', Id.Lit_Other),  # e.g. "$", must be last
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VSub_ArgDQ] = \
  _DQ_BACKSLASH +  _VS_ARG_COMMON + _LEFT_SUBS + _VARS + [

    C(r'\}', Id.Lit_EscapedChar),  # For "${var-\}}"

    R(r'[^$`/}"\0\\#%]+', Id.Lit_Chars),  # matches a line at most

    # Weird wart: even in double quoted state, double quotes are allowed
    C('"', Id.Left_DoubleQuote),

    # Another weird wart of bash/mksh: $'' is recognized but NOT ''!
    C("$'", Id.Left_DollarSingleQuote),
]

# NOTE: Id.Ignored_LineCont is NOT supported in SQ state, as opposed to DQ
# state.
LEXER_DEF[lex_mode_e.SQ_Raw] = [
    R(r"[^'\0]+", Id.Lit_Chars),  # matches a line at most
    C("'", Id.Right_SingleQuote),
]

# The main purpose for EXPR_CHARS is in regex literals, e.g. [a-z \t \n].
#
# In YSH expressions, Chars are code point integers, so \u{1234} is the same as
# 0x1234.  And \0 is 0x0.

# In Python:
# chr(0x00012345) == u'\U00012345'
#
# In YSH:
# 0x00012345 == \u{12345}
# chr(0x00012345) == chr(\u{12345}) == $'\u{012345}'

_U_BRACED_CHAR = R(r'\\[uU]\{[0-9a-fA-F]{1,6}\}', Id.Char_UBraced)

_X_CHAR_LOOSE = R(r'\\x[0-9a-fA-F]{1,2}', Id.Char_Hex)  # bash
_X_CHAR_STRICT = R(r'\\x[0-9a-fA-F]{2}', Id.Char_Hex)  # YSH

_U4_CHAR_LOOSE = R(r'\\u[0-9a-fA-F]{1,4}', Id.Char_Unicode4)  # bash

_U4_CHAR_STRICT = R(r'\\u[0-9a-fA-F]{4}', Id.Char_Unicode4)  # JSON-only

EXPR_CHARS = [
    # This is like Rust.  We don't have the legacy C escapes like \b.

    # NOTE: \' and \" are more readable versions of '"' and "'" in regexs
    R(r'\\[0rtn\\"%s]' % "'", Id.Char_OneChar),
    _X_CHAR_STRICT,

    # Because 'a' is a string, we use the syntax #'a' for char literals.
    # We explicitly leave out #''' because it's confusing.
    # Note: we're not doing utf-8 validation here.
    R(r"#'[^'\0]'", Id.Char_Pound),
    _U_BRACED_CHAR,
]

# Shared between echo -e and $''.
_C_STRING_COMMON = [

    # \x6 is valid in bash
    _X_CHAR_LOOSE,
    _U4_CHAR_LOOSE,
    R(r'\\U[0-9a-fA-F]{1,8}', Id.Char_Unicode8),
    R(r'\\[0abeEfrtnv\\]', Id.Char_OneChar),

    # e.g. \A is not an escape, and \x doesn't match a hex escape.  We allow it,
    # but a lint tool could warn about it.
    C('\\', Id.Unknown_Backslash),
]

ECHO_E_DEF = _C_STRING_COMMON + [
    # Note: tokens above \0377 can either be truncated or be flagged a syntax
    # error in strict mode.
    R(r'\\0[0-7]{1,3}', Id.Char_Octal4),
    C(r'\c', Id.Char_Stop),

    # e.g. 'foo', anything that's not a backslash escape
    R(r'[^\\\0]+', Id.Lit_Chars),
]

# https://json.org/

# Note that [0-9] has to come second, because Python chooses the first match.
_JSON_INT = r'-?([1-9][0-9]*|[0-9])'  # Numbers can't start with leading 0
_JSON_FRACTION = r'(\.[0-9]+)?'
_JSON_EXP = r'([eE][-+]?[0-9]+)?'

# R5RS extended alphabetic characters
# https://groups.csail.mit.edu/mac/ftpdir/scheme-reports/r5rs-html/r5rs_4.html
#
#   ! $ % & * + - . / : < = > ? @ ^ _ ~

# Description from Guile Scheme - https://www.gnu.org/software/guile/manual/html_node/Symbol-Read-Syntax.html
#
# "The read syntax for a symbol is a sequence of letters, digits, and extended
# alphabetic characters, beginning with a character that cannot begin a
# number. In addition, the special cases of +, -, and ... are read as symbols
# even though numbers can begin with +, - or ."
#
# (They should have used regular languages!)

# We take out $ and @ for our splicing syntax, i.e. $unquote and
# @unquote-splicing.  And : for now because we use it for name:value.

# Also note Scheme allows |a b| for symbols with funny chars, and Guile scheme
# allows #{a b}#.  We could use `a b` or (symbol "a b").

J8_SYMBOL_CHARS = r'!%&*+./<=>?^_~-'  # - is last for regex char class

# yapf: disable
J8_SYMBOL_RE = (
    r'[a-zA-Z' + J8_SYMBOL_CHARS + ']' +
    r'[a-zA-Z0-9' + J8_SYMBOL_CHARS + ']*')
# yapf: enable

_J8_LEFT = [
    C('"', Id.Left_DoubleQuote),  # JSON string
    # Three left quotes that are J8 only
    C("u'", Id.Left_USingleQuote),  # unicode string
    C("'", Id.Left_USingleQuote),  # '' is alias for u'' in data, not in code
    C("b'", Id.Left_BSingleQuote),  # byte string
]

J8_DEF = _J8_LEFT + [
    C('[', Id.J8_LBracket),
    C(']', Id.J8_RBracket),
    C('{', Id.J8_LBrace),
    C('}', Id.J8_RBrace),
    C('(', Id.J8_LParen),  # NIL8 only
    C(')', Id.J8_RParen),  # NIL8 only
    C(',', Id.J8_Comma),
    C(':', Id.J8_Colon),
    C('null', Id.J8_Null),
    C('true', Id.J8_Bool),
    C('false', Id.J8_Bool),
    R(_JSON_INT, Id.J8_Int),
    R(_JSON_INT + _JSON_FRACTION + _JSON_EXP, Id.J8_Float),

    # Identifier names come AFTER null true false.
    # - Happens to be the same as shell identifier # names.
    # - Note that JS allows $ as an identifier, but we don't.
    # - Used for dict keys / NIL8 field names.
    R(VAR_NAME_RE, Id.J8_Identifier),

    # Symbol is a SUPERSET of Identifier.  The first word in NIL8 can be can
    # be either Symbol or plain Identifier, but field names can only be
    # Identifier.  JSON8 only has Identifier.
    #R(J8_SYMBOL_RE, Id.J8_Symbol),  # NIL8 only
    R(r'[~!@$%^&*+=|;./<>?-]+', Id.J8_Operator),  # NIL8 only

    # TODO: emit Id.Ignored_Newline to count lines for error messages?
    R(r'[ \r\n\t]+', Id.Ignored_Space),
    # comment is # until end of line
    # // comments are JavaScript style, but right now we might want them as
    # symbols?
    R(r'#[^\n\0]*', Id.Ignored_Comment),  # J8 only (JSON8, NIL8)

    # This will reject ASCII control chars
    R(r'[^\0]', Id.Unknown_Tok),
]

# Exclude control characters 0x00-0x1f, aka 0-31 in J8 data only (not YSH code)
_ASCII_CONTROL = R(r'[\x01-\x1F]', Id.Char_AsciiControl)

J8_LINES_DEF = _J8_LEFT + [
    # not sure if we want \r here - same with lex_mode_e.Expr
    R(r'[ \r\t]+', Id.WS_Space),
    R(r'[\n]', Id.Op_Newline),

    # doesn't match \t, which means tabs are allowed in the middle of unquoted
    # lines
    _ASCII_CONTROL,

    # not space or ' or " or ASCII control or EOF
    R(r'''[^ \t\r\n'"\x00-\x1F]+''', Id.Lit_Chars),
]

# https://json.org list of chars, plus '
_JSON_ONE_CHAR = R(r'\\[\\"/bfnrt]', Id.Char_OneChar)

# Union of escapes that "" u"" b"" accept.  Validation is separate.

_J8_STR_COMMON = [
    C("'", Id.Right_SingleQuote),  # end for J8
    _JSON_ONE_CHAR,
    C("\\'", Id.Char_OneChar),

    # osh/word_parse.py relies on this.  It has to match $'', which uses _C_STRING_COMMON
    C('\\', Id.Unknown_Backslash),
    R(r'\\y[0-9a-fA-F]{2}', Id.Char_YHex),  # \yff - J8 only
    _U_BRACED_CHAR,  # \u{123456} - J8 only
]

# ASCII control characters are disallowed in DATA, but not CODE!
J8_STR_DEF = _J8_STR_COMMON + [
    _ASCII_CONTROL,
    # will match invalid UTF-8 - we have a separate validation step
    R(r"[^\\'\x00-\x1F]+", Id.Lit_Chars),
]

# For "JSON strings \" \u1234"
JSON_STR_DEF = [
    C('"', Id.Right_DoubleQuote),  # end for JSON
    _JSON_ONE_CHAR,
    _U4_CHAR_STRICT,  # \u1234 - JSON only

    # High surrogate [\uD800, \uDC00)
    # Low surrogate  [\uDC00, \uE000)
    # This pattern makes it easier to decode.  Unpaired surrogates because Id.Char_Unicode4.
    R(
        r'\\u[dD][89aAbB][0-9a-fA-F][0-9a-fA-F]\\u[dD][cCdDeEfF][0-9a-fA-F][0-9a-fA-F]',
        Id.Char_SurrogatePair),
    _ASCII_CONTROL,

    # Note: This will match INVALID UTF-8.  UTF-8 validation is another step.
    R(r'[^\\"\x00-\x1F]+', Id.Lit_Chars),
    R(r'[^\0]', Id.Unknown_Tok),
]

LEXER_DEF[lex_mode_e.J8_Str] = _J8_STR_COMMON + [
    # don't produce Char_AsciiControl tokens - that's only for data

    # will match invalid UTF-8 - we have a separate validation step
    R(r"[^\\'\0]+", Id.Lit_Chars),
]

OCTAL3_RE = r'\\[0-7]{1,3}'

# https://www.gnu.org/software/bash/manual/html_node/Controlling-the-PromptEvaluator.html#Controlling-the-PromptEvaluator
PS1_DEF = [
    R(OCTAL3_RE, Id.PS_Octal3),
    R(r'\\[adehHjlnrstT@AuvVwW!#$\\]', Id.PS_Subst),
    # \D{%H:%M} strftime format
    R(r'\\D\{[^}\0]*\}', Id.PS_Subst),
    C(r'\[', Id.PS_LBrace),  # non-printing
    C(r'\]', Id.PS_RBrace),
    R(r'[^\\\0]+', Id.PS_Literals),
    # e.g. \x is not a valid escape.
    C('\\', Id.PS_BadBackslash),
]

# NOTE: Id.Ignored_LineCont is also not supported here, even though the whole
# point of it is that supports other backslash escapes like \n!  It just
# becomes a regular backslash.
LEXER_DEF[lex_mode_e.SQ_C] = _C_STRING_COMMON + [
    # Weird special case matching bash: backslash that ends a line.  We emit
    # this token literally in OSH, but disable it in YSH.
    C('\\\n', Id.Unknown_Backslash),

    # Silly difference!  In echo -e, the syntax is \0377, but here it's $'\377',
    # with no leading 0.
    R(OCTAL3_RE, Id.Char_Octal3),

    # ' and " are escaped in $'' mode, but not echo -e.
    C(r"\'", Id.Char_OneChar),
    C(r'\"', Id.Char_OneChar),

    # e.g. 'foo', anything that's not a backslash escape or '
    R(r"[^\\'\0]+", Id.Lit_Chars),
    C("'", Id.Right_SingleQuote),
]

LEXER_DEF[lex_mode_e.PrintfOuter] = _C_STRING_COMMON + [
    R(OCTAL3_RE, Id.Char_Octal3),
    R(r"[^%\\\0]+", Id.Lit_Chars),
    C('%%', Id.Format_EscapedPercent),
    C('%', Id.Format_Percent),
]

# Maybe: bash also supports %(strftime)T
LEXER_DEF[lex_mode_e.PrintfPercent] = [
    # Flags
    R('[- +#]', Id.Format_Flag),
    C('0', Id.Format_Zero),
    R('[1-9][0-9]*', Id.Format_Num),
    C('*', Id.Format_Star),
    C('.', Id.Format_Dot),
    # We support dsq.  The others we parse to display an error message.
    R('[disqbcouxXeEfFgG]', Id.Format_Type),
    R('\([^()\0]*\)T', Id.Format_Time),
    R(r'[^\0]', Id.Unknown_Tok),  # any other char
]

LEXER_DEF[lex_mode_e.VSub_1] = [
    R(VAR_NAME_RE, Id.VSub_Name),
    #  ${11} is valid, compared to $11 which is $1 and then literal 1.
    R(r'[0-9]+', Id.VSub_Number),
    C('!', Id.VSub_Bang),
    C('@', Id.VSub_At),
    C('#', Id.VSub_Pound),
    C('$', Id.VSub_Dollar),
    C('*', Id.VSub_Star),
    C('-', Id.VSub_Hyphen),
    C('?', Id.VSub_QMark),
    C('.', Id.VSub_Dot),  # ${.myproc builtin sub}
    C('}', Id.Right_DollarBrace),
    C('\\\n', Id.Ignored_LineCont),
    C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
    R(r'[^\0]', Id.Unknown_Tok),  # any char except newline
]

LEXER_DEF[lex_mode_e.VSub_2] = \
    ID_SPEC.LexerPairs(Kind.VTest) + \
    ID_SPEC.LexerPairs(Kind.VOp0) + \
    ID_SPEC.LexerPairs(Kind.VOpYsh) + \
    ID_SPEC.LexerPairs(Kind.VOp1) + \
    ID_SPEC.LexerPairs(Kind.VOp2) + \
    ID_SPEC.LexerPairs(Kind.VOp3) + [
    C('}', Id.Right_DollarBrace),

    C('\\\n', Id.Ignored_LineCont),
    C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
    R(r'[^\0]', Id.Unknown_Tok),  # any char except newline
]

_EXPR_ARITH_SHARED = [
    C('\\\n', Id.Ignored_LineCont),
    R(r'[^\0]', Id.Unknown_Tok)  # any char.  This should be a syntax error.
]

# https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html#Shell-Arithmetic
LEXER_DEF[lex_mode_e.Arith] = \
    _LEFT_SUBS + _VARS + _LEFT_UNQUOTED + [

    # Arithmetic expressions can cross newlines.
    R(r'[ \t\r\n]+', Id.Ignored_Space),

    # Examples of arith constants:
    #   64#azAZ
    #   0xabc 0xABC
    #   0123
    # A separate digits token makes this easier to parse STATICALLY.  But this
    # doesn't help with DYNAMIC parsing.
    R(VAR_NAME_RE, Id.Lit_ArithVarLike),  # for variable names or 64#_
    R(r'[0-9]+', Id.Lit_Digits),
    C('@', Id.Lit_At),  # for 64#@ or ${a[@]}
    C('#', Id.Lit_Pound),  # for 64#a

    # TODO: 64#@ interferes with VS_AT.  Hm.
] + ID_SPEC.LexerPairs(Kind.Arith) + _EXPR_ARITH_SHARED

# A lexer for the parser that converts globs to extended regexes.  Since we're
# only parsing character classes ([^[:space:][:alpha:]]) as opaque blobs, we
# don't need lexer modes here.
GLOB_DEF = [
    # These could be operators in the glob, or just literals in a char class,
    # e.g.  touch '?'; echo [?].
    C('*', Id.Glob_Star),
    C('?', Id.Glob_QMark),

    # For negation.  Treated as operators inside [], but literals outside.
    C('!', Id.Glob_Bang),
    C('^', Id.Glob_Caret),

    # Character classes.
    C('[', Id.Glob_LBracket),
    C(']', Id.Glob_RBracket),

    # There is no whitelist of characters; backslashes are unconditionally
    # removed.  With libc.fnmatch(), the pattern r'\f' matches 'f' but not '\\f'.
    # See libc_test.py.
    R(r'\\[^\0]', Id.Glob_EscapedChar),
    C('\\', Id.Glob_BadBackslash),  # Trailing single backslash

    # For efficiency, combine other characters into a single token,  e.g. 'py' in
    # '*.py' or 'alpha' in '[[:alpha:]]'.
    R(r'[a-zA-Z0-9_]+', Id.Glob_CleanLiterals),  # no regex escaping
    R(r'[^\0]', Id.Glob_OtherLiteral),  # anything else -- examine the char
]

# History expansion.  We're doing this as "pre-lexing" since that's what bash
# and zsh seem to do.  Example:
#
# $ foo=x
# $ echo $
# $ !!foo   # expands to echo $foo and prints x
#
# We can also reuse this in the RootCompleter to expand history interactively.
#
# bash note: handled in lib/readline/histexpand.c.  Quite messy and handles
# quotes AGAIN.
#
# Note: \! gets expanded to literal \! for the real lexer, but no history
# expansion occurs.

HISTORY_DEF = [
    # Common operators.
    R(r'![!*^$]', Id.History_Op),

    # By command number.
    R(r'!-?[0-9]+', Id.History_Num),

    # Search by prefix of substring (optional '?').
    # NOTE: there are no numbers allowed here!  Bash doesn't seem to support it.
    # No hyphen since it conflits with $-1 too.
    #
    # Required trailing whitespace is there to avoid conflict with [!charclass]
    # and ${!indirect}.  This is a simpler hack than the one bash has.  See
    # frontend/lex_test.py.
    R(r'!\??[a-zA-Z_/.][0-9a-zA-Z_/.]+[ \t\r\n]', Id.History_Search),

    # Comment is until end of line
    R(r"#[^\0]*", Id.History_Other),

    # Single quoted, e.g. 'a' or $'\n'.  Terminated by another single quote or
    # end of string.
    R(r"'[^'\0]*'?", Id.History_Other),

    # Runs of chars that are definitely not special
    R(r"[^!\\'#\0]+", Id.History_Other),

    # Escaped characters.  \! disables history
    R(r'\\[^\0]', Id.History_Other),
    # Other single chars, like a trailing \ or !
    R(r'[^\0]', Id.History_Other),
]

BRACE_RANGE_DEF = [
    R(r'-?[0-9]+', Id.Range_Int),
    R(r'[a-zA-Z]', Id.Range_Char),  # just a single character
    R(r'\.\.', Id.Range_Dots),
    R(r'[^\0]', Id.Range_Other),  # invalid
]

#
# YSH lexing
#

# Valid in lex_mode_e.{Expr,DQ}
# Used by ysh/grammar_gen.py
YSH_LEFT_SUBS = [
    C('$(', Id.Left_DollarParen),
    C('${', Id.Left_DollarBrace),
    C('$[', Id.Left_DollarBracket),  # TODO: Implement $[x]
]

# Valid in lex_mode_e.Expr, but not valid in DQ
# Used by ysh/grammar_gen.py

YSH_LEFT_UNQUOTED = [
    C('"', Id.Left_DoubleQuote),
    # In expression mode, we add the r'' and c'' prefixes for '' and $''.
    C("'", Id.Left_SingleQuote),
    C("r'", Id.Left_RSingleQuote),
    C("u'", Id.Left_USingleQuote),
    C("b'", Id.Left_BSingleQuote),
    C("$'", Id.Left_DollarSingleQuote),
    C('^"', Id.Left_CaretDoubleQuote),
    C('"""', Id.Left_TDoubleQuote),
    # In expression mode, we add the r'' and c'' prefixes for '' and $''.
    C("'''", Id.Left_TSingleQuote),
    C("r'''", Id.Left_RTSingleQuote),
    C("u'''", Id.Left_UTSingleQuote),
    C("b'''", Id.Left_BTSingleQuote),
    C('@(', Id.Left_AtParen),  # Split Command Sub
    C('^(', Id.Left_CaretParen),  # Block literals in expression mode
    C('^[', Id.Left_CaretBracket),  # Expr literals
    C('^{', Id.Left_CaretBrace),  # Unused
    C(':|', Id.Left_ColonPipe),  # shell-like word arrays.
    C('%(', Id.Left_PercentParen),  # old syntax for shell-like word arrays.
    C('%[', Id.Expr_Reserved),  # Maybe: like %() without unquoted [], {}
    C('%{', Id.Expr_Reserved),  # Table literals
    # t = %{
    #    name:Str  age:Int
    #    'andy c'  10
    # }
    # Significant newlines.  No unquoted [], {}

    # Not sure if we'll use these
    C('@{', Id.Expr_Reserved),
    C('@[', Id.Expr_Reserved),

    # Idea: Set literals are #{a, b} like Clojure
]

# Used by ysh/grammar_gen.py
EXPR_OPS = [
    # Terminator
    C(';', Id.Op_Semi),
    C('(', Id.Op_LParen),
    C(')', Id.Op_RParen),
    # NOTE: type expressions are expressions, e.g. Dict[Str, Int]
    C('[', Id.Op_LBracket),
    C(']', Id.Op_RBracket),
    C('{', Id.Op_LBrace),
    C('}', Id.Op_RBrace),
]

# Newline is significant, but sometimes elided by expr_parse.py.
_EXPR_NEWLINE_COMMENT = [
    C('\n', Id.Op_Newline),
    R(r'#[^\n\0]*', Id.Ignored_Comment),
    # Like lex_mode_e.Arith, \r is whitespace even without \n
    R(r'[ \t\r]+', Id.Ignored_Space),
]

_WHITESPACE = r'[ \t\r\n]*'  # ASCII whitespace doesn't have legacy \f \v

# Python allows 0 to be written 00 or 0_0_0, which is weird.  But let's be
# consistent, and avoid '00' turning into a float!
_DECIMAL_INT_RE = r'[0-9](_?[0-9])*'

# Used for YSH comparison operators > >= < <=
LOOKS_LIKE_INTEGER = _WHITESPACE + '-?' + _DECIMAL_INT_RE + _WHITESPACE

_FLOAT_RE = (
    _DECIMAL_INT_RE +
    # Unlike Python, exponent can't be like 42e5_000.  There's no use because
    # 1e309 is already inf.  Let's keep our code simple.
    r'(\.' + _DECIMAL_INT_RE + ')?([eE][+\-]?[0-9]+)?')

# Ditto, used for comparison operators
# Added optional Optional -?
# Example: -3_000_000.000_001e12
LOOKS_LIKE_FLOAT = _WHITESPACE + '-?' + _FLOAT_RE + _WHITESPACE

# Python 3 float literals:

# digitpart     ::=  digit (["_"] digit)*
# fraction      ::=  "." digitpart
# exponent      ::=  ("e" | "E") ["+" | "-"] digitpart
# pointfloat    ::=  [digitpart] fraction | digitpart "."
# exponentfloat ::=  (digitpart | pointfloat) exponent
# floatnumber   ::=  pointfloat | exponentfloat

# NOTE: Borrowing tokens from Arith (i.e. $(( )) ), but not using LexerPairs().
LEXER_DEF[lex_mode_e.Expr] = \
    _VARS + YSH_LEFT_SUBS + YSH_LEFT_UNQUOTED + EXPR_OPS + EXPR_WORDS + \
    EXPR_CHARS + [

    # https://docs.python.org/3/reference/lexical_analysis.html#integer-literals
    #
    # integer      ::=  decinteger | bininteger | octinteger | hexinteger
    # decinteger   ::=  nonzerodigit (["_"] digit)* | "0"+ (["_"] "0")*
    # bininteger   ::=  "0" ("b" | "B") (["_"] bindigit)+
    # octinteger   ::=  "0" ("o" | "O") (["_"] octdigit)+
    # hexinteger   ::=  "0" ("x" | "X") (["_"] hexdigit)+
    # nonzerodigit ::=  "1"..."9"
    # digit        ::=  "0"..."9"
    # bindigit     ::=  "0" | "1"
    # octdigit     ::=  "0"..."7"
    # hexdigit     ::=  digit | "a"..."f" | "A"..."F"

    R(_DECIMAL_INT_RE, Id.Expr_DecInt),

    R(r'0[bB](_?[01])+', Id.Expr_BinInt),
    R(r'0[oO](_?[0-7])+', Id.Expr_OctInt),
    R(r'0[xX](_?[0-9a-fA-F])+', Id.Expr_HexInt),

    R(_FLOAT_RE, Id.Expr_Float),

    # These can be looked up as keywords separately, so you enforce that they have
    # space around them?
    R(VAR_NAME_RE, Id.Expr_Name),

    R('%' + VAR_NAME_RE, Id.Expr_Symbol),

    #
    # Arith
    #

    C(',', Id.Arith_Comma),
    C(':', Id.Arith_Colon),   # for slicing a[1:2], and mylist:pop()

    C('?', Id.Arith_QMark),   # regex postfix

    C('+', Id.Arith_Plus),    # arith infix, regex postfix
    C('-', Id.Arith_Minus),   # arith infix, regex postfix
    C('*', Id.Arith_Star),
    C('^', Id.Arith_Caret),   # xor
    C('/', Id.Arith_Slash),
    C('%', Id.Arith_Percent),

    C('**', Id.Arith_DStar),  # exponentiation
    C('++', Id.Arith_DPlus),  # Option for string/list concatenation

    C('<', Id.Arith_Less),
    C('>', Id.Arith_Great),
    C('<=', Id.Arith_LessEqual),
    C('>=', Id.Arith_GreatEqual),
    C('===', Id.Expr_TEqual),
    C('!==', Id.Expr_NotDEqual),

    C('==', Id.Unknown_DEqual),  # user must choose === or ~==

    # Bitwise operators
    C('&', Id.Arith_Amp),
    C('|', Id.Arith_Pipe),
    C('>>', Id.Arith_DGreat),
    C('<<', Id.Arith_DLess),  # Doesn't Java also have <<< ?

    # Bitwise complement, as well as infix pattern matching
    C('~', Id.Arith_Tilde),
    C('!~', Id.Expr_NotTilde),
    C('~~', Id.Expr_DTilde),
    C('!~~', Id.Expr_NotDTilde),

    # Left out for now:
    # ++ --       -- needed for loops, awk?
    # ! && ||     -- needed for find dialect
    # = += etc.

    C('=', Id.Arith_Equal),

    C('+=', Id.Arith_PlusEqual),
    C('-=', Id.Arith_MinusEqual),
    C('*=', Id.Arith_StarEqual),
    C('/=', Id.Arith_SlashEqual),
    C('%=', Id.Arith_PercentEqual),

    C('>>=', Id.Arith_DGreatEqual),
    C('<<=', Id.Arith_DLessEqual),
    C('&=', Id.Arith_AmpEqual),
    C('|=', Id.Arith_PipeEqual),
    C('^=', Id.Arith_CaretEqual),  # Exponentiation

    # Augmented assignment that YSH has, but sh and OSH don't have
    C('**=', Id.Expr_DStarEqual),
    C('//=', Id.Expr_DSlashEqual),

    #
    # Expr
    #

    C('!', Id.Expr_Bang),     # For eggex negation

    C('//', Id.Expr_DSlash),  # For YSH integer division
    C('~==', Id.Expr_TildeDEqual),  # approximate equality

    C('.', Id.Expr_Dot),      # d.key is alias for d['key']
    C('..', Id.Expr_DDot),    # range 1..5
    C('->', Id.Expr_RArrow),  # s->startswith()
    C('$', Id.Expr_Dollar),   # legacy regex end: /d+ $/ (better written /d+ >/

    # Reserved this.  Go uses it for channels, etc.
    # I guess it conflicts with -4<-3, but that's OK -- spaces suffices.
    C('<-', Id.Expr_Reserved),
    C('=>', Id.Expr_RDArrow), # for df => filter(age > 10)
                            # and match (x) { 1 => "one" }
                            # note: other languages use |>
                            # R/dplyr uses %>%

    C('...', Id.Expr_Ellipsis),  # f(...args) and maybe a[:, ...]

    # For multiline regex literals?
    C('///', Id.Expr_Reserved),

    # Splat operators
    C('@', Id.Expr_At),
    # NOTE: Unused
    C('@@', Id.Expr_DoubleAt),
] + _EXPR_NEWLINE_COMMENT + _EXPR_ARITH_SHARED

LEXER_DEF[lex_mode_e.FuncParens] = [
    # () with spaces
    R(r'[ \t]*\([ \t]*\)', Id.LookAhead_FuncParens),
    # anything else
    R(r'[^\0]', Id.Unknown_Tok)
]
