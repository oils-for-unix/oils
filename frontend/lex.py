"""
lex.py -- Shell lexer.

It consists of a series of lexer modes, each with a regex -> Id mapping.

NOTE: If this changes, the lexer may need to be recompiled with
build/codegen.sh lexer.

Input Handling
--------------

Note that our style of input Handling affects the regular expressions in the
lexer.

We pass one line at a time to the Lexer, via LineLexer.  We must be able to
parse one line at a time because of interactive parsing (e.g. using the output
of GNU readline.)

There are two ways we could handle input:

  1. Every line is NUL terminated:
     'one\n\0' 'last line\0'
  2. Every line is terminated by NUL, except the last:
     'one\n' 'last line\0'

The advantage of #2 is that in the common case of reading files, we don't have
to do it one line at a time.  We could slurp the whole file in, or mmap() it,
etc.

The second option makes the regular expressions more complicated, so I'm
punting on it for now.  We assume the first.

That means:

  - No regexes below should match \0.  They are added by
    core/lexer_gen.py for re2c.

For example, [^']+ is not valid.  [^'\0]+ is correct.  Otherwise we would read
unitialized memory past the sentinel.

Python's regex engine knows where the end of the input string is, so it
doesn't require need a sentinel like \0.

Note that re2c is not able to work in a mode with a strict length limit.  It
would cause too many extra checks?  The language is then no longer regular!

http://re2c.org/examples/example_03.html

UPDATE: Two More Options
------------------------

3. Change the \n at the end of every line to \0.  \0 becomes Id.Op_Newline, at
least in lex_mode.Outer.

Advantage: This makes the regular expressions easier to generate, but allows
you to read in the whole file at once instead of allocating lines.

Disadvantages:
- You can't mmap() the file because the data is mutated.  Or it will have to be
  copy-on-write.
- You can't get rid of comment lines if you read the whole file.

4. Read a line at a time.  Throw away the lines, unless you're parsing a
function, which should be obvious.

After you parse the function, you can COPY all the tokens to another location.
Very few tokens need their actual text data.  Most of them can just be
identified by ID.

Contents are relevant:

- Lit_Chars, Lit_Other, Lit_EscapedChar, Lit_Digits
- Id.Lit_VarLike -- for the name, and for = vs +=
- Id.Lit_ArithVarLike
- VSub_Name, VSub_Number
- Id.Redir_* for the LHS file descriptor.  Although this is one or two bytes
  that could be copied.

You can also take this opportunity to enter the strings in an intern table.
How much memory would that save?

Remaining constructs
--------------------

Case terminators:
  ;;&                  Op_DSemiAmp  for case
  ;&                   Op_Semi

Left Index:

  VAR_NAME_RE + '\['  Lit_LeftIndexLikeOpen
  ]=                   Lit_LeftIndexLikeClose

Indexed array and Associative array literals:
  declare -A a=([key]=value [key2]=value2)
  declare -a a=([1 + 2]=value [3 + 4]=value2)  # parsed!

  Lit_LBracket Lit_RBracketEqual
  Left_Bracket, Right_BracketEqual?
  Op_LBracket Op_RBracketEqual
"""

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.types_asdl import lex_mode_e
from core.meta import ID_SPEC
from frontend.lexer import C, R

# See unit tests in frontend/match_test.py.
# We need the [^\0]* because the re2c translation assumes it's anchored like $.
SHOULD_HIJACK_RE = r'#!.*sh[ \t\r\n][^\0]*'


_SIGNIFICANT_SPACE = R(r'[ \t\r]+', Id.WS_Space)

_BACKSLASH = [
  R(r'\\[^\n\0]', Id.Lit_EscapedChar),
  C('\\\n', Id.Ignored_LineCont),
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
  C("'", Id.Left_SingleQuoteRaw),
  C('$"', Id.Left_DollarDoubleQuote),
  C("$'", Id.Left_SingleQuoteC),

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
LEXER_DEF[lex_mode_e.Comment] = [
  R(r'[^\n\0]*', Id.Ignored_Comment)
]

# A whitelist for efficiency.  The shell language says that "anything else" is
# a literal character.  In other words, a single $ \ or ! is a literal, not a
# syntax error.  It's defined negatively, but let's define positive runs here.
# TODO: Add + and @ here they are never special?  It's different for Oil
# though.
_LITERAL_WHITELIST_REGEX = r'[a-zA-Z0-9_/.-]+'

_UNQUOTED = _BACKSLASH + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: We could add anything 128 and above to this character class?  So
  # utf-8 characters don't get split?
  R(_LITERAL_WHITELIST_REGEX, Id.Lit_Chars),

  # For tilde expansion. The list of chars is Lit_Chars, but WITHOUT the /.  We
  # want the next token after the tilde TildeLike token start with a /.
  # NOTE: Happens in both ShCommand and DBracket modes.
  R(r'~[a-zA-Z0-9_.-]*', Id.Lit_TildeLike),

  C('#', Id.Lit_Pound),  # For comments
  _SIGNIFICANT_SPACE,

  C('\n', Id.Op_Newline),

  C('&', Id.Op_Amp),
  C('|', Id.Op_Pipe),
  C('|&', Id.Op_PipeAmp),
  C('&&', Id.Op_DAmp),
  C('||', Id.Op_DPipe),
  C(';', Id.Op_Semi),
  C(';;', Id.Op_DSemi),

  C('(', Id.Op_LParen),
  C(')', Id.Op_RParen),

  R(r'[^\0]', Id.Lit_Other),  # any other single char is a literal
]

# In ShCommand and DBracket states.
_EXTGLOB_BEGIN = [
  C('@(', Id.ExtGlob_At),
  C('*(', Id.ExtGlob_Star),
  C('+(', Id.ExtGlob_Plus),
  C('?(', Id.ExtGlob_QMark),
  C('!(', Id.ExtGlob_Bang),
]

_KEYWORDS = [
  # NOTE: { is matched elsewhere
  C('[[',       Id.KW_DLeftBracket),
  C('!',        Id.KW_Bang),
  C('for',      Id.KW_For),
  C('while',    Id.KW_While),
  C('until',    Id.KW_Until),
  C('do',       Id.KW_Do),
  C('done',     Id.KW_Done),
  C('in',       Id.KW_In),
  C('case',     Id.KW_Case),
  C('esac',     Id.KW_Esac),
  C('if',       Id.KW_If),
  C('fi',       Id.KW_Fi),
  C('then',     Id.KW_Then),
  C('else',     Id.KW_Else),
  C('elif',     Id.KW_Elif),
  C('function', Id.KW_Function),
  C('time',     Id.KW_Time),

  # Oil integration
  C('var',      Id.KW_Var),
  C('setvar',   Id.KW_SetVar),
  C('set',      Id.KW_Set),
  C('func',     Id.KW_Func),
  C('proc',     Id.KW_Proc),
]

# These are treated like builtins in bash, but keywords in OSH.  However, we
# maintain compatibility with bash for the 'type' builtin.
_MORE_KEYWORDS = [
  C('break',    Id.ControlFlow_Break),
  C('continue', Id.ControlFlow_Continue),
  C('return',   Id.ControlFlow_Return),
  C('exit',     Id.ControlFlow_Exit),
]

# Used by oil_lang/grammar_gen.py too
EXPR_WORDS = [
  C('null', Id.Expr_Null),
  C('true', Id.Expr_True),
  C('false', Id.Expr_False),

  C('div', Id.Expr_Div),
  C('xor', Id.Expr_Xor),

  C('and', Id.Expr_And),
  C('or', Id.Expr_Or),
  C('not', Id.Expr_Not),

  C('for', Id.Expr_For),
  C('is', Id.Expr_Is),
  C('in', Id.Expr_In),
  C('if', Id.Expr_If),
  C('else', Id.Expr_Else),

  C('func', Id.Expr_Func),
]


# The 'compen' and 'type' builtins introspect on keywords and builtins.
OSH_KEYWORD_NAMES = [name for _, name, _ in _KEYWORDS]
OSH_KEYWORD_NAMES.append('{')  # not in our lexer list
OTHER_OSH_BUILTINS = [name for _, name, _ in _MORE_KEYWORDS]


def IsOtherBuiltin(name):
  # type: (str) -> bool
  return name in OTHER_OSH_BUILTINS


def IsKeyword(name):
  # type: (str) -> bool
  return name in OSH_KEYWORD_NAMES


# These two can must be recognized in the Outer state, but can't nested within
# [[.
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

  # For brace expansion {a,b}
  C('{', Id.Lit_LBrace),
  C('}', Id.Lit_RBrace),  # Also for var sub ${a}
  C(',', Id.Lit_Comma),

  C('=', Id.Lit_Equals),  # for x = 1+2*3

  # @array and @func(1, c)
  R('@' + VAR_NAME_RE, Id.Lit_Splice),  # for Oil splicing

  R(r'[0-9]*<', Id.Redir_Less),
  R(r'[0-9]*>', Id.Redir_Great),
  R(r'[0-9]*<<', Id.Redir_DLess),
  R(r'[0-9]*<<<', Id.Redir_TLess),
  R(r'[0-9]*>>', Id.Redir_DGreat),
  R(r'[0-9]*<<-', Id.Redir_DLessDash),
  R(r'[0-9]*>&', Id.Redir_GreatAnd),
  R(r'[0-9]*<&', Id.Redir_LessAnd),
  R(r'[0-9]*<>', Id.Redir_LessGreat),
  R(r'[0-9]*>\|', Id.Redir_Clobber),

  # No leading descriptor (2 is implied)
  C(r'&>', Id.Redir_AndGreat),
  C(r'&>>', Id.Redir_AndDGreat),

] + _KEYWORDS + _MORE_KEYWORDS + _UNQUOTED + _EXTGLOB_BEGIN

# Preprocessing before Outer
LEXER_DEF[lex_mode_e.Backtick] = [
  C(r'`', Id.Backtick_Right),
  # A backslash, and then one of the SAME FOUR escaped chars in the DQ mode.
  R(r'\\[$`"\\]', Id.Backtick_Quoted),
  R(r'[^`\\\0]+', Id.Backtick_Other),  # contiguous run of literals
  R(r'[^\0]', Id.Backtick_Other),  # anything else
]

# DBRACKET: can be like Outer, except:
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
# From code: ( | ) are treated special.

LEXER_DEF[lex_mode_e.BashRegex] = _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: bash accounts for spaces and non-word punctuation like ; inside ()
  # and [].  We will avoid that and ask the user to extract a variable?

  R(r'[a-zA-Z0-9_/-]+', Id.Lit_Chars),  # not including period
  _SIGNIFICANT_SPACE,

  # Normally, \x evalutes to x.  But quoted regex metacharacters like \* should
  # evaluate to \*.  Compare with ( | ).
  R(r'\\[*+?.^$\[\]]', Id.Lit_RegexMeta),

  # Everything else is an escape.
  R(r'\\[^\n\0]', Id.Lit_EscapedChar),
  C('\\\n', Id.Ignored_LineCont),

  # NOTE: ( | and ) aren't operators!
  R(r'[^\0]', Id.Lit_Other),  # everything else is literal
]

LEXER_DEF[lex_mode_e.DQ] = [
  # Only 4 characters are backslash escaped inside "".
  # https://www.gnu.org/software/bash/manual/bash.html#Double-Quotes
  R(r'\\[$`"\\]', Id.Lit_EscapedChar),
  C('\\\n', Id.Ignored_LineCont),
] + _LEFT_SUBS + _VARS + [
  R(r'[^$`"\0\\]+', Id.Lit_Chars),  # matches a line at most
  # NOTE: When parsing here doc line, this token doesn't end it.
  C('"', Id.Right_DoubleQuote),
  R(r'[^\0]', Id.Lit_Other),  # e.g. "$"
]

_VS_ARG_COMMON = _BACKSLASH + [
  C('/', Id.Lit_Slash),  # for patsub (not Id.VOp2_Slash)
  C('#', Id.Lit_Pound),  # for patsub prefix (not Id.VOp1_Pound)
  C('%', Id.Lit_Percent),  # for patsdub suffix (not Id.VOp1_Percent)
  C('}', Id.Right_DollarBrace),  # For var sub "${a}"
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VSub_ArgUnquoted] = \
  _VS_ARG_COMMON + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: added < and > so it doesn't eat <()
  R(r'[^$`/}"\'\0\\#%<>]+', Id.Lit_Chars),
  R(r'[^\0]', Id.Lit_Other),  # e.g. "$", must be last
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VSub_ArgDQ] = _VS_ARG_COMMON + _LEFT_SUBS + _VARS + [
  R(r'[^$`/}"\0\\#%]+', Id.Lit_Chars),  # matches a line at most

  # Weird wart: even in double quoted state, double quotes are allowed
  C('"', Id.Left_DoubleQuote),

  # Another weird wart of bash/mksh: $'' is recognized but NOT ''!
  C("$'", Id.Left_SingleQuoteC),

  R(r'[^\0]', Id.Lit_Other),  # e.g. "$", must be last
]

# NOTE: Id.Ignored_LineCont is NOT supported in SQ state, as opposed to DQ
# state.
LEXER_DEF[lex_mode_e.SQ_Raw] = [
  R(r"[^'\0]+", Id.Lit_Chars),  # matches a line at most
  C("'", Id.Right_SingleQuote),
]

# Shared between echo -e and $''.
_C_STRING_COMMON = [

  # \x6 is valid in bash
  R(r'\\x[0-9a-fA-F]{1,2}', Id.Char_Hex),
  R(r'\\u[0-9a-fA-F]{1,4}', Id.Char_Unicode4),
  R(r'\\U[0-9a-fA-F]{1,8}', Id.Char_Unicode8),

  R(r'\\[0abeEfrtnv\\]', Id.Char_OneChar),

  # Backslash that ends a line.  Note '.' doesn't match a newline character.
  C('\\\n', Id.Char_Literals),

  # e.g. \A is not an escape, and \x doesn't match a hex escape.  We allow it,
  # but a lint tool could warn about it.
  C('\\', Id.Char_BadBackslash),
]

# Used by ECHO_LEXER in core/builtin.py.
ECHO_E_DEF = _C_STRING_COMMON + [
  # Note: tokens above \0377 can either be truncated or be flagged a syntax
  # error in strict mode.
  R(r'\\0[0-7]{1,3}', Id.Char_Octal4),

  C(r'\c', Id.Char_Stop),

  # e.g. 'foo', anything that's not a backslash escape
  R(r'[^\\\0]+', Id.Char_Literals),
]

OCTAL3_RE = r'\\[0-7]{1,3}'

# https://www.gnu.org/software/bash/manual/html_node/Controlling-the-PromptEvaluator.html#Controlling-the-PromptEvaluator
PS1_DEF = [
    R(OCTAL3_RE, Id.PS_Octal3),
    R(r'\\[adehHjlnrstT@AuvVwW!#$\\]', Id.PS_Subst),
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
  # Silly difference!  In echo -e, the syntax is \0377, but here it's $'\377',
  # with no leading 0.
  R(OCTAL3_RE, Id.Char_Octal3),

  # ' is escaped in $'' mode, but not echo -e.  Ditto fr ", not sure why.
  C(r"\'", Id.Char_OneChar),
  C(r'\"', Id.Char_OneChar),

  # e.g. 'foo', anything that's not a backslash escape.  Need to exclude ' as
  # well.
  R(r"[^\\'\0]+", Id.Char_Literals),

  C("'", Id.Right_SingleQuote),

  # Backslash that ends the file!  Caught by re2c exhaustiveness check.  Parser
  # will assert; should give a better syntax error.
  C('\\\0', Id.Unknown_Tok),
]

LEXER_DEF[lex_mode_e.PrintfOuter] = _C_STRING_COMMON + [
  R(OCTAL3_RE, Id.Char_Octal3),
  R(r"[^%\\\0]+", Id.Char_Literals),
  C('%%', Id.Format_EscapedPercent),
  C('%', Id.Format_Percent),
]

# Maybe: bash also supports %(strftime)T
LEXER_DEF[lex_mode_e.PrintfPercent] = [
  # Flags
  R('[-0 +#]', Id.Format_Flag),

  R('[1-9][0-9]*', Id.Format_Num),
  C('.', Id.Format_Dot),
  # We support dsq.  The others we parse to display an error message.
  R('[disqbcouxXeEfFgG]', Id.Format_Type),
  R(r'[^\0]', Id.Unknown_Tok),  # any otehr char
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

  C('}', Id.Right_DollarBrace),

  C('\\\n', Id.Ignored_LineCont),

  C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  R(r'[^\0]', Id.Unknown_Tok),  # any char except newline
]

LEXER_DEF[lex_mode_e.VSub_2] = \
    ID_SPEC.LexerPairs(Kind.VTest) + \
    ID_SPEC.LexerPairs(Kind.VOp0) + \
    ID_SPEC.LexerPairs(Kind.VOp1) + \
    ID_SPEC.LexerPairs(Kind.VOp2) + [
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

  # For negation.
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
# Oil lexing.  TODO: Move to a different file?
#


_OIL_KEYWORDS = [
  # Blocks
  C('const',     Id.KW_Const),
  C('set',       Id.KW_Set),
  C('var',       Id.KW_Var),

  # Blocks
  C('proc',      Id.KW_Proc),
  C('func',      Id.KW_Func),

  C('do',        Id.KW_Do),
  C('time',      Id.KW_Time),  # Or should this be time do ?

  # Loops
  C('for',       Id.KW_For),
  C('in',        Id.KW_In),
  C('while',     Id.KW_While),

  # Conditionals
  C('if',        Id.KW_If),
  C('else',      Id.KW_Else),
  C('elif',      Id.KW_Elif),  # Python and shell both use elif

  C('switch',    Id.KW_Switch),  # for C translation
  C('match',     Id.KW_Match),
  C('case',      Id.KW_Case),
  C('with',      Id.KW_With),
]

# Valid in lex_mode_e.{Command,Array,Expr,DQ_Oil}
_OIL_LEFT_SUBS = [
  C('$(', Id.Left_DollarParen),
  C('${', Id.Left_DollarBrace),
  C('$[', Id.Left_DollarBracket),
  C('$/', Id.Left_DollarSlash),
]

# Valid in lex_mode_e.{Command,Array,Expr}
# TODO:
# - raw strings with r' r"
# - multiline strings ''' """ r''' r"""
_OIL_LEFT_UNQUOTED = [
  C('"', Id.Left_DoubleQuote),

  # In expression mode, we add the r'' and c'' prefixes for '' and $''.
  C("'", Id.Left_SingleQuoteRaw),
  C("r'", Id.Left_SingleQuoteRaw),

  C("c'", Id.Left_SingleQuoteC),
  C("$'", Id.Left_SingleQuoteC),

  # Not valid in DQ_Oil
  C('@(', Id.Left_AtParen),  # Legacy shell arrays.
  C('@[', Id.Left_AtBracket),  # Oil arrays.  Not used yet.
]

# Newline is significant, but sometimes elided by expr_parse.py.
_EXPR_NEWLINE_COMMENT = [
  C('\n', Id.Op_Newline),
  R(r'#[^\n\0]*', Id.Ignored_Comment),
  R(r'[ \t\r]+', Id.Ignored_Space),
]


# Python 3 float literals:

# digitpart     ::=  digit (["_"] digit)*
# fraction      ::=  "." digitpart
# exponent      ::=  ("e" | "E") ["+" | "-"] digitpart
# pointfloat    ::=  [digitpart] fraction | digitpart "."
# exponentfloat ::=  (digitpart | pointfloat) exponent
# floatnumber   ::=  pointfloat | exponentfloat

# This is the same as far as I can tell?

# This is a hand-written re2c rule to "refine" the Id.Expr_Float token to 
# include undescores: 1_000.234_567

LEXER_REFINEMENTS = {
  (lex_mode_e.Expr, Id.Expr_Float): """
digit = [0-9]
digitpart = digit ("_"? digit)*
fraction = "." digitpart
exponent = ("e" | "E") ("+" | "-")? digitpart
float = digitpart fraction? exponent? | fraction exponent?
"""
}

# TODO: Should all of these be Kind.Op instead of Kind.Arith?  And Kind.Expr?

# NOTE: Borrowing tokens from Arith (i.e. $(( )) ), but not using LexerPairs().
LEXER_DEF[lex_mode_e.Expr] = \
    _OIL_LEFT_SUBS + _OIL_LEFT_UNQUOTED + EXPR_WORDS + [

  # https://docs.python.org/3/reference/lexical_analysis.html#literals
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

  # Python allows 0 to be written 00 or 0_0_0, which is weird.
  C('0', Id.Expr_DecInt),
  R(r'[1-9](_?[0-9])*', Id.Expr_DecInt),

  R(r'0[bB](_?[01])+', Id.Expr_BinInt),
  R(r'0[oO](_?[0-7])+', Id.Expr_OctInt),
  R(r'0[xX](_?[0-9a-fA-F])+', Id.Expr_HexInt),

  # !!! This is REFINED by a hand-written re2c rule !!!
  # The dev build is slightly different than the production build.
  R(r'[0-9]+(\.[0-9]*)?([eE][+\-]?[0-9]+)?', Id.Expr_Float),

  # These can be looked up as keywords separately, so you enforce that they have
  # space around them?
  R(VAR_NAME_RE, Id.Expr_Name),
  # keywords:
  # div xor      # binary
  # and or not   # boolean
  # for          # comprehensions
  # is
  # in
  # if     # ternary
  # match  # consistent with if/else expressions
  # func   # literals

  C(',', Id.Arith_Comma),
  C(':', Id.Arith_Colon),   # for slicing a[1:2]

  C('?', Id.Arith_QMark),   # regex postfix

  C('+', Id.Arith_Plus),    # arith infix, regex postfix
  C('-', Id.Arith_Minus),   # arith infix, regex postfix
  C('*', Id.Arith_Star),
  C('^', Id.Arith_Caret),   # ^ rather than ** is exponentiation.  xor is 'xor'.
  C('/', Id.Arith_Slash),
  C('%', Id.Arith_Percent),

  C('.', Id.Expr_Dot),      # attribute access (static or dynamic)
  C('::', Id.Expr_DColon),  # static namespace access
  C('->', Id.Expr_RArrow),  # dynamic dict access: be d->name->age
                            # instead of d['name']['age']
  C('=>', Id.Expr_RDArrow), # for df => filter(age > 10)
                            # and match (x) { 1 => "one" }
                            # note: other languages use |>
                            # R/dplyr uses %>%

  # Terminator
  C(';', Id.Op_Semi),
  C('(', Id.Op_LParen),
  C(')', Id.Op_RParen),
  # NOTE: type expressions are expressions, e.g. Dict[Str, Int]
  C('[', Id.Op_LBracket),
  C(']', Id.Op_RBracket),
  C('{', Id.Op_LBrace),
  C('}', Id.Op_RBrace),

  C('<', Id.Arith_Less),
  C('>', Id.Arith_Great),
  C('<=', Id.Arith_LessEqual),
  C('>=', Id.Arith_GreatEqual),
  C('==', Id.Arith_DEqual),
  C('!=', Id.Arith_NEqual),

  # Bitwise operators
  C('&', Id.Arith_Amp),
  C('|', Id.Arith_Pipe),
  C('>>', Id.Arith_DGreat),
  C('<<', Id.Arith_DLess),  # Doesn't Java also have <<< ?

  # Bitwise complement, as well as infix pattern matching
  C('~', Id.Arith_Tilde),
  C('!~', Id.Expr_NotTilde),

  # Splat operators
  C('@', Id.Expr_At),
  C('@@', Id.Expr_DoubleAt),

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

  C('&=', Id.Arith_AmpEqual),
  C('|=', Id.Arith_PipeEqual),
  C('^=', Id.Arith_CaretEqual),  # Exponentiation

  C('>>=', Id.Arith_DGreatEqual),
  C('<<=', Id.Arith_DLessEqual),


  # NOTE: % could be string interpolation with a context other than locals?
  # like '$foo $bar' % {foo: 'X', bar: 'Y'}
  # single quoted rather than double quoted?
  # Would that be a security issue?

  # expr as List[Int] for casting?  Or just cast(List[Int]], expr)
  # What about specifying types?  NOTE: we attach it to the expression rather
  # than the type.
  # x = [] : Array<Int>
  #
  # inc = |x| x+1 for simple lambdas.
] + _EXPR_NEWLINE_COMMENT + _EXPR_ARITH_SHARED


# Differences from expression mode:
# - no nested regexes
# - only a limited set of operators
# - character classes are valid

# TODO: Do we allow $name $() ${} $[] in regexes?  I don't think they're really
# necessary.
LEXER_DEF[lex_mode_e.Regex] = _OIL_LEFT_UNQUOTED + [
  # These can be looked up as keywords separately, so you enforce that they have
  # space around them?
  R(VAR_NAME_RE, Id.Expr_Name),
  # keywords:
  # div xor      # binary
  # and or not   # boolean
  # for          # comprehensions
  # is
  # in
  # if     # ternary
  # match  # consistent with if/else expressions
  # func   # literals

  C('?', Id.Arith_QMark),   # optional

  C('+', Id.Arith_Plus),    # 1 or more
  C('*', Id.Arith_Star),    # 0 or more
  C('^', Id.Arith_Caret),   # x^{1,3}

  C('(', Id.Op_LParen),
  C(')', Id.Op_RParen),

  C('[', Id.Op_LBracket),
  C(']', Id.Op_RBracket),

  C('{', Id.Op_LBrace),
  C('}', Id.Op_RBrace),

  C('/', Id.Arith_Slash),  # Ends the regex.  TODO: Op_Slash?
] + _EXPR_NEWLINE_COMMENT + _EXPR_ARITH_SHARED

LEXER_DEF[lex_mode_e.CharClass] = [
  # placeholder.  Need a-z A-Z, NOT, \n, \x00, etc.
  R(_LITERAL_WHITELIST_REGEX, Id.Lit_Chars),

  _SIGNIFICANT_SPACE,
  # end char class
  C(']', Id.Op_RBracket),

  R(r'[^\]\0]', Id.Lit_Other),
]
