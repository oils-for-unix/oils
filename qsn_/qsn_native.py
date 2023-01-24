"""
qsn_native.py -- Depends on Oil's C code and generated code.

In contrast, qsn_/qsn.py is pure Python, and has a reference decoder
py_decode().
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import Token
from _devbuild.gen.types_asdl import lex_mode_e, lex_mode_t
from core.pyerror import log, p_die
from frontend import consts

from typing import Tuple, List, TYPE_CHECKING
if TYPE_CHECKING:
  from frontend.lexer import Lexer


def IsWhitespace(s):
  # type: (str) -> bool
  """Alternative to s.isspace() that doesn't have legacy \f \v codes.

  QSN is a "legacy-free" format.

  Also used by osh/word_compile.py.
  """
  for ch in s:
    if ch not in ' \n\r\t':
      return False
  return True


def Parse(lexer):
  # type: (Lexer) -> List[Token]
  """Given a QSN literal in a string, return the corresponding byte string.

  Grammar:
      qsn = SingleQuote Kind.Char* SingleQuote Whitespace? Eof_Real
  """
  tok = lexer.Read(lex_mode_e.QSN)
  # Caller ensures this.  It's really a left single quote.
  assert tok.id == Id.Right_SingleQuote

  result = []  # type: List[Token]
  while True:
    tok = lexer.Read(lex_mode_e.QSN)
    #log('tok = %s', tok)

    if tok.id == Id.Unknown_Tok:  # extra error
      p_die('Unexpected token in QSN string', tok)

    kind = consts.GetKind(tok.id)
    if kind != Kind.Char:
      break

    result.append(tok)

  if tok.id != Id.Right_SingleQuote:
    p_die('Expected closing single quote in QSN string', tok)

  # HACK: read in shell's SQ_C mode to get whitespace, which is disallowe
  # INSIDE QSN.  This gets Eof_Real too.
  tok = lexer.Read(lex_mode_e.SQ_C)

  # Doesn't work because we want to allow literal newlines / tabs
  if tok.id == Id.Char_Literals:
    if not IsWhitespace(tok.val):
      p_die("Unexpected data after closing quote", tok)
    tok = lexer.Read(lex_mode_e.QSN)

  if tok.id != Id.Eof_Real:
    p_die('Unexpected token after QSN string', tok)

  return result
