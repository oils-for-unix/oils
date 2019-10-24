"""
meta.py

This file is used only at build time.

TODO:
- Consolidate ID_SPEC in core/id_kind_gen.py, and this one, which is used only
  by frontend/lex.py.
- Move the REDIR tables somewhere else.  They depend on Id.
"""

from pgen2 import grammar

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from core.pyutil import _ResourceLoader


def LoadOilGrammar(loader):
  # type: (_ResourceLoader) -> grammar.Grammar
  oil_grammar = grammar.Grammar()
  f = loader.open('_devbuild/gen/grammar.marshal')
  contents = f.read()
  f.close()
  oil_grammar.loads(contents)
  return oil_grammar
