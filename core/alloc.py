from _devbuild.gen.syntax_asdl import source_t, Token, SourceLine
from asdl import runtime
from mycpp.mylib import log

from typing import List, Dict, Any

_ = log


class ctx_SourceCode(object):

    def __init__(self, arena, src):
        # type: (Arena, source_t) -> None
        arena.PushSource(src)
        self.arena = arena

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.arena.PopSource()


class Arena(object):
    """Manages source_t, SourceLine, Token."""

    def __init__(self, save_tokens=False):
        # type: (bool) -> None

        self.save_tokens = save_tokens

        # indexed by span_id
        self.tokens = []  # type: List[Token]
        self.num_tokens = 0

        # Only used in tools
        self.span_id_lookup = {}  # type: Dict[Token, int]

        # All lines that haven't been discarded.  For LST formatting.
        self.lines_list = []  # type: List[SourceLine]

        # reuse these instances in many line_span instances
        self.source_instances = []  # type: List[source_t]

    def SaveTokens(self):
        # type: () -> None
        """
        Used by --tool X.  Do we need LosslessArena?
        """
        self.save_tokens = True

    def PushSource(self, src):
        # type: (source_t) -> None
        self.source_instances.append(src)

    def PopSource(self):
        # type: () -> None
        self.source_instances.pop()

    def AddLine(self, line, line_num):
        # type: (str, int) -> SourceLine
        """Save a physical line and return a line_id for later retrieval.

        The line number is 1-based.
        """
        src_line = SourceLine(line_num, line, self.source_instances[-1])
        self.lines_list.append(src_line)
        return src_line

    def DiscardLines(self):
        # type: () -> None
        """Remove references ot lines we've accumulated.

        - This makes the linear search in SnipCodeString() shorter.
        - It removes the ARENA's references to all lines.  The TOKENS still
          reference some lines.
        """
        #log("discarding %d lines", len(self.lines_list))
        del self.lines_list[:]

    def SnipCodeString(self, left, right, inclusive=True):
        # type: (Token, Token, bool) -> str
        """Return the code string between left and right tokens, INCLUSIVE.

        Used for ALIAS expansion, which happens in the PARSER.

        The argument to aliases can span multiple lines, like this:

        $ myalias '1     2     3'
        """
        if inclusive:
            ileft = left.col
            iright = right.col + right.length
        else:
            ileft = left.col + left.length
            iright = right.col

        pieces = []  # type: List[str]
        if not inclusive:
            pieces.append(' ' * ileft)

        if left.line == right.line:
            for li in self.lines_list:
                if li == left.line:
                    pieces.append(li.content[ileft:iright])
                    return ''.join(pieces)

        saving = False
        found_left = False
        found_right = False
        for li in self.lines_list:
            if li == left.line:
                found_left = True
                saving = True

                # Save everything after the left token
                piece = li.content[ileft:]
                pieces.append(piece)
                #log('   %r', piece)
                continue

            if li == right.line:
                found_right = True

                piece = li.content[:iright]
                pieces.append(piece)
                #log('   %r', piece)

                saving = False
                break

            if saving:
                pieces.append(li.content)
                #log('   %r', li.content)

        assert found_left, "Couldn't find left token"
        assert found_right, "Couldn't find right token"
        return ''.join(pieces)

    def NewToken(self, id_, col, length, src_line):
        # type: (int, int, int, SourceLine) -> Token

        tok = Token(id_, length, col, src_line, None)
        if self.save_tokens:
            span_id = self.num_tokens
            self.num_tokens += 1

            self.tokens.append(tok)
            self.span_id_lookup[tok] = span_id
        return tok

    def UnreadOne(self):
        # type: () -> None
        """Reuse the last span ID."""
        if self.save_tokens:
            self.tokens.pop()
            self.num_tokens -= 1

    def GetToken(self, span_id):
        # type: (int) -> Token
        assert span_id != runtime.NO_SPID, span_id
        assert span_id < len(self.tokens), \
          'Span ID out of range: %d is greater than %d' % (span_id, len(self.tokens))
        return self.tokens[span_id]

    def GetSpanId(self, tok):
        # type: (Token) -> int
        """Given a Token, returns its a sequence number"""
        #return tok.span_id
        #return -1
        assert tok in self.span_id_lookup
        return self.span_id_lookup[tok]

    def LastSpanId(self):
        # type: () -> int
        """Return one past the last span ID."""
        return len(self.tokens)


class LosslessArena(Arena):
    """
    TODO:

    Has lossless invariant, for
    --tool fmt
    --tool ysh-ify

    Retains all SourceLine and Token

    Somehow disallow re-parsing?  Is that equivalent to ctx_SourceCode()?
    """
    pass


class DynamicArena(Arena):
    """
    For batch and interactive shell

    TODO:
    - Test that SourceLine and Token are GC'd

    However, it should support:
    - SnipCodeString() for aliases
    - SnipCodeBlock() for Hay

    Neither of those are necessary in the LosslessArena?  We might have
    different utilities there.
    """
    pass
