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
least in lex_mode.OUTER.

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

from osh.meta import types, Id, Kind, ID_SPEC
from core.lexer import C, R

lex_mode_e = types.lex_mode_e


# In oil, I hope to have these lexer modes:
# COMMAND
# EXPRESSION (takes place of ARITH, VS_ARG_UNQ, VS_ARG_DQ)
# SQ  RAW_SQ  DQ  RAW_DQ
# VS    -- a single state here?  Or switches into expression state, because }
#          is an operator
# Problem: DICT_KEY might be a different state, to accept either a bare word
# foo, or an expression (X=a+2), which is allowed in shell.  Python doesn't
# allowed unquoted words, but we want to.

# TODO: There are 4 shared groups here.  I think you should test if that
# structure should be preserved through re2c.  Do a benchmark.
#
# If a group has no matches, then return Id.Unknown_Tok?  And then you can
# chain the groups in order.  It might make sense to experiment with the order
# too.

_BACKSLASH = [
  R(r'\\[^\n\0]', Id.Lit_EscapedChar),
  C('\\\n', Id.Ignored_LineCont),
]

VAR_NAME_RE = r'[a-zA-Z_][a-zA-Z0-9_]*'

# All Kind.VSub
_VARS = [
  # Unbraced variables
  R(r'\$' + VAR_NAME_RE, Id.VSub_Name),
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
  C('$(', Id.Left_CommandSub),
  C('${', Id.Left_VarSub),
  C('$((', Id.Left_ArithSub),
  C('$[', Id.Left_ArithSub2),
]

# Additional Kind.Left that are valid in unquoted modes.
_LEFT_UNQUOTED = [
  C('"', Id.Left_DoubleQuote),
  C("'", Id.Left_SingleQuote),
  C('$"', Id.Left_DollarDoubleQuote),
  C("$'", Id.Left_DollarSingleQuote),

  C('<(', Id.Left_ProcSubIn),
  C('>(', Id.Left_ProcSubOut),
]

# Constructs used:
# Character classes [] with simple ranges and negation, +, *, \n, \0
# It would be nice to express this as CRE ... ?  And then compile to re2c
# syntax.  And Python syntax.

# NOTE: Should remain compatible with re2c syntax, for code gen.
# http://re2c.org/manual/syntax/syntax.html

# PROBLEM: \0 in Python re vs \000 in re2?  Can this be unified?
# Yes, Python allows \000 octal escapes.
#
# https://docs.python.org/2/library/re.html

LEXER_DEF = {}  # TODO: Should be a list so we enforce order.

# Anything until the end of the line is a comment.  Does not match the newline
# itself.  We want to switch modes and possibly process Op_Newline for here
# docs, etc.
LEXER_DEF[lex_mode_e.COMMENT] = [
  R(r'[^\n\0]*', Id.Ignored_Comment)
]

_UNQUOTED = _BACKSLASH + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: We could add anything 128 and above to this character class?  So
  # utf-8 characters don't get split?
  R(r'[a-zA-Z0-9_/.-]+', Id.Lit_Chars),

  # For tilde expansion. The list of chars is Lit_Chars, but WITHOUT the /.  We
  # want the next token after the tilde TildeLike token start with a /.
  R(r'~[a-zA-Z0-9_.-]*', Id.Lit_TildeLike),

  C('#', Id.Lit_Pound),  # For comments

  # Needs to be LONGER than any other
  #(VAR_NAME_RE + r'\[', Id.Lit_Maybe_LHS_ARRAY),
  # Id.Lit_Maybe_LHS_ARRAY2
  #(r'\]\+?=', Id.Lit_Maybe_ARRAY_ASSIGN_RIGHT),

  # For brace expansion {a,b}
  C('{', Id.Lit_LBrace),
  C('}', Id.Lit_RBrace),  # Also for var sub ${a}
  C(',', Id.Lit_Comma),

  R(r'[ \t\r]+', Id.WS_Space),

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
  R(r'[0-9]*&>', Id.Redir_AndGreat),
  R(r'[0-9]*&>>', Id.Redir_AndDGreat),

  R(r'[^\0]', Id.Lit_Other),  # any other single char is a literal
]

# In OUTER and DBRACKET states.
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
]

# These are treated like builtins in bash, but keywords in OSH.  However, we
# main compatibility with bash for the 'type' builtin.
_MORE_KEYWORDS = [
  C('declare',  Id.Assign_Declare),
  C('typeset',  Id.Assign_Typeset),
  C('local',    Id.Assign_Local),
  C('readonly', Id.Assign_Readonly),

  C('break',    Id.ControlFlow_Break),
  C('continue', Id.ControlFlow_Continue),
  C('return',   Id.ControlFlow_Return),
  C('exit',     Id.ControlFlow_Exit),
]


_TYPE_KEYWORDS = set(name for _, name, _ in _KEYWORDS)
_TYPE_KEYWORDS.add('{')  # not in our lexer list
_TYPE_BUILTINS = set(name for _, name, _ in _MORE_KEYWORDS)


def IsOtherBuiltin(name):
  return name in _TYPE_BUILTINS


def IsKeyword(name):
  return name in _TYPE_KEYWORDS


# These two can must be recognized in the OUTER state, but can't nested within
# [[.
# Keywords have to be checked before _UNQUOTED so we get <KW_If "if"> instead
# of <Lit_Chars "if">.
LEXER_DEF[lex_mode_e.OUTER] = [
  # These four are not allowed within [[, so they are in OUTER but not
  # _UNQUOTED.

  # e.g. beginning of NAME=val, which will always be longer than the above
  # Id.Lit_Chars.
  R(r'[a-zA-Z_][a-zA-Z0-9_]*\+?=', Id.Lit_VarLike),
  R(r'[a-zA-Z_][a-zA-Z0-9_]*\[', Id.Lit_ArrayLhsOpen),
  R(r'\]\+?=', Id.Lit_ArrayLhsClose),
  C('((', Id.Op_DLeftParen),
] + _KEYWORDS + _MORE_KEYWORDS + _UNQUOTED + _EXTGLOB_BEGIN

# DBRACKET: can be like OUTER, except:
# - Don't really need redirects either... Redir_Less could be Op_Less
# - Id.Op_DLeftParen can't be nested inside.
LEXER_DEF[lex_mode_e.DBRACKET] = [
  C(']]', Id.Lit_DRightBracket),
  C('!', Id.KW_Bang),
] + ID_SPEC.LexerPairs(Kind.BoolUnary) + \
    ID_SPEC.LexerPairs(Kind.BoolBinary) + \
    _UNQUOTED + _EXTGLOB_BEGIN

# Inside an extended glob, most characters are literals, including spaces and
# punctuation.  We also accept \, $var, ${var}, "", etc.  They can also be
# nested, so _EXTGLOB_BEGIN appears here.
#
# Example: echo @(<> <>|&&|'foo'|$bar)
LEXER_DEF[lex_mode_e.EXTGLOB] = \
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

LEXER_DEF[lex_mode_e.BASH_REGEX] = _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: bash accounts for spaces and non-word punctuation like ; inside ()
  # and [].  We will avoid that and ask the user to extract a variable?

  R(r'[a-zA-Z0-9_/-]+', Id.Lit_Chars),  # not including period
  R(r'[ \t\r]+', Id.WS_Space),

  # From _BACKSLASH
  R(r'\\[^\n\0]', Id.Lit_EscapedChar),
  C('\\\n', Id.Ignored_LineCont),

  #C('{', Id.Lit_RegexMeta),    # { -> \{
  #C('}', Id.Lit_RegexMeta),    # } -> \}
  # In [[ foo =~ foo$ ]], the $ doesn't get escaped
  #C('$', Id.Lit_RegexMeta),

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
  C('}', Id.Right_VarSub),  # For var sub "${a}"
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VS_ARG_UNQ] = \
  _VS_ARG_COMMON + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: added < and > so it doesn't eat <()
  R(r'[^$`/}"\'\0\\#%<>]+', Id.Lit_Chars),
  R(r'[^\0]', Id.Lit_Other),  # e.g. "$", must be last
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VS_ARG_DQ] = _VS_ARG_COMMON + _LEFT_SUBS + _VARS + [
  R(r'[^$`/}"\0\\#%]+', Id.Lit_Chars),  # matches a line at most
  # Weird wart: even in double quoted state, double quotes are allowed
  C('"', Id.Left_DoubleQuote),
  R(r'[^\0]', Id.Lit_Other),  # e.g. "$", must be last
]

# NOTE: Id.Ignored_LineCont is NOT supported in SQ state, as opposed to DQ
# state.
LEXER_DEF[lex_mode_e.SQ] = [
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

# NOTE: Id.Ignored_LineCont is also not supported here, even though the whole
# point of it is that supports other backslash escapes like \n!  It just
# becomes a regular backslash.
LEXER_DEF[lex_mode_e.DOLLAR_SQ] = _C_STRING_COMMON + [
  # Silly difference!  In echo -e, the syntax is \0377, but here it's $'\377',
  # with no leading 0.
  R(r'\\[0-7]{1,3}', Id.Char_Octal3),

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

LEXER_DEF[lex_mode_e.VS_1] = [
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

  C('}', Id.Right_VarSub),

  C('\\\n', Id.Ignored_LineCont),

  C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  R(r'[^\0]', Id.Unknown_Tok),  # any char except newline
]

LEXER_DEF[lex_mode_e.VS_2] = \
    ID_SPEC.LexerPairs(Kind.VTest) + \
    ID_SPEC.LexerPairs(Kind.VOp1) + \
    ID_SPEC.LexerPairs(Kind.VOp2) + [
  C('}', Id.Right_VarSub),

  C('\\\n', Id.Ignored_LineCont),
  C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  R(r'[^\0]', Id.Unknown_Tok),  # any char except newline
]

# https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html#Shell-Arithmetic
LEXER_DEF[lex_mode_e.ARITH] = \
    _LEFT_SUBS + _VARS + _LEFT_UNQUOTED + [
  # newline is ignored space, unlike in OUTER
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
] + ID_SPEC.LexerPairs(Kind.Arith) + [
  C('\\\n', Id.Ignored_LineCont),
  R(r'[^\0]', Id.Unknown_Tok)  # any char.  This should be a syntax error.
]

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

  R(r'\\[^\0]', Id.Glob_EscapedChar),
  C('\\', Id.Glob_BadBackslash),  # Trailing single backslash

  # For efficiency, combine other characters into a single token,  e.g. 'py' in
  # '*.py' or 'alpha' in '[[:alpha:]]'.
  R(r'[a-zA-Z0-9_]+', Id.Glob_CleanLiterals),  # no regex escaping
  R(r'[^\0]', Id.Glob_OtherLiteral),  # anything else -- examine the char
]
