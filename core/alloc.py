"""
alloc.py - FAILED attempt at memory management.

TODO: Just use a straightforward graph and rely on the garbage collector.
There's NO ARENA.

The idea is to save the LST for functions, but discard it for commands that
have already executed.  Each statement/function can be parsed into a separate
Arena, and the entire Arena can be discarded at once.

Also, we don't want to save comment lines.
"""

from _devbuild.gen.syntax_asdl import source_t, Token, SourceLine
from asdl import runtime
from mycpp.mylib import log

from typing import List, Any

_ = log


def SnipCodeBlock(left, right, lines):
    # type: (Token, Token, List[SourceLine]) -> str
    """Return the code string between left and right tokens, EXCLUSIVE.

    Meaning { } are not included.

    Used for Hay evaluation. Similar to SnipCodeString().
    """
    pieces = []  # type: List[str]

    assert left.length == 1, "{ expected"
    assert right.length == 1, "} expected"

    # Pad with spaces so column numbers aren't off
    pieces.append(' ' * (left.col + 1))

    if left.line == right.line:
        for li in lines:
            if li == left.line:
                piece = li.content[left.col + left.length:right.col]
                pieces.append(piece)
        return ''.join(pieces)

    saving = False
    found_left = False
    found_right = False
    for li in lines:
        if li == left.line:
            found_left = True
            saving = True

            # Save everything after the left token
            piece = li.content[left.col + left.length:]
            pieces.append(piece)
            #log('   %r', piece)
            continue

        if li == right.line:
            found_right = True

            piece = li.content[:right.col]
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


class ctx_Location(object):
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
    """A collection line spans and associated debug info.

    Use Cases:
    1. Error reporting
    2. osh-to-oil Translation
    """

    def __init__(self, save_tokens=False):
        # type: (bool) -> None

        self.save_tokens = save_tokens

        # indexed by span_id
        self.tokens = []  # type: List[Token]
        self.num_tokens = 0

        # All lines that haven't been discarded.  For LST formatting.
        self.lines_list = []  # type: List[SourceLine]

        # reuse these instances in many line_span instances
        self.source_instances = []  # type: List[source_t]

    def SaveTokens(self):
        # type: () -> None
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

    def SaveLinesAndDiscard(self, left, right):
        # type: (Token, Token) -> List[SourceLine]
        """Save the lines between two tokens, e.g. for { and }

        Why?
        - In between { }, we want to preserve lines not pointed to by a token, e.g.
          comment lines.
        - But we don't want to save all lines in an interactive shell:
          echo 1
          echo 2
          ...
          echo 500000
          echo 500001

        The lines should be freed after execution takes place.
        """
        #log('*** Saving lines between %r and %r', left, right)

        saved = []  # type: List[SourceLine]
        saving = False
        for li in self.lines_list:
            if li == left.line:
                saving = True

            # These lines are PERMANENT, and never deleted.  What if you overwrite a
            # function name?  You might want to save those in a the function record
            # ITSELF.
            #
            # This is for INLINE hay blocks that can be evaluated at any point.  In
            # contrast, parse_hay(other_file) uses ParseWholeFile, and we could save
            # all lines.

            # TODO: consider creating a new Arena for each CommandParser?  Or rename itj
            # to 'BackingLines' or something.

            # TODO: We should mutate li.line_id here so it's the index into
            # saved_lines?
            if saving:
                saved.append(li)
                #log('   %r', li.val)

            if li == right.line:
                saving = False
                break

        #log('*** SAVED %d lines', len(saved))

        self.DiscardLines()
        return saved

        #log('SAVED = %s', [line.val for line in self.saved_lines])

    def SnipCodeString(self, left, right):
        # type: (Token, Token) -> str
        """Return the code string between left and right tokens, INCLUSIVE.

        Used for ALIAS expansion, which happens in the PARSER.

        The argument to aliases can span multiple lines, like this:

        $ myalias '1     2     3'
        """
        if left.line == right.line:
            for li in self.lines_list:
                if li == left.line:
                    piece = li.content[left.col:right.col + right.length]
                    return piece

        pieces = []  # type: List[str]
        saving = False
        found_left = False
        found_right = False
        for li in self.lines_list:
            if li == left.line:
                found_left = True
                saving = True

                # Save everything after the left token
                piece = li.content[left.col:]
                pieces.append(piece)
                #log('   %r', piece)
                continue

            if li == right.line:
                found_right = True

                piece = li.content[:right.col + right.length]
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

    def NewToken(self, id_, col, length, src_line, val):
        # type: (int, int, int, SourceLine, str) -> Token
        span_id = self.num_tokens  # spids are just array indices
        self.num_tokens += 1

        tok = Token(id_, col, length, span_id, src_line, val)
        if self.save_tokens:
            self.tokens.append(tok)
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

    def LastSpanId(self):
        # type: () -> int
        """Return one past the last span ID."""
        return len(self.tokens)
