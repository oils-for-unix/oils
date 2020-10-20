"""
qsn_native.py -- Depends on Oil's C code and generated code.

In contrast, qsn_/qsn.py is pure Python, and has a reference decoder
py_decode().
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.types_asdl import lex_mode_e, lex_mode_t
from core.pyerror import log

from typing import Tuple, TYPE_CHECKING
if TYPE_CHECKING:
  from frontend.lexer import Lexer


def decode(lexer):
  # type: (Lexer) -> Tuple[str, int]
  """Given a QSN literal in a string, return the corresponding byte string."""

  pos = 0
  while True:
    tok = lexer.Read(lex_mode_e.QSN)
    log('%r', tok.val)

    if tok.id == Id.Eof_Real:
      break

  return '', pos


