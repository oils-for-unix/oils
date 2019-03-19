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


# In oil, I hope to have these lexer modes:
# COMMAND
# EXPRESSION (takes place of ARITH, VS_ArgUnquoted, VS_ArgDQ)
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
  C(r'$RANDOM', Id.VSub_DollarSpecialName),
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
  R(r'~[a-zA-Z0-9_.-]*', Id.Lit_TildeLike),

  C('#', Id.Lit_Pound),  # For comments

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

# In Outer and DBracket states.
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
LEXER_DEF[lex_mode_e.Outer] = [
  # These four are not allowed within [[, so they are in Outer but not
  # _UNQUOTED.

  # e.g. beginning of NAME=val, which will always be longer than
  # _LITERAL_WHITELIST_REGEX.
  R(r'[a-zA-Z_][a-zA-Z0-9_]*\+?=', Id.Lit_VarLike),
  R(r'[a-zA-Z_][a-zA-Z0-9_]*\[', Id.Lit_ArrayLhsOpen),
  R(r'\]\+?=', Id.Lit_ArrayLhsClose),
  C('((', Id.Op_DLeftParen),
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
  C('!', Id.KW_Bang),
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
  R(r'[ \t\r]+', Id.WS_Space),

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
  C('}', Id.Right_VarSub),  # For var sub "${a}"
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VS_ArgUnquoted] = \
  _VS_ARG_COMMON + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: added < and > so it doesn't eat <()
  R(r'[^$`/}"\'\0\\#%<>]+', Id.Lit_Chars),
  R(r'[^\0]', Id.Lit_Other),  # e.g. "$", must be last
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[lex_mode_e.VS_ArgDQ] = _VS_ARG_COMMON + _LEFT_SUBS + _VARS + [
  R(r'[^$`/}"\0\\#%]+', Id.Lit_Chars),  # matches a line at most

  # Weird wart: even in double quoted state, double quotes are allowed
  C('"', Id.Left_DoubleQuote),

  # Another weird wart of bash/mksh: $'' is recognized but NOT ''!
  C("$'", Id.Left_DollarSingleQuote),

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
LEXER_DEF[lex_mode_e.DollarSQ] = _C_STRING_COMMON + [
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
    ID_SPEC.LexerPairs(Kind.VOp0) + \
    ID_SPEC.LexerPairs(Kind.VOp1) + \
    ID_SPEC.LexerPairs(Kind.VOp2) + [
  C('}', Id.Right_VarSub),

  C('\\\n', Id.Ignored_LineCont),
  C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  R(r'[^\0]', Id.Unknown_Tok),  # any char except newline
]

# https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html#Shell-Arithmetic
LEXER_DEF[lex_mode_e.Arith] = \
    _LEFT_SUBS + _VARS + _LEFT_UNQUOTED + [
  # newline is ignored space, unlike in Outer
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
  R(r'!\??[a-zA-Z_/.][0-9a-zA-Z_/.]+', Id.History_Search),

  # Single quoted, e.g. 'a' or $'\n'.  Terminated by another single quote or
  # end of string.
  R(r"'[^'\0]*'?", Id.History_Other),

  # Runs of chars that are definitely not special
  R(r"[^!\\'\0]+", Id.History_Other),
  # Escaped characters.  \! disables history
  R(r'\\[^\0]', Id.History_Other),
  # Other single chars, like a trailing \ or !
  R(r'[^\0]', Id.History_Other),
]


#
# Oil lexing.  TODO: Move to a different file?
#


_OIL_KEYWORDS = [
  # Blocks
  C('const',     Id.KW_Const),
  C('set',       Id.KW_Set),
  C('setglobal', Id.KW_SetGlobal),
  C('var',       Id.KW_Var),

  # Blocks
  C('proc',      Id.KW_Proc),
  C('func',      Id.KW_Func),

  C('do',        Id.KW_Do),
  C('fork',      Id.KW_Fork),
  C('shell',     Id.KW_Shell),
  C('time',      Id.KW_Time),  # Or should this be time do ?

  # Loops
  C('for',       Id.KW_For),
  C('in',        Id.KW_In),
  C('while',     Id.KW_While),

  # Connditionals
  C('if',        Id.KW_If),
  C('else',      Id.KW_Else),
  C('elif',      Id.KW_Elif),  # Python and shell both use elif

  C('match',     Id.KW_If),
  C('case',      Id.KW_Case),
  C('with',      Id.KW_With),
]

# Valid in double-quoted modes.
_OIL_LEFT_SUBS = [
  C('$(', Id.Left_ParenSub),
  C('${', Id.Left_BraceSub),
  C('$[', Id.Left_BracketSub),
]

# Valid in unquoted modes.
# TODO:
# - raw strings with r' r"
# - multiline strings ''' """ r''' r"""
_OIL_LEFT_UNQUOTED = [
  C('"', Id.Left_DoubleQuote),
  C("'", Id.Left_SingleQuote),
]

_OIL_VARS = [
  # Unbraced variables
  R(r'\$' + VAR_NAME_RE, Id.VSub_DollarName),
  R(r'\$[0-9]', Id.VSub_Number),
]

LEXER_DEF[lex_mode_e.OilOuter] = (
    _OIL_KEYWORDS + _BACKSLASH + _OIL_LEFT_SUBS + _OIL_LEFT_UNQUOTED + 
    _OIL_VARS + [

  R(_LITERAL_WHITELIST_REGEX, Id.Lit_Chars),

  C('#', Id.Lit_Pound),  # For comments
  R(r'[ \t\r]+', Id.WS_Space),
  C('\n', Id.Op_Newline),

  # TODO:
  # - Recognize glob chars like *.py here?  What about '?' ?
  # - Need % to start "words" mode?

  # File descriptor?  Or is that parsed like $foo?  &1 and &stderr?
  R('&[0-9]', Id.Fd_Number),
  R('&' + VAR_NAME_RE, Id.Fd_Name),

  # Unused now?  But we don't want them to be literals.
  C('(', Id.Op_LParen),
  C(')', Id.Op_RParen),
  # for proc args?  Otherwise unused?
  C('[', Id.Op_LBracket),
  C(']', Id.Op_RBracket),
  # For blocks
  C('{', Id.Op_LBrace),
  C('}', Id.Op_RBrace),

  C('!', Id.Op_Bang),
  C('|', Id.Op_Pipe),
  C('&&', Id.Op_DAmp),
  C('||', Id.Op_DPipe),
  C(';', Id.Op_Semi),

  C('<', Id.Redir_Less),
  C('>', Id.Redir_Great),
  C('>+', Id.Redir_GreatPlus),  # Append

  C('<<', Id.Redir_DLess),
  C('>>', Id.Redir_DGreat),
  C('>>+', Id.Redir_DGreatPlus),

  R(r'[^\0]', Id.Lit_Other),  # any other single char is a literal
])
