#!/usr/bin/python
"""
lex.py -- Shell lexer.

It consists of a series of lexical modes, each with regex -> Id mappings.

TODO:
- \0 should be Id.Op_Newline or Id.WS_Newline.  And then the higher level Lexer
  should return the Id.Eof_Real token, as it does now.
"""

from core.tokens import Id, ID_SPEC
from core import util

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
_CHAR_ESCAPE = (r'\\[^\n]', Id.Lit_EscapedChar)

_VAR_NAME_RE = r'[a-zA-Z_][a-zA-Z0-9_]*'

# All Kind.VSub
_VARS = [
  # Unbraced variables
  (r'\$' + _VAR_NAME_RE, Id.VSub_Name),
  (r'\$[0-9]', Id.VSub_Number),
  (r'\$!', Id.VSub_Bang),
  (r'\$@', Id.VSub_At),
  (r'\$\#', Id.VSub_Pound),
  (r'\$\$', Id.VSub_Dollar),
  (r'\$&', Id.VSub_Amp),
  (r'\$\*', Id.VSub_Star),
  (r'\$\-', Id.VSub_Hyphen),
  (r'\$\?', Id.VSub_QMark),
]

# All Kind.Left
_LEFT_SUBS = [
  (r'`', Id.Left_Backtick),
  (r'\$\(', Id.Left_CommandSub),
  (r'\$\{', Id.Left_VarSub),
  (r'\$\(\(', Id.Left_ArithSub),
  (r'\$\[', Id.Left_ArithSub2),
]

# All Kind.Left
_LEFT_UNQUOTED = [
  (r'"', Id.Left_DoubleQuote),
  (r'\'', Id.Left_SingleQuote),
  (r'\$"', Id.Left_DollarDoubleQuote),
  (r'\$\'', Id.Left_DollarSingleQuote),

  (r'<\(', Id.Left_ProcSubIn),
  (r'>\(', Id.Left_ProcSubOut),
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

LEXER_DEF = {}  # TODO: Could be a list too

# Anything until the end of the line is a comment.
LEXER_DEF[LexMode.COMMENT] = [
  (r'.*', Id.Ignored_Comment)  # does not match newline
]

_UNQUOTED = [
  (r'[a-zA-Z0-9_/.-]+', Id.Lit_Chars),

  # The other ones aren't MAYBE though... put them in a different category.
  # The whole category is
  # Id.Lit_Lhs
  # Id.Lit_Braceex
  # Id.Lit_Dbracket

  # Id.Lit_Maybe_LHS_VAR
  (r'[a-zA-Z_][a-zA-Z0-9_]*\+?=', Id.Lit_VarLike),  # might be NAME=val

  (r'#', Id.Lit_Pound),  # For comments

  # Needs to be LONGER than any other
  #(_VAR_NAME_RE + r'\[', Id.Lit_Maybe_LHS_ARRAY),
  # Id.Lit_Maybe_LHS_ARRAY2
  #(r'\]\+?=', Id.Lit_Maybe_ARRAY_ASSIGN_RIGHT),

  # For brace expansion {a,b}
  (r'\{', Id.Lit_LBrace),
  (r'\}', Id.Lit_RBrace),  # Also for var sub ${a}
  (r',', Id.Lit_Comma),

  # For tilde substitution
  (r'~', Id.Lit_Tilde),

  _CHAR_ESCAPE,
  (r'\\\n', Id.Ignored_LineCont),

  (r'[ \t\r]+', Id.WS_Space),

  (r'\0', Id.Eof_Real),  # TODO: Remove?

  (r'\n', Id.Op_Newline),

  (r'&', Id.Op_Amp),
  (r'\|', Id.Op_Pipe),
  (r'\|&', Id.Op_PipeAmp),
  (r'&&', Id.Op_DAmp),
  (r'\|\|', Id.Op_DPipe),
  (r';', Id.Op_Semi),
  (r';;', Id.Op_DSemi),

  (r'\(', Id.Op_LParen),
  (r'\)', Id.Op_RParen),

  (r'[0-9]*<', Id.Redir_Less),
  (r'[0-9]*>', Id.Redir_Great),
  (r'[0-9]*<<', Id.Redir_DLess),
  (r'[0-9]*<<<', Id.Redir_TLess),  # Does this need a descriptor?
  (r'[0-9]*>>', Id.Redir_DGreat),
  (r'[0-9]*<<-', Id.Redir_DLessDash),
  (r'[0-9]*>&', Id.Redir_GreatAnd),
  (r'[0-9]*<&', Id.Redir_LessAnd),
  (r'<>', Id.Redir_LessGreat),  # does it need a descriptor?
  (r'>\|', Id.Redir_Clobber),  # does it need a descriptor?
] + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  (r'.', Id.Lit_Other),  # any other single char is a literal
]

_KEYWORDS = [
  # NOTE: { is matched elsewhere
  (r'\[\[',     Id.KW_DLeftBracket),
  (r'!',        Id.KW_Bang),
  (r'for',      Id.KW_For),
  (r'while',    Id.KW_While),
  (r'until',    Id.KW_Until),
  (r'do',       Id.KW_Do),
  (r'done',     Id.KW_Done),
  (r'in',       Id.KW_In),
  (r'case',     Id.KW_Case),
  (r'esac',     Id.KW_Esac),
  (r'if',       Id.KW_If),
  (r'fi',       Id.KW_Fi),
  (r'then',     Id.KW_Then),
  (r'else',     Id.KW_Else),
  (r'elif',     Id.KW_Elif),
  (r'function', Id.KW_Function),

  (r'declare',  Id.Assign_Declare),
  (r'export',   Id.Assign_Export),
  (r'local',    Id.Assign_Local),
  (r'readonly', Id.Assign_Readonly),
]

# These two can must be recognized in the OUTER state, but can't nested within
# [[.
# Keywords have to be checked before _UNQUOTED so we get <KW_If "if"> instead
# of <Lit_Chars "if">.
LEXER_DEF[LexMode.OUTER] = [
  (r'\(\(', Id.Op_DLeftParen),  # TODO: Remove for DBracket?
] + _KEYWORDS + _UNQUOTED 


bool_lexer_pairs = ID_SPEC.BoolLexerPairs() 
assert len(bool_lexer_pairs) == 38, len(bool_lexer_pairs)

# \n isn't an operator inside [[ ]]; it's just ignored
LEXER_DEF[LexMode.DBRACKET] = [
  (r'\]\]', Id.KW_DRightBracket),
  (r'!', Id.KW_Bang),  # TODO: change to Lit_Bang?

] + bool_lexer_pairs + _UNQUOTED

# DBRACKET: can be like OUTER, except Id.Op_Newline is Id.WS_Newline
# Don't really need redirects either... it actually hurts things
# No Id.Op_DLeftParen -- DPAREN can't be nested inside.

LEXER_DEF[LexMode.BASH_REGEX] = [
  # Match these literals first, and then the rest of the OUTER state I guess.
  # That's how bash works.
  #
  # At a minimum, you do need $ and ~ expansions to happen.  <>;& could have
  # been allowed unescaped too, but that's not what bash does.  The criteria
  # was whether they were "special" in both languages, which seems dubious.
  (r'\(', Id.Lit_Chars),
  (r'\)', Id.Lit_Chars),
  (r'\|', Id.Lit_Chars),
] + _UNQUOTED

LEXER_DEF[LexMode.DQ] = [
  (r'[^$`"\0\\]+', Id.Lit_Chars),  # matches a line at most
  _CHAR_ESCAPE,
  (r'\\\n', Id.Ignored_LineCont),

  # NOTE: Doesn't change state when parsing here doc line
  (r'"', Id.Right_DoubleQuote),

] + _LEFT_SUBS + _VARS + [
  (r'\0', Id.Eof_Real),
  (r'.', Id.Lit_Other),  # e.g. "$"
]

_VAROP_Common = [
  _CHAR_ESCAPE,
  (r'\\\n', Id.Ignored_LineCont),
  (r'/', Id.Lit_Slash),  # for patsub (not Id.VOp2_Slash)
  (r'#', Id.Lit_Pound),  # for patsub prefix (not Id.VOp1_Pound)
  (r'%', Id.Lit_Percent),  # for patsdub suffix (not Id.VOp1_Percent)
  (r'\}', Id.Right_VarSub),  # For var sub "${a}"
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[LexMode.VS_ARG_UNQ] = [
  # NOTE: added < and > so it doesn't eat <()
  (r'[^$`/}"\0\\#%<>]+', Id.Lit_Chars),
] + _VAROP_Common + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  (r'\0', Id.Eof_Real),
  (r'.', Id.Lit_Other),  # e.g. "$", must be last
]

# Kind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[LexMode.VS_ARG_DQ] = [
  (r'[^$`/}"\0\\#%]+', Id.Lit_Chars),  # matches a line at most
  # Weird wart: even in double quoted state, double quotes are allowed
  (r'"', Id.Left_DoubleQuote),
] + _VAROP_Common + _LEFT_SUBS + _VARS + [
  (r'\0', Id.Eof_Real),
  (r'.', Id.Lit_Other),  # e.g. "$", must be last
]

# NOTE: Id.Ignored_LineCont is NOT supported in SQ state, as opposed to DQ
# state.
LEXER_DEF[LexMode.SQ] = [
  (r"[^']+", Id.Lit_Chars),  # matches a line at most
  (r"'", Id.Right_SingleQuote),
  (r'\0', Id.Eof_Real),
]

# NOTE: Id.Ignored_LineCont is also not supported here, even though the whole
# point of it is that supports other backslash escapes like \n!
LEXER_DEF[LexMode.DOLLAR_SQ] = [
  (r"[^'\\]+", Id.Lit_Chars),
  (r"\\.", Id.Lit_EscapedChar),
  (r"'", Id.Right_SingleQuote),
  (r'\0', Id.Eof_Real),
]

LEXER_DEF[LexMode.VS_1] = [
  (_VAR_NAME_RE, Id.VSub_Name),
  #  ${11} is valid, compared to $11 which is $1 and then literal 1.
  (r'[0-9]+', Id.VSub_Number),
  (r'!', Id.VSub_Bang),
  (r'@', Id.VSub_At),
  (r'#', Id.VSub_Pound),
  (r'\$', Id.VSub_Dollar),
  (r'&', Id.VSub_Amp),
  (r'\*', Id.VSub_Star),
  (r'\-', Id.VSub_Hyphen),
  (r'\?', Id.VSub_QMark),

  (r'\}', Id.Right_VarSub),

  (r'\\\n', Id.Ignored_LineCont),

  (r'\0', Id.Eof_Real),  # not used?
  (r'\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  (r'.', Id.Unknown_Tok),  # any char except newline
]

LEXER_DEF[LexMode.VS_2] = [
  (r':-',  Id.VTest_ColonHyphen),
  (r'-',   Id.VTest_Hyphen),
  (r':=',  Id.VTest_ColonEquals),
  (r'=',   Id.VTest_Equals),
  (r':\?', Id.VTest_ColonQMark),
  (r'\?',  Id.VTest_QMark),
  (r':\+', Id.VTest_ColonPlus),
  (r'\+',  Id.VTest_Plus),

  (r'%',  Id.VOp1_Percent),
  (r'%%', Id.VOp1_DPercent),
  (r'#',  Id.VOp1_Pound),
  (r'##', Id.VOp1_DPound),

  (r'\^',   Id.VOp1_Caret),
  (r'\^\^', Id.VOp1_DCaret),
  (r',',    Id.VOp1_Comma),
  (r',,',   Id.VOp1_DComma),

  (r'/', Id.VOp2_Slash),
  (r':', Id.VOp2_Colon),  # slicing

  (r'\[', Id.VOp2_LBracket),
  (r'\]', Id.VOp2_RBracket),

  (r'\}', Id.Right_VarSub),

  (r'\\\n', Id.Ignored_LineCont),
  (r'\n', Id.Unknown_Tok),  # newline not allowed inside ${}
  (r'.', Id.Unknown_Tok),  # any char except newline
]

# https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html#Shell-Arithmetic
LEXER_DEF[LexMode.ARITH] = [
  # newline is ignored space, unlike in OUTER
  (r'[ \t\r\n]+', Id.Ignored_Space),

  # Examples of arith constants:
  #   64#azAZ
  #   0xabc 0xABC
  #   0123

  # A separate digits part makes this easier to parse STATICALLY.  But this
  # doesn't help with DYNAMIC parsing.
  (r'[a-zA-Z_@]+', Id.Lit_Chars),  # for 64#@ or 64@_
  (r'[0-9]+', Id.Lit_Digits),
  (r'#', Id.Lit_Pound),

  (r';', Id.Arith_Semi),  # for loop only
  (r',', Id.Arith_Comma),  # function call and C comma operator

  (r'\+', Id.Arith_Plus),  # unary or binary
  (r'\-', Id.Arith_Minus),  # unary or binary
  (r'\*', Id.Arith_Star),
  (r'/', Id.Arith_Slash),
  (r'%', Id.Arith_Percent),

  (r'\+\+', Id.Arith_DPlus),  # Pre and post increment
  (r'--', Id.Arith_DMinus),  # "
  (r'\*\*', Id.Arith_DStar),  # exponentiation

  (r'\(', Id.Arith_LParen),
  (r'\)', Id.Arith_RParen),

  (r'\[', Id.Arith_LBracket),
  (r'\]', Id.Arith_RBracket),

  (r'\}', Id.Arith_RBrace),  # for ending var sub

  # SPECIAL CASE for ${a[@]}.  The expression in the [] is either and
  # arithmetic expression or @ or *.  In the ArithParser, we disallow this
  # token everywhere.
  # Other tokens that serve double duty:
  # - AS_STAR for ${a[*]}
  # - AS_COLON for ${a : i>0 a : 1 : 0 }
  (r'@', Id.Arith_At),

  # Logical operators
  (r'\?', Id.Arith_QMark),  # ternary
  (r':', Id.Arith_Colon),  # ternary

  (r'<=', Id.Arith_LessEqual),
  (r'<', Id.Arith_Less),
  (r'>=', Id.Arith_GreatEqual),
  (r'>', Id.Arith_Great),
  (r'==', Id.Arith_DEqual),
  (r'!=', Id.Arith_NEqual),

  # Bitwise operators
  (r'>>', Id.Arith_DGreat),
  (r'<<', Id.Arith_DLess),
  (r'&', Id.Arith_Amp),
  (r'\|', Id.Arith_Pipe),
  (r'\^', Id.Arith_Caret),
  (r'~', Id.Arith_Tilde),  # bitwise negation

  (r'=', Id.Arith_Equal),
  (r'\+=', Id.Arith_PlusEqual),
  (r'-=', Id.Arith_MinusEqual),
  (r'\*=', Id.Arith_StarEqual),
  (r'/=', Id.Arith_SlashEqual),
  (r'%=', Id.Arith_PercentEqual),
  (r'>>=', Id.Arith_DGreatEqual),
  (r'<<=', Id.Arith_DLessEqual),
  (r'&=', Id.Arith_AmpEqual),
  (r'\|=', Id.Arith_PipeEqual),
  (r'\^=', Id.Arith_CaretEqual),

  (r'&&', Id.Arith_DAmp),
  (r'\|\|', Id.Arith_DPipe),
  (r'!', Id.Arith_Bang),  # logical negation

  # NOTE: Tested all left-unquoted in both quoted and unquoted contexts.  e.g.
  # "$(( ${as[$'hi\n']} ))" works, as well as unquoted $(( ${as[$'hi\n']} ))
  # works

] + _LEFT_SUBS + _VARS + _LEFT_UNQUOTED + [

  (r'\\\n', Id.Ignored_LineCont),
  (r'.', Id.Unknown_Tok),  # any char.  This should be a syntax error.
]

# Notes on BASH_REGEX states
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
