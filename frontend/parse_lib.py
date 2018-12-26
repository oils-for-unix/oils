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


class _CompletionState(object):
  """
  Output from the parser that helps us complete commands.
  """

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

  def __repr__(self):
    return '<_CompletionState %s %s>' % (self.words, self.tokens)


class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, aliases):
    self.arena = arena
    self.aliases = aliases
    # Completion state lives here since it may span multiple parsers.
    self.comp_state = _CompletionState()
    self.completing = False

  def _MakeLexer(self, line_reader, arena=None):
    """Helper function.

    TODO: should we combine the LineLexer and Lexer?  And the matcher?
    """
    line_lexer = lexer.LineLexer(match.MATCHER, '', arena=arena or self.arena)
    return lexer.Lexer(line_lexer, line_reader)

  def PrepareForCompletion(self):
    """Called every time we parse for completion."""
    self.completing = True
    # must be deleted or we will have words from the oshrc arena!
    del self.comp_state.words[:]
    # The other ones don't need to be reset?
    del self.comp_state.tokens[:]

  def SetLatestWords(self, words, redirects):
    """Called by the CommandParser every time we can a command."""
    if not self.completing:
      return False
    self.comp_state.words = words
    self.comp_state.redirects = redirects

  def AppendToken(self, token):
    """Called by the CommandParser every time we can a command."""
    if not self.completing:
      return False
    self.comp_state.tokens.append(token)

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
  def MakeParserForCompletion(self, code_str, arena):
    """Parser for partial lines.

    NOTE: Uses its own arena!
    """
    # NOTE: We don't need to use a arena here?  Or we need a "scratch arena"
    # that doesn't interfere with the rest of the program.
    line_reader = reader.StringLineReader(code_str, arena)
    lx = self._MakeLexer(line_reader, arena=arena)
    lx.EmitCompDummy()  # A special token before EOF!
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, w_parser, lx, line_reader,
                                       arena=arena)
    return c_parser

  # Another parser instantiation:
  # - For Array Literal in word_parse.py WordParser:
  #   w_parser = WordParser(self.lexer, self.line_reader)
