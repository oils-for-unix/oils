"""
lex.py -- Shell lexer.

It consists of a series of lexical modes, each with regex -> Id mappings.

TODO:
- \0 should be Id.Op_Newline or Id.WS_Newline.  And then the higher level Lexer
  should return the Id.Eof_Real token, as it does now.
"""

from core.id_kind import Id, Kind, ID_SPEC
from core import util
from core.lexer import C, R

import re

# Thirteen lexer modes for osh.
# Possible additional modes:
# - extended glob?
# - nested backticks: echo `echo \`echo foo\` bar`
LexMode = util.Enum('LexMode', """
NONE
COMMENT
OUTER
DBRACKET
SQ DQ DOLLAR_SQ
ARITH
VS_1 VS_2 VS_ARG_UNQ VS_ARG_DQ
BASH_REGEX
BASH_REGEX_CHARS
""".split())

# In oil, I hope to have these lexer modes:
# COMMAND
# EXPRESSION (takes place of ARITH, VS_UNQ_ARG, VS_DQ_ARG)
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

# Explicitly exclude newline, although '.' would work too
_BACKSLASH = [
  R(r'\\[^\n]', Id.Lit_EscapedChar),
  C('\\\n', Id.Ignored_LineCont),
]

_VAR_NAME_RE = r'[a-zA-Z_][a-zA-Z0-9_]*'

# Used by osh/cmd_parse.py to validate for loop name.  Note it must be
# anchored on the right.
VAR_NAME_RE = re.compile(_VAR_NAME_RE + '$')

# All Kind.VSub
_VARS = [
  # Unbraced variables
  R(r'\$' + _VAR_NAME_RE, Id.VSub_Name),
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

# Anything until the end of the line is a comment.
LEXER_DEF[LexMode.COMMENT] = [
  R(r'.*', Id.Ignored_Comment)  # does not match newline
]

_UNQUOTED = _BACKSLASH + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  R(r'[a-zA-Z0-9_/.-]+', Id.Lit_Chars),
  # e.g. beginning of NAME=val, which will always be longer than the above
  # Id.Lit_Chars.
  R(r'[a-zA-Z_][a-zA-Z0-9_]*\+?=', Id.Lit_VarLike),

  C('#', Id.Lit_Pound),  # For comments

  # Needs to be LONGER than any other
  #(_VAR_NAME_RE + r'\[', Id.Lit_Maybe_LHS_ARRAY),
  # Id.Lit_Maybe_LHS_ARRAY2
  #(r'\]\+?=', Id.Lit_Maybe_ARRAY_ASSIGN_RIGHT),

  # For brace expansion {a,b}
  C('{', Id.Lit_LBrace),
  C('}', Id.Lit_RBrace),  # Also for var sub ${a}
  C(',', Id.Lit_Comma),
  C('~', Id.Lit_Tilde),  # For tilde expansion

  R(r'[ \t\r]+', Id.WS_Space),

  C('\0', Id.Eof_Real),  # TODO: Remove?
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

  R(r'.', Id.Lit_Other),  # any other single char is a literal
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
LEXER_DEF[LexMode.OUTER] = [
  C('((', Id.Op_DLeftParen),  # not allowed within [[
] + _KEYWORDS + _MORE_KEYWORDS + _UNQUOTED

# DBRACKET: can be like OUTER, except:
# - Don't really need redirects either... Redir_Less could be Op_Less
# - Id.Op_DLeftParen can't be nested inside.
LEXER_DEF[LexMode.DBRACKET] = [
  C(']]', Id.Lit_DRightBracket),
  C('!', Id.KW_Bang),
] + ID_SPEC.LexerPairs(Kind.BoolUnary) + \
    ID_SPEC.LexerPairs(Kind.BoolBinary) + \
    _UNQUOTED

LEXER_DEF[LexMode.BASH_REGEX] = [
  # Match these literals first, and then the rest of the OUTER state I guess.
  # That's how bash works.
  #
  # At a minimum, you do need $ and ~ expansions to happen.  <>;& could have
  # been allowed unescaped too, but that's not what bash does.  The criteria
  # was whether they were "special" in both languages, which seems dubious.
  C('(', Id.Lit_Chars),
  C(')', Id.Lit_Chars),
  C('|', Id.Lit_Chars),
] + _UNQUOTED

LEXER_DEF[LexMode.DQ] = _BACKSLASH + _LEFT_SUBS + _VARS + [
  R(r'[^$`"\0\\]+', Id.Lit_Chars),  # matches a line at most
  # NOTE: When parsing here doc line, this token doesn't end it.
  C('"', Id.Right_DoubleQuote),
  C('\0', Id.Eof_Real),
  R(r'.', Id.Lit_Other),  # e.g. "$"
]

_VS_ARG_COMMON = _BACKSLASH + [
  C('/', Id.Lit_Slash),  # for patsub (not Id.VOp2_Slash)
  C('#', Id.Lit_Pound),  # for patsub prefix (not Id.VOp1_Pound)
  C('%', Id.Lit_Percent),  # for patsdub suffix (not Id.VOp1_Percent)
  C('}', Id.Right_VarSub),  # For var sub "${a}"
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[LexMode.VS_ARG_UNQ] = \
  _VS_ARG_COMMON + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  # NOTE: added < and > so it doesn't eat <()
  R(r'[^$`/}"\'\0\\#%<>]+', Id.Lit_Chars),
  C('\0', Id.Eof_Real),
  R(r'.', Id.Lit_Other),  # e.g. "$", must be last
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[LexMode.VS_ARG_DQ] = _VS_ARG_COMMON + _LEFT_SUBS + _VARS + [
  R(r'[^$`/}"\0\\#%]+', Id.Lit_Chars),  # matches a line at most
  # Weird wart: even in double quoted state, double quotes are allowed
  C('"', Id.Left_DoubleQuote),
  C('\0', Id.Eof_Real),
  R(r'.', Id.Lit_Other),  # e.g. "$", must be last
]

# NOTE: Id.Ignored_LineCont is NOT supported in SQ state, as opposed to DQ
# state.
LEXER_DEF[LexMode.SQ] = [
  R(r"[^']+", Id.Lit_Chars),  # matches a line at most
  C("'", Id.Right_SingleQuote),
  C('\0', Id.Eof_Real),
]

# NOTE: Id.Ignored_LineCont is also not supported here, even though the whole
# point of it is that supports other backslash escapes like \n!
LEXER_DEF[LexMode.DOLLAR_SQ] = [
  R(r"[^'\\]+", Id.Lit_Chars),
  R(r"\\.", Id.Lit_EscapedChar),
  C("'", Id.Right_SingleQuote),
  C('\0', Id.Eof_Real),
]

LEXER_DEF[LexMode.VS_1] = [
  R(_VAR_NAME_RE, Id.VSub_Name),
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

  C('\0', Id.Eof_Real),  # not used?
  C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  R(r'.', Id.Unknown_Tok),  # any char except newline
]

LEXER_DEF[LexMode.VS_2] = \
    ID_SPEC.LexerPairs(Kind.VTest) + \
    ID_SPEC.LexerPairs(Kind.VOp1) + \
    ID_SPEC.LexerPairs(Kind.VOp2) + [
  C('}', Id.Right_VarSub),

  C('\\\n', Id.Ignored_LineCont),
  C('\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  R(r'.', Id.Unknown_Tok),  # any char except newline
]

# https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html#Shell-Arithmetic
LEXER_DEF[LexMode.ARITH] = \
    _LEFT_SUBS + _VARS + _LEFT_UNQUOTED + [
  # newline is ignored space, unlike in OUTER
  R(r'[ \t\r\n]+', Id.Ignored_Space),

  # Examples of arith constants:
  #   64#azAZ
  #   0xabc 0xABC
  #   0123
  # A separate digits token makes this easier to parse STATICALLY.  But this
  # doesn't help with DYNAMIC parsing.
  R(_VAR_NAME_RE, Id.Lit_ArithVarLike),  # for variable names or 64#_
  R(r'[0-9]+', Id.Lit_Digits),
  C('@', Id.Lit_At),  # for 64#@ or ${a[@]}
  C('#', Id.Lit_Pound),  # for 64#a

# TODO: 64#@ interferes with VS_AT.  Hm.
] + ID_SPEC.LexerPairs(Kind.Arith) + [
  C('\\\n', Id.Ignored_LineCont),
  R(r'.', Id.Unknown_Tok)  # any char.  This should be a syntax error.
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
