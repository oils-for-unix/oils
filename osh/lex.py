#!/usr/bin/python
"""
lex.py -- Shell lexer.

It consists of a series of lexical modes, each with regex -> Id mappings.

TODO:
- \0 should be OP_NEWLINE or WS_NEWLINE.  And then the higher level Lexer
  should return the Eof_REAL token, as it does now.
"""

from core.tokens import *

# In oil, I hope to have:
# COMMAND
# EXPRESSION (takes place of ARITH, VS_UNQ_ARG, VS_DQ_ARG)
# SQ  RAW_SQ  DQ  RAW_DQ
# VS    -- a single state here?  Or switches into expression state, because } is 
#       -- an operator
# Problem: DICT_KEY might be a different state, to accept either a bare word
# foo, or an expression (X=a+2), which is allowed in shell.  Python doesn't
# allowed unquoted words, but we want to.

# - BASH_REGEX -- compatibility mode, %parse-compat bash-regex

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

# TODO: There are 4 shared groups here.  I think you should test if that
# structure should be preserved through re2c.  Do a benchmark.
#
# If a group has no matches, then return UNKNOWN_TOK?  And then you can chain
# the groups in order.  It might make sense to experiment with the order too.

# Explicitly exclude newline, although '.' would work too
_CHAR_ESCAPE = (r'\\[^\n]', LIT_ESCAPED_CHAR)

_VAR_NAME_RE = r'[a-zA-Z_][a-zA-Z0-9_]*'

# All TokenKind.VS 
_VARS = [
  # Unbraced variables
  (r'\$' + _VAR_NAME_RE, VS_NAME),
  (r'\$[0-9]', VS_NUMBER),
  (r'\$!', VS_BANG),
  (r'\$@', VS_AT),
  (r'\$\#', VS_POUND),
  (r'\$\$', VS_DOLLAR),
  (r'\$&', VS_AMP),
  (r'\$\*', VS_STAR),
  (r'\$\-', VS_HYPHEN),
  (r'\$\?', VS_QMARK),
]

# All TokenKind.LEFT
_LEFT_SUBS = [
  (r'`', LEFT_BACKTICK),
  (r'\$\(', LEFT_COMMAND_SUB),
  (r'\$\{', LEFT_VAR_SUB),
  (r'\$\(\(', LEFT_ARITH_SUB),
  (r'\$\[', LEFT_ARITH_SUB2),
]

# All TokenKind.LEFT
_LEFT_UNQUOTED = [
  (r'"', LEFT_D_QUOTE),
  (r'\'', LEFT_S_QUOTE),
  (r'\$"', LEFT_DD_QUOTE),
  (r'\$\'', LEFT_DS_QUOTE),

  (r'<\(', LEFT_PROC_SUB_IN),
  (r'>\(', LEFT_PROC_SUB_OUT),
]

# Constructs used:
# character classes [] with simple ranges and negation, +, *, \n, \0
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
  (r'.*', IGNORED_COMMENT)  # does not match newline
]

_unquoted = [
  (r'[a-zA-Z0-9_/.-]+', LIT_CHARS),

  # The other ones aren't MAYBE though... put them in a different category.
  # The whole category is
  # LIT_LHS
  # LIT_BRACEEX
  # LIT_DBRACKET

  # LIT_MAYBE_LHS_VAR
  (r'[a-zA-Z_][a-zA-Z0-9_]*\+?=', LIT_VAR_LIKE),  # might be NAME=val

  (r'#', LIT_POUND),  # For comments

  # Needs to be LONGER than any other
  #(_VAR_NAME_RE + r'\[', LIT_MAYBE_LHS_ARRAY),
  # LIT_MAYBE_LHS_ARRAY2
  #(r'\]\+?=', LIT_MAYBE_ARRAY_ASSIGN_RIGHT),

  # For brace expansion {a,b} 
  (r'\{', LIT_LBRACE),
  (r'\}', LIT_RBRACE),  # Also for var sub ${a}
  (r',', LIT_COMMA),

  # For tilde substitution
  (r'~', LIT_TILDE),

  _CHAR_ESCAPE,
  (r'\\\n', IGNORED_LINE_CONT),

  (r'[ \t\r]+', WS_SPACE),

  (r'\0', Eof_REAL),  # TODO: Remove?

  (r'\n', OP_NEWLINE),

  (r'&', OP_AMP),
  (r'\|', OP_PIPE),
  (r'\|&', OP_PIPEAMP),
  (r'&&', OP_AND_IF),
  (r'\|\|', OP_OR_IF),
  (r';', OP_SEMI),
  (r';;', OP_DSEMI),

  (r'\(', OP_LPAREN),
  (r'\)', OP_RPAREN),

  (r'[0-9]*<', REDIR_LESS),
  (r'[0-9]*>', REDIR_GREAT),
  (r'[0-9]*<<', REDIR_DLESS),
  (r'[0-9]*<<<', REDIR_TLESS),  # Does this need a descriptor?
  (r'[0-9]*>>', REDIR_DGREAT),
  (r'[0-9]*<<-', REDIR_DLESSDASH),
  (r'[0-9]*>&', REDIR_GREATAND),
  (r'[0-9]*<&', REDIR_LESSAND),
  (r'<>', REDIR_LESSGREAT),  # does it need a descriptor?
  (r'>\|', REDIR_CLOBBER),  # does it need a descriptor?
] + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  (r'.', LIT_OTHER),  # any other single char is a literal
]

# These two can must be recognized in the _unquoted state, but can't nested a [[.
LEXER_DEF[LexMode.OUTER] = [
  (r'\[\[', LIT_LEFT_DBRACKET),  # this needs to be a single token
  (r'\(\(', OP_LEFT_DPAREN),  # TODO: Remove for DBracket?
] + _unquoted

# \n isn't an operator inside [[ ]]; it's just ignored
LEXER_DEF[LexMode.DBRACKET] = [

  (r'\]\]', LIT_RIGHT_DBRACKET),
  (r'=', LIT_EQUAL),
  (r'==', LIT_DEQUAL),
  (r'!=', LIT_NEQUAL),
  (r'=~', LIT_TEQUAL),
] + _unquoted

# DBRACKET: can be like OUTER, except OP_NEWLINE is WS_NEWLINE
# Don't really need redirects either... it actually hurts things
# No OP_LEFT_DPAREN -- DPAREN can't be nested inside.

LEXER_DEF[LexMode.BASH_REGEX] = [
  # Match these literals first, and then the rest of the OUTER state I guess.
  # That's how bash works.
  #
  # At a minimum, you do need $ and ~ expansions to happen.  <>;& could have
  # been allowed unescaped too, but that's not what bash does.  The criteria
  # was whether they were "special" in both languages, which seems dubious.
  (r'\(', LIT_CHARS),
  (r'\)', LIT_CHARS),
  (r'\|', LIT_CHARS),
] + _unquoted

LEXER_DEF[LexMode.DQ] = [
  (r'[^$`"\0\\]+', LIT_CHARS),  # matches a line at most
  _CHAR_ESCAPE,
  (r'\\\n', IGNORED_LINE_CONT),

  # NOTE: Doesn't change state when parsing here doc line
  (r'"', RIGHT_D_QUOTE),

] + _LEFT_SUBS + _VARS + [
  (r'\0', Eof_REAL),
  (r'.', LIT_OTHER),  # e.g. "$"
]

_VAROP_COMMON = [
  _CHAR_ESCAPE,
  (r'\\\n', IGNORED_LINE_CONT),
  (r'/', LIT_SLASH),  # for patsub (not VS_OP_SLASH)
  (r'#', LIT_POUND),  # for patsub prefix (not VS_UNARY_POUND)
  (r'%', LIT_PERCENT),  # for patsdub suffix (not VS_UNARY_PERCENT)
  (r'\}', RIGHT_VAR_SUB),  # For var sub "${a}"
]

# TokenKind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[LexMode.VS_ARG_UNQ] = [
  (r'[^$`/}"\0\\#%<>]+', LIT_CHARS),  # NOTE: added < and > so it doesn't eat <()
] + _VAROP_COMMON + _LEFT_SUBS + _LEFT_UNQUOTED + _VARS + [
  (r'\0', Eof_REAL),
  (r'.', LIT_OTHER),  # e.g. "$", must be last
]

# TokenKind.{LIT,IGNORED,VS,LEFT,RIGHT,Eof}
LEXER_DEF[LexMode.VS_ARG_DQ] = [
  (r'[^$`/}"\0\\#%]+', LIT_CHARS),  # matches a line at most
  # Weird wart: even in double quoted state, double quotes are allowed
  (r'"', LEFT_D_QUOTE),
] + _VAROP_COMMON + _LEFT_SUBS + _VARS + [
  (r'\0', Eof_REAL),
  (r'.', LIT_OTHER),  # e.g. "$", must be last
]

# NOTE: IGNORED_LINE_CONT is NOT supported in SQ state, as opposed to DQ state.
LEXER_DEF[LexMode.SQ] = [
  (r"[^']+", LIT_CHARS),  # matches a line at most
  (r"'", RIGHT_S_QUOTE),
  (r'\0', Eof_REAL),
]

# NOTE: IGNORED_LINE_CONT is also not supported here, even though the whole
# point of it is that supports other backslash escapes like \n!
LEXER_DEF[LexMode.DOLLAR_SQ] = [
  (r"[^'\\]+", LIT_CHARS),
  (r"\\.", LIT_ESCAPED_CHAR),
  (r"'", RIGHT_S_QUOTE),
  (r'\0', Eof_REAL),
]

LEXER_DEF[LexMode.VS_1] = [
  (_VAR_NAME_RE, VS_NAME),
  #  ${11} is valid, compared to $11 which is $1 and then literal 1.
  (r'[0-9]+', VS_NUMBER),
  (r'!', VS_BANG),
  (r'@', VS_AT),
  (r'#', VS_POUND),
  (r'\$', VS_DOLLAR),
  (r'&', VS_AMP),
  (r'\*', VS_STAR),
  (r'\-', VS_HYPHEN),
  (r'\?', VS_QMARK),

  (r'\}', RIGHT_VAR_SUB),

  (r'\\\n', IGNORED_LINE_CONT),

  (r'\0', Eof_REAL),  # not used?
  (r'\n', UNKNOWN_TOK),  # newline not allowed inside ${}
  (r'.', UNKNOWN_TOK),  # any char except newline
]

LEXER_DEF[LexMode.VS_2] = [
  (r':-',  VS_TEST_COLON_HYPHEN),
  (r'-',   VS_TEST_HYPHEN),
  (r':=',  VS_TEST_COLON_EQUALS),
  (r'=',   VS_TEST_EQUALS),
  (r':\?', VS_TEST_COLON_QMARK),
  (r'\?',  VS_TEST_QMARK),
  (r':\+', VS_TEST_COLON_PLUS),
  (r'\+',  VS_TEST_PLUS),

  (r'%',  VS_UNARY_PERCENT),
  (r'%%', VS_UNARY_DPERCENT),
  (r'#',  VS_UNARY_POUND),
  (r'##', VS_UNARY_DPOUND),

  (r'\^',   VS_UNARY_CARET),
  (r'\^\^', VS_UNARY_DCARET),
  (r',',    VS_UNARY_COMMA),
  (r',,',   VS_UNARY_DCOMMA),

  (r'/', VS_OP_SLASH),
  (r':', VS_OP_COLON),  # slicing

  (r'\[', VS_OP_LBRACKET),
  (r'\]', VS_OP_RBRACKET),

  (r'\}', RIGHT_VAR_SUB),

  (r'\\\n', IGNORED_LINE_CONT),
  (r'\n', UNKNOWN_TOK),  # newline not allowed inside ${}
  (r'.', UNKNOWN_TOK),  # any char except newline
]

# https://www.gnu.org/software/bash/manual/html_node/Shell-Arithmetic.html#Shell-Arithmetic
LEXER_DEF[LexMode.ARITH] = [
  (r'[ \t\r\n]+', IGNORED_SPACE),  # newline is ignored space, unlike in OUTER

  # Words allowed:
  # 64#azAZ
  # 0xabc 0xABC
  # 0123

  # A separate digits part makes this easier to parse STATICALLY.  But this
  # doesn't help with DYNAMIC parsing.
  (r'[a-zA-Z_@]+', LIT_CHARS),  # for 64#@ or 64@_
  (r'[0-9]+', LIT_DIGITS),
  (r'#', LIT_POUND),

  (r';', AS_OP_SEMI),  # for loop only
  (r',', AS_OP_COMMA),  # function call and C comma operator

  (r'\+', AS_OP_PLUS),  # unary or binary
  (r'\-', AS_OP_MINUS),  # unary or binary
  (r'\*', AS_OP_STAR),
  (r'/', AS_OP_SLASH),
  (r'%', AS_OP_PERCENT),

  (r'\+\+', AS_OP_DPLUS),  # Pre and post increment
  (r'--', AS_OP_DMINUS),  # "
  (r'\*\*', AS_OP_DSTAR),  # exponentiation

  (r'\(', AS_OP_LPAREN),
  (r'\)', AS_OP_RPAREN),

  (r'\[', AS_OP_LBRACKET),
  (r'\]', AS_OP_RBRACKET),

  (r'\}', AS_OP_RBRACE),  # for ending var sub

  # SPECIAL CASE for ${a[@]}.  The expression in the [] is either and
  # arithmetic expression or @ or *.  In the ArithParser, we disallow this
  # token everywhere.
  # Other tokens that serve double duty:
  # - AS_STAR for ${a[*]}
  # - AS_COLON for ${a : i>0 a : 1 : 0 }
  (r'@', AS_OP_AT),

  # Logical operators
  (r'\?', AS_OP_QMARK),  # ternary
  (r':', AS_OP_COLON),  # ternary

  (r'<=', AS_OP_LE),
  (r'<', AS_OP_LESS),
  (r'>=', AS_OP_GE),
  (r'>', AS_OP_GREAT),
  (r'==', AS_OP_DEQUAL),
  (r'!=', AS_OP_NEQUAL),

  # Bitwise operators
  (r'>>', AS_OP_DGREAT),
  (r'<<', AS_OP_DLESS),
  (r'&', AS_OP_AMP),
  (r'\|', AS_OP_PIPE),
  (r'\^', AS_OP_CARET),
  (r'~', AS_OP_TILDE),  # bitwise negation

  (r'=', AS_OP_EQUAL),
  (r'\+=', AS_OP_PLUS_EQUAL),
  (r'-=', AS_OP_MINUS_EQUAL),
  (r'\*=', AS_OP_STAR_EQUAL),
  (r'/=', AS_OP_SLASH_EQUAL),
  (r'%=', AS_OP_PERCENT_EQUAL),
  (r'>>=', AS_OP_DGREAT_EQUAL),
  (r'<<=', AS_OP_DLESS_EQUAL),
  (r'&=', AS_OP_AMP_EQUAL),
  (r'\|=', AS_OP_PIPE_EQUAL),
  (r'\^=', AS_OP_CARET_EQUAL),

  (r'&&', AS_OP_DAMP),
  (r'\|\|', AS_OP_DPIPE),
  (r'!', AS_OP_BANG),  # logical negation

# NOTE: Tested all left-unquoted in both quoted and unquoted contexts.  e.g.
# "$(( ${as[$'hi\n']} ))" works, as well as unquotedj
# $(( ${as[$'hi\n']} )) works

] + _LEFT_SUBS + _VARS + _LEFT_UNQUOTED + [

  (r'\\\n', IGNORED_LINE_CONT),
    # NOTE: This will give you VS_QMARK tokens, etc.
  (r'.', UNKNOWN_TOK),  # any char.  This should be a syntax error.
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
