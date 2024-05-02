#!/usr/bin/env python2
"""
j8.py: J8 Notation, a superset of JSON

TODO:

- Many more tests
  - Run JSONTestSuite

Later:

- PrettyPrinter uses hnode.asdl?
  - color
  - line wrapping -- do this later
  - would like CONTRIBUTORS here

- Unify with ASDL pretty printing - NIL8
   - {} [] are identical
   - () is for statically typed ASDL data
     (command.Simple blame_tok:(...) words:[ ])
     although we are also using [] for typed ASDL arrays, not just JSON
   - object IDs
     - @ x123 can create an ID
     - ! x123 can reference an ID
   - <> can be for non-J8 data types?  For the = operator
   - 'hi \(name)' interpolation is useful for code

- Common between JSON8 and NIL8 - for writing by hand
  - comments - # line or // line (JSON5 uses // line, following JS)
  - unquoted identifier names - NIL8 could be more relaxed for (+ 1 (* 3 4))
  - commas
    - JSON8 could have trailing commas rule
    - NIL8 at least has no commas for [1 2 "hi"]
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.value_asdl import (value, value_e, value_t, value_str)
from _devbuild.gen.nil8_asdl import (nvalue, nvalue_t)

from asdl import format as fmt
from core import error
from data_lang import pyj8
# dependency issue: consts.py pulls in frontend/option_def.py
from frontend import consts
from frontend import match
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, NewDict, log

import fastfunc

_ = log

from typing import cast, Dict, List, Tuple, Optional


# COPIED from ui.ValType() to break dep
def ValType(val):
    # type: (value_t) -> str
    """For displaying type errors in the UI."""

    return value_str(val.tag(), dot=False)


if mylib.PYTHON:

    def HeapValueId(val):
        # type: (value_t) -> int
        """
        Python's id() returns the address, which is up to 64 bits.

        In C++ we can use the GC ID, which fits within 32 bits.
        """
        return id(val)


def ValueId(val):
    # type: (value_t) -> int
    """
    Return an integer ID for object that:

    1. Can be used to determine whether 2 objects are the same, e.g. for
       List, Dict, Func, Proc, etc.
    2. Will help detect object cycles

    Primitives types like Int and Float don't have this notion.  They're
    immutable values that are copied and compared by value.
    """
    with tagswitch(val) as case:
        if case(value_e.Null, value_e.Bool, value_e.Int, value_e.Float,
                value_e.Str):
            # These will not be on the heap if we switch to tagged pointers
            # Str is handled conservatively - when we add small string
            # optimization, some strings will be values, so we assume all are.
            return -1
        else:
            return HeapValueId(val)


def ValueIdString(val):
    # type: (value_t) -> str
    """Used by pp value (42) and = 42"""
    heap_id = ValueId(val)  # could be -1
    if heap_id == -1:
        return ''
    else:
        return ' 0x%s' % mylib.hex_lower(heap_id)


def Utf8Encode(code):
    # type: (int) -> str
    """Return utf-8 encoded bytes from a unicode code point.

    Based on https://stackoverflow.com/a/23502707
    """
    num_cont_bytes = 0

    if code <= 0x7F:
        return chr(code & 0x7F)  # ASCII

    elif code <= 0x7FF:
        num_cont_bytes = 1
    elif code <= 0xFFFF:
        num_cont_bytes = 2
    elif code <= 0x10FFFF:
        num_cont_bytes = 3

    else:
        return '\xEF\xBF\xBD'  # unicode replacement character

    bytes_ = []  # type: List[int]
    for _ in xrange(num_cont_bytes):
        bytes_.append(0x80 | (code & 0x3F))
        code >>= 6

    b = (0x1E << (6 - num_cont_bytes)) | (code & (0x3F >> num_cont_bytes))
    bytes_.append(b)
    bytes_.reverse()

    # mod 256 because Python ints don't wrap around!
    tmp = [chr(b & 0xFF) for b in bytes_]
    return ''.join(tmp)


SHOW_CYCLES = 1 << 1  # show as [...] or {...} I think, with object ID
SHOW_NON_DATA = 1 << 2  # non-data objects like Eggex can be <Eggex 0xff>
LOSSY_JSON = 1 << 3  # JSON is lossy

# Hack until we fully translate
assert pyj8.LOSSY_JSON == LOSSY_JSON


def _Print(val, buf, indent, options=0):
    # type: (value_t, mylib.BufWriter, int, int) -> None
    """
    Args:
      indent: number of spaces to indent, or -1 for everything on one line
    """
    p = InstancePrinter(buf, indent, options)
    p.Print(val)


def PrintMessage(val, buf, indent):
    # type: (value_t, mylib.BufWriter, int) -> None
    """ For json8 write (x) and toJson8() 

    Caller must handle error.Encode
    """
    _Print(val, buf, indent)


def PrintJsonMessage(val, buf, indent):
    # type: (value_t, mylib.BufWriter, int) -> None
    """ For json write (x) and toJson()

    Caller must handle error.Encode()
    Doesn't decay to b'' strings - will use Unicode replacement char.
    """
    _Print(val, buf, indent, options=LOSSY_JSON)


def PrintLine(val, f):
    # type: (value_t, mylib.Writer) -> None
    """ For pp line (x) """

    # error.Encode should be impossible - we show cycles and non-data
    buf = mylib.BufWriter()
    _Print(val, buf, -1, options=SHOW_CYCLES | SHOW_NON_DATA)
    f.write(buf.getvalue())
    f.write('\n')


def EncodeString(s, buf, unquoted_ok=False):
    # type: (str, mylib.BufWriter, bool) -> None
    """ For pp proc, etc."""

    if unquoted_ok and fastfunc.CanOmitQuotes(s):
        buf.write(s)
        return

    _Print(value.Str(s), buf, -1)


def MaybeEncodeString(s):
    # type: (str) -> str
    """ For write --json8 $s  and compexport """

    # TODO: add unquoted_ok here?
    # /usr/local/foo-bar/x.y/a_b

    buf = mylib.BufWriter()
    _Print(value.Str(s), buf, -1)
    return buf.getvalue()


def MaybeEncodeJsonString(s):
    # type: (str) -> str
    """ For write --json """

    # TODO: add unquoted_ok here?
    # /usr/local/foo-bar/x.y/a_b
    buf = mylib.BufWriter()
    _Print(value.Str(s), buf, -1, options=LOSSY_JSON)
    return buf.getvalue()


# DFS traversal state
UNSEEN = 0
EXPLORING = 1
FINISHED = 2


class InstancePrinter(object):
    """Print a value tree as J8/JSON."""

    def __init__(self, buf, indent, options):
        # type: (mylib.BufWriter, int, int) -> None
        self.buf = buf
        self.indent = indent
        self.options = options

        # Key is vm.HeapValueId(val)
        # Value is always True
        # Dict[int, None] doesn't translate -- it would be nice to have a set()
        self.visited = {}  # type: Dict[int, int]

    def _ItemIndent(self, level):
        # type: (int) -> None

        if self.indent == -1:
            return

        self.buf.write_spaces((level + 1) * self.indent)

    def _BracketIndent(self, level):
        # type: (int) -> None

        if self.indent == -1:
            return

        self.buf.write_spaces(level * self.indent)

    def _MaybeNewline(self):
        # type: () -> None
        if self.indent == -1:
            return
        self.buf.write('\n')

    def _MaybeSpace(self):
        # type: () -> None
        if self.indent == -1:
            return
        self.buf.write(' ')

    def _PrintList(self, val, level):
        # type: (value.List, int) -> None

        if len(val.items) == 0:  # Special case like Python/JS
            self.buf.write('[]')
        else:
            self.buf.write('[')
            self._MaybeNewline()
            for i, item in enumerate(val.items):
                if i != 0:
                    self.buf.write(',')
                    self._MaybeNewline()

                self._ItemIndent(level)
                self.Print(item, level + 1)
            self._MaybeNewline()

            self._BracketIndent(level)
            self.buf.write(']')

    def _PrintDict(self, val, level):
        # type: (value.Dict, int) -> None

        if len(val.d) == 0:  # Special case like Python/JS
            self.buf.write('{}')
        else:
            self.buf.write('{')
            self._MaybeNewline()
            i = 0
            for k, v in iteritems(val.d):
                if i != 0:
                    self.buf.write(',')
                    self._MaybeNewline()

                self._ItemIndent(level)

                pyj8.WriteString(k, self.options, self.buf)

                self.buf.write(':')
                self._MaybeSpace()

                self.Print(v, level + 1)

                i += 1

            self._MaybeNewline()
            self._BracketIndent(level)
            self.buf.write('}')

    def Print(self, val, level=0):
        # type: (value_t, int) -> None

        # special value that means everything is on one line
        # It's like
        #    JSON.stringify(d, null, 0)
        # except we use -1, not 0.  0 can still have newlines.

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Null):
                self.buf.write('null')

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                self.buf.write('true' if val.b else 'false')

            elif case(value_e.Int):
                val = cast(value.Int, UP_val)
                # TODO: avoid intermediate allocation with
                # self.buf.WriteBigInt(val.i)
                #
                # Or maybe we need pyj8.WriteBigInt() because truly BigInt may
                # be of arbitrary length, and will need a growth strategy.
                # Although that is not very common, so we could allocate in
                # that case.

                self.buf.write(mops.ToStr(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                # TODO: avoid intrmediate allocation with
                # self.buf.WriteFloat(val.f)
                self.buf.write(str(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)

                pyj8.WriteString(val.s, self.options, self.buf)

            elif case(value_e.List):
                val = cast(value.List, UP_val)

                # Cycle detection, only for containers that can be in cycles
                heap_id = HeapValueId(val)

                node_state = self.visited.get(heap_id, UNSEEN)
                if node_state == FINISHED:
                    # Print it AGAIN.  We print a JSON tree, which means we can
                    # visit and print nodes MANY TIMES, as long as they're not
                    # in a cycle.
                    self._PrintList(val, level)
                    return
                if node_state == EXPLORING:
                    if self.options & SHOW_CYCLES:
                        self.buf.write('[ -->%s ]' % ValueIdString(val))
                        return
                    else:
                        # node.js prints which index closes the cycle
                        raise error.Encode(
                            "Can't encode List%s in object cycle" %
                            ValueIdString(val))

                self.visited[heap_id] = EXPLORING
                self._PrintList(val, level)
                self.visited[heap_id] = FINISHED

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)

                # Cycle detection, only for containers that can be in cycles
                heap_id = HeapValueId(val)

                node_state = self.visited.get(heap_id, UNSEEN)
                if node_state == FINISHED:
                    # Print it AGAIN.  We print a JSON tree, which means we can
                    # visit and print nodes MANY TIMES, as long as they're not
                    # in a cycle.
                    self._PrintDict(val, level)
                    return
                if node_state == EXPLORING:
                    if self.options & SHOW_CYCLES:
                        self.buf.write('{ -->%s }' % ValueIdString(val))
                        return
                    else:
                        # node.js prints which key closes the cycle
                        raise error.Encode(
                            "Can't encode Dict%s in object cycle" %
                            ValueIdString(val))

                self.visited[heap_id] = EXPLORING
                self._PrintDict(val, level)
                self.visited[heap_id] = FINISHED

            # BashArray and BashAssoc should be printed with pp line (x), e.g.
            # for spec tests.
            # - BashAssoc has a clear encoding.
            # - BashArray could eventually be Dict[int, str].  But that's not
            #   encodable in JSON, which has string keys!
            #   So I think we can print it like ["a",null,'b"] and that won't
            #   change.  That's what users expect.
            elif case(value_e.BashArray):
                val = cast(value.BashArray, UP_val)

                self.buf.write('[')
                self._MaybeNewline()
                for i, s in enumerate(val.strs):
                    if i != 0:
                        self.buf.write(',')
                        self._MaybeNewline()

                    self._ItemIndent(level)
                    if s is None:
                        self.buf.write('null')
                    else:
                        pyj8.WriteString(s, self.options, self.buf)

                self._MaybeNewline()

                self._BracketIndent(level)
                self.buf.write(']')

            elif case(value_e.BashAssoc):
                val = cast(value.BashAssoc, UP_val)

                self.buf.write('{')
                self._MaybeNewline()
                i = 0
                for k2, v2 in iteritems(val.d):
                    if i != 0:
                        self.buf.write(',')
                        self._MaybeNewline()

                    self._ItemIndent(level)

                    pyj8.WriteString(k2, self.options, self.buf)

                    self.buf.write(':')
                    self._MaybeSpace()

                    pyj8.WriteString(v2, self.options, self.buf)

                    i += 1

                self._MaybeNewline()
                self._BracketIndent(level)
                self.buf.write('}')

            else:
                pass  # mycpp workaround
                if self.options & SHOW_NON_DATA:
                    # Similar to = operator, ui.DebugPrint()
                    # TODO: that prints value.Range in a special way
                    ysh_type = ValType(val)
                    id_str = ValueIdString(val)
                    self.buf.write('<%s%s>' % (ysh_type, id_str))
                else:
                    raise error.Encode("Can't serialize object of type %s" %
                                       ValType(val))


class PrettyPrinter(object):
    """ Unused right now, but could enhance the = operator.

    Output to polymorphic ColorOutput 

    Features like asdl/format.py:
    - line wrapping
    - color
    - sharing detection by passing in a REF COUTN dict
      - print @123 the first time, and then print ... the second time

    and 

    - Pretty spaces: {"k": "v", "k2": "v2"} instead of {"k":"v","k2","v2"}
    - Unquoted: {k: "v", k2: "v2"} instead of {"k": "v", "k2": "v2"}

    - Omitting commas for ASDL?  Maybe we can use two spaces

    (Token id: Id.VSub_DollarName  start: 0  length: 3)
    (Token id:Id.VSub_DollarName start:0 length:3)  - color makes this work
    """

    def __init__(self, max_col):
        # type: (int) -> None
        self.max_col = max_col

        # This could be an optimized set an C++ bit set like
        # mark_sweep_heap.h, rather than a Dict
        #self.unique_objs = mylib.UniqueObjects()

        # first pass of object ID -> number of times references

        self.ref_count = {}  # type: Dict[int, int]

    def PrettyTree(self, val, f):
        # type: (value_t, fmt.ColorOutput) -> None

        # TODO: first convert to hnode.asdl types?

        # Although we might want
        # hnode.AlreadyShown = (str type, int unique_id)
        pass

    def Print(self, val, buf):
        # type: (value_t, mylib.BufWriter) -> None

        # Or print to stderr?
        f = fmt.DetectConsoleOutput(mylib.Stdout())
        self.PrettyTree(val, f)

        # Then print those with ASDL
        pass


class LexerDecoder(object):
    """J8 lexer and string decoder.

    Similar interface as SimpleLexer, except we return an optional decoded
    string
    """

    def __init__(self, s, is_j8, lang_str):
        # type: (str, bool, str) -> None
        self.s = s
        self.is_j8 = is_j8
        self.lang_str = lang_str

        self.pos = 0

        # current line being lexed -- for error messages
        self.cur_line_num = 1

        # Reuse this instance to save GC objects.  JSON objects could have
        # thousands of strings.
        self.decoded = mylib.BufWriter()

    def _Error(self, msg, end_pos):
        # type: (str, int) -> error.Decode

        # Use the current position as start pos
        return error.Decode(msg, self.s, self.pos, end_pos, self.cur_line_num)

    def Next(self):
        # type: () -> Tuple[Id_t, int, Optional[str]]
        """ Returns a token and updates self.pos """

        tok_id, end_pos = match.MatchJ8Token(self.s, self.pos)

        if not self.is_j8:
            if tok_id in (Id.Left_BSingleQuote, Id.Left_USingleQuote):
                raise self._Error(
                    "Single quotes aren't part of JSON; you may want 'json8 read'",
                    end_pos)
            if tok_id == Id.Ignored_Comment:
                raise self._Error(
                    "Comments aren't part of JSON; you may want 'json8 read'",
                    end_pos)

        if tok_id in (Id.Left_DoubleQuote, Id.Left_BSingleQuote,
                      Id.Left_USingleQuote):
            return self._DecodeString(tok_id, end_pos)

        if tok_id == Id.Ignored_Newline:
            #log('LINE %d', self.cur_line_num)
            self.cur_line_num += 1

        self.pos = end_pos
        return tok_id, end_pos, None

    def NextForLines(self):
        # type: () -> Tuple[Id_t, int, Optional[str]]
        """ Like Next(), but for J8 Lines """

        tok_id, end_pos = match.MatchJ8LinesToken(self.s, self.pos)

        if tok_id in (Id.Left_DoubleQuote, Id.Left_BSingleQuote,
                      Id.Left_USingleQuote):
            return self._DecodeString(tok_id, end_pos)

        # Check that UNQUOTED lines are valid UTF-8.  (_DecodeString() does
        # this for quoted strings.)
        if (tok_id == Id.Lit_Chars and
                not pyj8.PartIsUtf8(self.s, self.pos, end_pos)):
            raise self._Error(
                'Invalid UTF-8 in %s string literal' % self.lang_str, end_pos)
        if tok_id == Id.Char_AsciiControl:
            raise self._Error(
                "J8 Lines can't have unescaped ASCII control chars", end_pos)

        if tok_id == Id.J8_Newline:
            #log('LINE %d', self.cur_line_num)
            self.cur_line_num += 1

        self.pos = end_pos
        return tok_id, end_pos, None

    def _DecodeString(self, left_id, str_pos):
        # type: (Id_t, int) -> Tuple[Id_t, int, Optional[str]]
        """ Returns a string token and updates self.pos """

        while True:
            if left_id == Id.Left_DoubleQuote:
                tok_id, str_end = match.MatchJsonStrToken(self.s, str_pos)
            else:
                tok_id, str_end = match.MatchJ8StrToken(self.s, str_pos)

            #log('String tok %s', Id_str(tok_id))

            if tok_id == Id.Eol_Tok:
                # TODO: point to beginning of # quote?
                raise self._Error(
                    'Unexpected EOF while lexing %s string' % self.lang_str,
                    str_end)
            if tok_id == Id.Unknown_Backslash:
                raise self._Error(
                    'Bad backslash escape in %s string' % self.lang_str,
                    str_end)
            if tok_id == Id.Char_AsciiControl:
                raise self._Error(
                    "%s strings can't have unescaped ASCII control chars" %
                    self.lang_str, str_end)

            if tok_id in (Id.Right_SingleQuote, Id.Right_DoubleQuote):

                self.pos = str_end

                s = self.decoded.getvalue()
                self.decoded.clear()  # reuse this instance

                #log('decoded %r', self.decoded.getvalue())
                return Id.J8_String, str_end, s

            #
            # Now handle each kind of token
            #

            if tok_id == Id.Lit_Chars:  # JSON and J8
                part = self.s[str_pos:str_end]
                if not pyj8.PartIsUtf8(self.s, str_pos, str_end):
                    raise self._Error(
                        'Invalid UTF-8 in %s string literal' % self.lang_str,
                        str_end)

            # TODO: would be nice to avoid allocation in all these cases.
            # But LookupCharC() would have to change.

            elif tok_id == Id.Char_OneChar:  # JSON and J8
                ch = self.s[str_pos + 1]
                part = consts.LookupCharC(ch)

            elif tok_id == Id.Char_UBraced:  # J8 only
                h = self.s[str_pos + 3:str_end - 1]
                i = int(h, 16)

                # Same check in osh/word_parse.py
                if 0xD800 <= i and i < 0xE000:
                    raise self._Error(
                        r"\u{%s} escape is illegal because it's in the surrogate range"
                        % h, str_end)

                part = Utf8Encode(i)

            elif tok_id == Id.Char_YHex:  # J8 only
                h = self.s[str_pos + 2:str_end]

                # Same check in osh/word_parse.py
                if left_id != Id.Left_BSingleQuote:
                    assert left_id != Id.Left_BTSingleQuote, "Not handled here"
                    raise self._Error(
                        r"\y%s escapes not allowed in u'' strings" % h,
                        str_end)

                i = int(h, 16)
                part = chr(i)

            elif tok_id == Id.Char_SurrogatePair:
                h1 = self.s[str_pos + 2:str_pos + 6]
                h2 = self.s[str_pos + 8:str_pos + 12]

                # https://www.oilshell.org/blog/2023/06/surrogate-pair.html
                i1 = int(h1, 16) - 0xD800  # high surrogate
                i2 = int(h2, 16) - 0xDC00  # low surrogate
                code_point = 0x10000 + (i1 << 10) + i2

                part = Utf8Encode(code_point)

            elif tok_id == Id.Char_Unicode4:  # JSON only, unpaired
                h = self.s[str_pos + 2:str_end]
                i = int(h, 16)
                part = Utf8Encode(i)

            else:
                # Should never happen
                raise AssertionError(Id_str(tok_id))

            #log('%s part %r', Id_str(tok_id), part)
            self.decoded.write(part)
            str_pos = str_end


class _Parser(object):

    def __init__(self, s, is_j8):
        # type: (str, bool) -> None
        self.s = s
        self.is_j8 = is_j8
        self.lang_str = "J8" if is_j8 else "JSON"

        self.lexer = LexerDecoder(s, is_j8, self.lang_str)
        self.tok_id = Id.Undefined_Tok
        self.start_pos = 0
        self.end_pos = 0
        self.decoded = ''  # decoded J8 string

    def _Next(self):
        # type: () -> None

        # This isn't the start of a J8_Bool token, it's the END of the token before it
        while True:
            self.start_pos = self.end_pos
            self.tok_id, self.end_pos, self.decoded = self.lexer.Next()
            if self.tok_id not in (Id.Ignored_Space, Id.Ignored_Newline,
                                   Id.Ignored_Comment):
                break
            # TODO: add Ignored_Newline to count lines, and show line numbers
            # in errors messages.  The position of the last newline and a token
            # can be used to calculate a column number.

        #log('NEXT %s %s %s %s', Id_str(self.tok_id), self.start_pos, self.end_pos, self.decoded or '-')

    def _Eat(self, tok_id):
        # type: (Id_t) -> None

        if self.tok_id != tok_id:
            #log('position %r %d-%d %r', self.s, self.start_pos,
            #    self.end_pos, self.s[self.start_pos:self.end_pos])
            raise self._ParseError("Expected %s, got %s" %
                                   (Id_str(tok_id), Id_str(self.tok_id)))
        self._Next()

    def _NextForLines(self):
        # type: () -> None
        """Like _Next, but use the J8 Lines lexer."""
        self.start_pos = self.end_pos
        self.tok_id, self.end_pos, self.decoded = self.lexer.NextForLines()

    def _ParseError(self, msg):
        # type: (str) -> error.Decode
        return error.Decode(msg, self.s, self.start_pos, self.end_pos,
                            self.lexer.cur_line_num)


class Parser(_Parser):
    """JSON and JSON8 Parser."""

    def __init__(self, s, is_j8):
        # type: (str, bool) -> None
        _Parser.__init__(self, s, is_j8)

    def _ParsePair(self):
        # type: () -> Tuple[str, value_t]

        k = self.decoded  # Save the potential string value
        self._Eat(Id.J8_String)  # Check that it's a string
        assert k is not None

        self._Eat(Id.J8_Colon)

        v = self._ParseValue()
        return k, v

    def _ParseDict(self):
        # type: () -> value_t
        """
        pair = string ':' value
        Dict      = '{' '}'
                  | '{' pair (',' pair)* '}'
        """
        # precondition
        assert self.tok_id == Id.J8_LBrace, Id_str(self.tok_id)

        #log('> Dict')

        d = NewDict()  # type: Dict[str, value_t]

        self._Next()
        if self.tok_id == Id.J8_RBrace:
            self._Next()
            return value.Dict(d)

        k, v = self._ParsePair()
        d[k] = v
        #log('  [1] k %s  v  %s  Id %s', k, v, Id_str(self.tok_id))

        while self.tok_id == Id.J8_Comma:
            self._Next()
            k, v = self._ParsePair()
            d[k] = v
            #log('  [2] k %s  v  %s  Id %s', k, v, Id_str(self.tok_id))

        self._Eat(Id.J8_RBrace)

        #log('< Dict')

        return value.Dict(d)

    def _ParseList(self):
        # type: () -> value_t
        """
        List = '[' ']'
             | '[' value (',' value)* ']'
        """
        assert self.tok_id == Id.J8_LBracket, Id_str(self.tok_id)

        items = []  # type: List[value_t]

        self._Next()
        if self.tok_id == Id.J8_RBracket:
            self._Next()
            return value.List(items)

        items.append(self._ParseValue())

        while self.tok_id == Id.J8_Comma:
            self._Next()
            items.append(self._ParseValue())

        self._Eat(Id.J8_RBracket)

        return value.List(items)

    def _ParseValue(self):
        # type: () -> value_t
        if self.tok_id == Id.J8_LBrace:
            return self._ParseDict()

        elif self.tok_id == Id.J8_LBracket:
            return self._ParseList()

        elif self.tok_id == Id.J8_Null:
            self._Next()
            return value.Null

        elif self.tok_id == Id.J8_Bool:
            #log('%r %d', self.s[self.start_pos], self.start_pos)
            b = value.Bool(self.s[self.start_pos] == 't')
            self._Next()
            return b

        elif self.tok_id == Id.J8_Int:
            part = self.s[self.start_pos:self.end_pos]
            self._Next()
            return value.Int(mops.FromStr(part))

        elif self.tok_id == Id.J8_Float:
            part = self.s[self.start_pos:self.end_pos]
            self._Next()
            return value.Float(float(part))

        # UString, BString too
        elif self.tok_id == Id.J8_String:
            str_val = value.Str(self.decoded)
            #log('d %r', self.decoded)
            self._Next()
            return str_val

        elif self.tok_id == Id.Eol_Tok:
            raise self._ParseError('Unexpected EOF while parsing %s' %
                                   self.lang_str)

        else:  # Id.Unknown_Tok, Id.J8_{LParen,RParen}
            raise self._ParseError('Invalid token while parsing %s: %s' %
                                   (self.lang_str, Id_str(self.tok_id)))

    def ParseValue(self):
        # type: () -> value_t
        """ Raises error.Decode. """
        self._Next()
        obj = self._ParseValue()
        if self.tok_id != Id.Eol_Tok:
            raise self._ParseError('Unexpected trailing input')
        return obj


class Nil8Parser(_Parser):
    """
    Tokens not in JSON8:
      LParen RParen Symbol

    Tokens not in JSON, but in JSON8 and NIL8:
      Identifier (unquoted keys)
      Ignored_Comment
    """

    def __init__(self, s, is_j8):
        # type: (str, bool) -> None
        _Parser.__init__(self, s, is_j8)

    if 0:

        def _LookAhead(self):
            # type: () -> Id_t
            """
            Don't need this right now
            """
            end_pos = self.end_pos  # look ahead from last token
            while True:
                tok_id, end_pos = match.MatchJ8Token(self.s, end_pos)
                if tok_id not in (Id.Ignored_Space, Id.Ignored_Newline,
                                  Id.Ignored_Comment):
                    break
            return tok_id

    def _ParseRecord(self):
        # type: () -> nvalue_t
        """
        Yaks
          (self->Next)             =>  (-> self Next)
          (self->Next obj.field)   =>  ((-> self Next) (. obj field))

          Similar to
          ((identity identity) 42) => 42 in Clojure

        ASDL
          (Node left:(. x4beef2))
          (Node left !x4beef2)

        # Ambiguous because value can be identifier.
        # We have to look ahead to and see if there's a colon :
        field = 
          Identifier ':' value
        | value

        record = '(' head field* ')'

        - Identifier | Symbol are treated the same, it's a side effect of
          the lexing style
        - do positional args come before named args
        - () is invalid?  Use [] for empty list
        """
        assert self.tok_id == Id.J8_LParen, Id_str(self.tok_id)

        items = []  # type: List[nvalue_t]

        self._Next()
        if self.tok_id == Id.J8_RParen:
            self._Next()
            return nvalue.List(items)

        #log('TOK %s', Id_str(self.tok_id))
        while self.tok_id != Id.J8_RParen:
            items.append(self._ParseNil8())
            #log('TOK 2 %s', Id_str(self.tok_id))

        self._Eat(Id.J8_RParen)

        return nvalue.List(items)

    def _ParseList8(self):
        # type: () -> nvalue_t
        """
        List8 = '[' value* ']'

        No commas, not even optional ones for now.
        """
        assert self.tok_id == Id.J8_LBracket, Id_str(self.tok_id)

        items = []  # type: List[nvalue_t]

        self._Next()
        if self.tok_id == Id.J8_RBracket:
            self._Next()
            return nvalue.List(items)

        #log('TOK %s', Id_str(self.tok_id))
        while self.tok_id != Id.J8_RBracket:
            items.append(self._ParseNil8())
            #log('TOK 2 %s', Id_str(self.tok_id))

        self._Eat(Id.J8_RBracket)

        return nvalue.List(items)

    def _ParseNil8(self):
        # type: () -> nvalue_t
        if self.tok_id == Id.J8_LParen:
            obj = self._ParseRecord()  # type: nvalue_t
            #return obj

        elif self.tok_id == Id.J8_LBracket:
            obj = self._ParseList8()
            #return obj

        # Primitives are copied from J8 above.
        # TODO: We also want hex literals.
        elif self.tok_id == Id.J8_Null:
            self._Next()
            obj = nvalue.Null

        elif self.tok_id == Id.J8_Bool:
            b = nvalue.Bool(self.s[self.start_pos] == 't')
            self._Next()
            obj = b

        elif self.tok_id == Id.J8_Int:
            part = self.s[self.start_pos:self.end_pos]
            self._Next()
            obj = nvalue.Int(int(part))

        elif self.tok_id == Id.J8_Float:
            part = self.s[self.start_pos:self.end_pos]
            self._Next()
            obj = nvalue.Float(float(part))

        elif self.tok_id == Id.J8_String:
            str_val = nvalue.Str(self.decoded)
            self._Next()
            obj = str_val

        # <- etc.
        elif self.tok_id in (Id.J8_Identifier, Id.J8_Operator, Id.J8_Colon,
                             Id.J8_Comma):
            # unquoted "word" treated like a string
            part = self.s[self.start_pos:self.end_pos]
            self._Next()
            obj = nvalue.Symbol(part)

        elif self.tok_id == Id.Eol_Tok:
            raise self._ParseError('Unexpected EOF while parsing %s' %
                                   self.lang_str)

        else:  # Id.Unknown_Tok, Id.J8_{LParen,RParen}
            raise self._ParseError('Invalid token while parsing %s: %s' %
                                   (self.lang_str, Id_str(self.tok_id)))

        #log('YO %s', Id_str(self.tok_id))
        if self.tok_id in (Id.J8_Operator, Id.J8_Colon, Id.J8_Comma):
            #log('AT %s', Id_str(self.tok_id))

            # key: "value" -> (: key "value")
            part = self.s[self.start_pos:self.end_pos]
            op = nvalue.Symbol(part)

            self._Next()
            operand2 = self._ParseNil8()
            infix = nvalue.List([op, obj, operand2])  # type: nvalue_t
            #print("--> INFIX %d %s" % (id(infix), infix))
            return infix

        #next_id = self._LookAhead()
        #print('NEXT %s' % Id_str(next_id))

        #raise AssertionError()
        #print("--> OBJ %d %s" % (id(obj), obj))
        return obj

    def ParseNil8(self):
        # type: () -> nvalue_t
        """ Raises error.Decode. """
        self._Next()
        #print('yo')
        obj = self._ParseNil8()
        #print("==> %d %s" % (id(obj), obj))
        if self.tok_id != Id.Eol_Tok:
            raise self._ParseError('Unexpected trailing input')
        return obj


class J8LinesParser(_Parser):
    """Decode lines from a string with newlines.

    We specify this with a grammar, to preserve location info and to reduce
    allocations.  (But note that unquoted_line is more like a LOOP than it is
    grammatical.)

    Grammar:

        end           = J8_Newline | Eol_Tok

        empty_line    = WS_Space? end

        # special case: read until end token, but REMOVE trailing WS_Space
        unquoted_line = WS_Space? Lit_Chars ANY* WS_Space? end

        j8_line       = WS_Space? J8_String WS_Space? end

        lines         = (empty_line | unquoted_line | j8_line)*

    where Lit_Chars is valid UTF-8

    Notes:

    (1) We disallow multiple strings on a line, like:

        "json" "json2"
        "json" unquoted

    (2) Internal quotes are allowed on unquoted lines.  Consider this line:

        foo "" u''

    The "" and u'' are not a decoded string, because the line started with
    Id.Lit_Chars literals.

    (3) This is related to TSV8?  Similar rules.  Does TSV8 have empty cells?
        Does it have - for empty cell?
    """

    def __init__(self, s):
        # type: (str) -> None
        _Parser.__init__(self, s, True)

    def _Show(self, s):
        # type: (str) -> None
        log('%s tok_id %s %d-%d', s, Id_str(self.tok_id), self.start_pos,
            self.end_pos)

    def _ParseLine(self, out):
        # type: (List[str]) -> None
        """ May append a line to 'out' """
        #self._Show('1')
        if self.tok_id == Id.WS_Space:
            self._NextForLines()

        # Empty line - return without doing anything
        if self.tok_id in (Id.J8_Newline, Id.Eol_Tok):
            self._NextForLines()
            return

        # Quoted string on line
        if self.tok_id == Id.J8_String:
            out.append(self.decoded)
            self._NextForLines()

            if self.tok_id == Id.WS_Space:  # trailing whitespace
                self._NextForLines()

            if self.tok_id not in (Id.J8_Newline, Id.Eol_Tok):
                raise self._ParseError('Unexpected text after J8 Line (%s)' %
                                       Id_str(self.tok_id))

            self._NextForLines()
            return

        # Unquoted line
        if self.tok_id == Id.Lit_Chars:
            # '  unquoted "" text on line  '   # read every token until end
            string_start = self.start_pos
            while True:
                # for stripping whitespace
                prev_id = self.tok_id
                prev_start = self.start_pos

                self._NextForLines()

                # It would be nicer if "middle" Id.WS_Space tokens didn't have
                # \r, but we're sticking with the JSON spec definition of
                # whitespace.  (As another data point, CPython on Unix allows
                # \r in the middle of expressions, treating it as whitespace.)
                if self.tok_id in (Id.J8_Newline, Id.Eol_Tok):
                    break

            if prev_id == Id.WS_Space:
                string_end = prev_start  # remove trailing whitespace
            else:
                string_end = self.start_pos

            out.append(self.s[string_start:string_end])

            self._NextForLines()  # past newline
            return

        raise AssertionError(Id_str(self.tok_id))

    def Parse(self):
        # type: () -> List[str]
        """ Raises error.Decode. """
        self._NextForLines()

        lines = []  # type: List[str]
        while self.tok_id != Id.Eol_Tok:
            self._ParseLine(lines)

        if self.tok_id != Id.Eol_Tok:
            raise self._ParseError('Unexpected trailing input in J8 Lines')

        return lines


def SplitJ8Lines(s):
    # type: (str) -> List[str]
    """Used by @(echo split command sub)

    Raises:
      error.Decode

    3 Errors:
    - J8 string syntax error inside quotes
    - Extra input on line
    - unquoted line isn't utf-8
    """
    p = J8LinesParser(s)
    return p.Parse()


# vim: sw=4
