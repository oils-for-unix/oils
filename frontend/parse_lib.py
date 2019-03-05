"""
parse_lib.py - Consolidate various parser instantiations here.
"""

from core.meta import types_asdl

from frontend import lexer
from frontend import reader
from frontend import tdop
from frontend import match

from osh import arith_parse
from osh import cmd_parse
from osh import word_parse

from oil_lang import cmd_parse as oil_cmd_parse

from core.alloc import Arena
from frontend.lexer import Lexer
from frontend.reader import _Reader
from frontend.tdop import TdopParser
from osh.word_parse import WordParser
from osh.cmd_parse import CommandParser
from _devbuild.gen.id_kind_asdl import Id_t
from _devbuild.gen.syntax_asdl import (
    token, word_t, redir_t, word__CompoundWord
)
from typing import List, Tuple, Dict, Optional

lex_mode_e = types_asdl.lex_mode_e


class _BaseTrail(object):

  def __init__(self):
    # type: () -> None
    # word from a partially completed command.
    # Filled in by _ScanSimpleCommand in osh/cmd_parse.py.
    self.words = []  # type: List[word__CompoundWord]
    self.redirects = []  # type: List[redir_t]
    # TODO: We should maintain the LST invariant and have a single list, but
    # that I ran into the "cases classes are better than variants" problem.

    # Non-ignored tokens, after PushHint translation.  Used for variable name
    # completion.  Filled in by _Peek() in osh/word_parse.py.
    #
    # Example:
    # $ echo $\
    # f<TAB>   
    # This could complete $foo.
    # Problem: readline doesn't even allow that, because it spans more than one
    # line!
    self.tokens = []  # type: List[token]

    self.alias_words = []  # type: List[word__CompoundWord]  # words INSIDE an alias expansion
    self.expanding_alias = False

  def Clear(self):
    pass

  def SetLatestWords(self, words, redirects):
    # type: (List[word__CompoundWord], List) -> None
    pass

  def AppendToken(self, token):
    # type: (token) -> None
    pass

  def BeginAliasExpansion(self):
    pass

  def EndAliasExpansion(self):
    pass

  def PrintDebugString(self, debug_f):
    debug_f.log('  words:')
    for w in self.words:
      w.PrettyPrint(f=debug_f)
    debug_f.log('')

    debug_f.log('  redirects:')
    for r in self.redirects:
      r.PrettyPrint(f=debug_f)
    debug_f.log('')

    debug_f.log('  tokens:')
    for p in self.tokens:
      p.PrettyPrint(f=debug_f)
    debug_f.log('')

    debug_f.log('  alias_words:')
    for w in self.alias_words:
      w.PrettyPrint(f=debug_f)
    debug_f.log('')

  def __repr__(self):
    return '<Trail %s %s %s %s>' % (
        self.words, self.redirects, self.tokens, self.alias_words)


class _NullTrail(_BaseTrail):
  """Used when we're not completing."""
  pass


class Trail(_BaseTrail):
  """Info left by the parser to help us complete shell syntax and commands.

  It's also used for history expansion.
  """
  def Clear(self):
    # type: () -> None
    del self.words[:]
    del self.redirects[:]
    # The other ones don't need to be reset?
    del self.tokens[:]
    del self.alias_words[:]

  def SetLatestWords(self, words, redirects):
    # type: (List[word__CompoundWord], List) -> None
    if self.expanding_alias:
      self.alias_words = words  # Save these separately
      return
    self.words = words
    self.redirects = redirects

  def AppendToken(self, token):
    # type: (token) -> None
    if self.expanding_alias:  # We don't want tokens inside aliases
      return
    self.tokens.append(token)

  def BeginAliasExpansion(self):
    # type: () -> None
    """Called by CommandParser so we know to be ready for FIRST alias word.

    For example, for

    alias ll='ls -l'

    Then we want to capture 'ls' as the first word.

    We do NOT want SetLatestWords or AppendToken to be active, because we don't
    need other tokens from 'ls -l'.
    
    It would also probably cause bugs in history expansion, e.g. echo !1 should
    be the first word the user typed, not the first word after alias expansion.
    """
    self.expanding_alias = True

  def EndAliasExpansion(self):
    # type: () -> None
    """Go back to the normal trail collection mode."""
    self.expanding_alias = False


class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, aliases, trail=None, one_pass_parse=False):
    # type: (Arena, Dict, Optional[_BaseTrail], bool) -> None
    self.arena = arena
    self.aliases = aliases
    # Completion state lives here since it may span multiple parsers.
    self.trail = trail or _NullTrail()
    self.one_pass_parse = one_pass_parse

  def _MakeLexer(self, line_reader, arena=None):
    # type: (_Reader, Optional[Arena]) -> Lexer
    """Helper function.

    TODO: should we combine the LineLexer and Lexer?  And the matcher?
    """
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena=arena or self.arena)
    return lexer.Lexer(line_lexer, line_reader)

  def MakeOshParser(self, line_reader, emit_comp_dummy=False,
                    aliases_in_flight=None):
    # type: (_Reader, bool, Optional[List[Tuple[str, int]]]) -> CommandParser
    lx = self._MakeLexer(line_reader)
    if emit_comp_dummy:
      lx.EmitCompDummy()  # A special token before EOF!
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader,
                                       aliases_in_flight=aliases_in_flight)
    return c_parser

  def MakeOilParser(self, line_reader):
    # Same lexer as Oil?  It just doesn't start in the OUTER state?
    lx = self._MakeLexer(line_reader)
    c_parser = oil_cmd_parse.OilParser(self, lx, line_reader)
    return c_parser

  def MakeWordParserForHereDoc(self, line_reader):
    # type: (_Reader) -> WordParser
    lx = self._MakeLexer(line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def MakeArithParser(self, code_str, arena):
    # type: (str, Arena) -> TdopParser
    """Used for a[x+1]=foo in the CommandParser.

    NOTE: We add tokens to a different arena, so we don't mess up the
    invariants for translation.
    """
    line_reader = reader.StringLineReader(code_str, arena)
    lx = self._MakeLexer(line_reader, arena=arena)
    w_parser = word_parse.WordParser(self, lx, line_reader,
                                     lex_mode=lex_mode_e.Arith)
    a_parser = tdop.TdopParser(arith_parse.SPEC, w_parser)
    return a_parser

  def MakeParserForCommandSub(self, line_reader, lexer, eof_id):
    # type: (_Reader, Lexer, Id_t) -> CommandParser
    """To parse command sub, we want a fresh word parser state.

    It's a new instance based on same lexer and arena.
    """
    w_parser = word_parse.WordParser(self, lexer, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lexer, line_reader,
                                       eof_id=eof_id)
    return c_parser

  def MakeWordParserForPlugin(self, code_str, arena):
    # type: (str, Arena) -> WordParser
    """FOr $PS1, etc.

    NOTE: Uses its own arena!  I think that does nothing though?
    """
    line_reader = reader.StringLineReader(code_str, arena)
    lx = self._MakeLexer(line_reader, arena=arena)
    return word_parse.WordParser(self, lx, line_reader)

  # Another parser instantiation:
  # - For Array Literal in word_parse.py WordParser:
  #   w_parser = WordParser(self.lexer, self.line_reader)
