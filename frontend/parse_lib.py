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

lex_mode_e = types_asdl.lex_mode_e


class _BaseCompletionTrail(object):

  def __init__(self):
    # word from a partially completed command.
    # Filled in by _ScanSimpleCommand in osh/cmd_parse.py.
    self.words = []
    self.redirects = []
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
    self.tokens = []

  def PrintDebugString(self, debug_f):
    from osh import ast_lib
    #debug_f.log('trail = %s', trail)
    debug_f.log('  words:')
    for w in self.words:
      ast_lib.PrettyPrint(w, f=debug_f)
    debug_f.log('')

    debug_f.log('  redirects:')
    for r in self.redirects:
      ast_lib.PrettyPrint(r, f=debug_f)
    debug_f.log('')

    debug_f.log('  tokens:')
    for p in self.tokens:
      ast_lib.PrettyPrint(p, f=debug_f)
    debug_f.log('')

  def __repr__(self):
    return '<CompletionTrail %s %s %s>' % (
        self.words, self.redirects, self.tokens)


class _NullCompletionTrail(_BaseCompletionTrail):
  """Used when we're not completing."""

  def Clear(self):
    pass

  def SetLatestWords(self, words, redirects):
    pass

  def AppendToken(self, token):
    pass


class CompletionTrail(_BaseCompletionTrail):
  """Info left by the parser to help us complete shell syntax and commands."""

  def Clear(self):
    del self.words[:]
    del self.redirects[:]
    # The other ones don't need to be reset?
    del self.tokens[:]

  def SetLatestWords(self, words, redirects):
    self.words = words
    self.redirects = redirects

  def AppendToken(self, token):
    self.tokens.append(token)


class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, aliases, trail=None):
    self.arena = arena
    self.aliases = aliases
    # Completion state lives here since it may span multiple parsers.
    self.trail = trail or _NullCompletionTrail()

  def _MakeLexer(self, line_reader, arena=None):
    """Helper function.

    TODO: should we combine the LineLexer and Lexer?  And the matcher?
    """
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena=arena or self.arena)
    return lexer.Lexer(line_lexer, line_reader)

  def MakeOshParser(self, line_reader):
    lx = self._MakeLexer(line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader)
    return w_parser, c_parser

  def MakeOilParser(self, line_reader):
    # Same lexer as Oil?  It just doesn't start in the OUTER state?
    lx = self._MakeLexer(line_reader)
    c_parser = oil_cmd_parse.OilParser(self, lx, line_reader)
    return c_parser

  def MakeWordParserForHereDoc(self, line_reader):
    lx = self._MakeLexer(line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def MakeArithParser(self, code_str, arena):
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
    """To parse command sub, we want a fresh word parser state.

    It's a new instance based on same lexer and arena.
    """
    w_parser = word_parse.WordParser(self, lexer, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lexer, line_reader,
                                       eof_id=eof_id)
    return c_parser

  def MakeWordParserForPlugin(self, code_str, arena):
    """FOr $PS1, etc.

    NOTE: Uses its own arena!  I think that does nothing though?
    """
    line_reader = reader.StringLineReader(code_str, arena)
    lx = self._MakeLexer(line_reader, arena=arena)
    return word_parse.WordParser(self, lx, line_reader)

  # NOTE: We could reuse w_parser with ResetInputObjects() each time.  That's
  # what the REPL does.
  def MakeParserForCompletion(self, code_str):
    """Parser for partial lines."""
    line_reader = reader.StringLineReader(code_str, self.arena)
    lx = self._MakeLexer(line_reader)
    lx.EmitCompDummy()  # A special token before EOF!
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader)
    return c_parser

  # Another parser instantiation:
  # - For Array Literal in word_parse.py WordParser:
  #   w_parser = WordParser(self.lexer, self.line_reader)
