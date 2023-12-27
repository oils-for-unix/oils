#!/usr/bin/env python2
"""
j8.py: J8 Notation and Related Utilities

TODO:

- Int vs. Float
  - match.LooksLikeInteger() is a shortcut

- Errors
  - Figure out location info for parse errors - turn a position into a line and
    column?
  - Assert should become parse errors

- Distinguish JSON vs. J8 -
  - json should fail can fail to encode
  - and distinguish "" b"" u""

- Distinguish pretty-printing vs. data transfer
  - SHOW_CYCLES and SHOW_NON_DATA

- Make the whole thing translate to C++
  - use Bjoern DFA for UTF-8 validation in printing and parsing
  - move more of LexerDecoder out of pyj8.py?  I think it can translate

- Many more tests
  - Run JSONTestSuite

- QSN maybe_shell_encode() is used for bash features
  - Remove shell_compat which does \\x00 instead of \\0

Other

- PrettyPrinter uses hnode.asdl?
  - color
  - line wrapping -- do this later
  - this is open to contribution

- Harmonize the API in data_lang/qsn.py 
  - use mylib.BufWriter output
  - use u_style.LiteralUtf8 instead of BIT8_UTF8, etc.

- Unify with ASDL pretty printing?

   () is for statically typed ASDL data?
      (command.Simple blame_tok:(...) words:[ ])
   <> is for non-J8 errors?  For the = operator
"""

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.value_asdl import (value, value_e, value_t)

from asdl import format as fmt
from core import vm
from data_lang import pyj8
from data_lang import qsn
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, NewDict, log

_ = log
unused = pyj8

from typing import cast, Dict, List, Tuple


class PrettyPrinter(object):
    """
    For = operator.  Output to polymorphic ColorOutput 

    Also pp value (x, option = :x)

    Features like asdl/format.py:
    - line wrapping
    - color

    Options:
    - unicode.UEscape
    - Float: It would be nice to separate the exact parts, like we do with
      strings

    Fixed behavior:
    - j_prefix.WhenNecessary
    - dialect.J8
    - Prints <Dict #42> on cycles
    - Prints ASDL (value.Expr ...) on non-data types
    """

    def __init__(self, max_col):
        # type: (int) -> None
        self.max_col = max_col

        # This could be an optimized set an C++ bit set like
        # mark_sweep_heap.h, rather than a Dict
        self.unique_objs = mylib.UniqueObjects()

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


SHOW_CYCLES = 1  # pretty-printing
SHOW_NON_DATA = 2  # non-data objects like Eggex can be <Eggex 0xff>

class Printer(object):
    """
    For json/j8 write (x), write (x), = operator, pp line (x)

    Options:
    - Control over escaping: \\u \\x raw UTF-8
    - Control over j prefix: when necessary, or always
    - Control over strict JSON subset (--json vs --j8)
    - Dumb indentation, not smart line wrapping
    """

    def __init__(self):
        # type: () -> None
        """
        Args:
          # These can all be packed into the same byte.  ASDL needs bit_set
          # support I think?
          options:
            control j"" vs. ""
            control escaping \\x and \\u escaping like QSN
            pretty.UnquotedKeys - ASDL uses this?
        """
        self.options = 0
        self.spaces = {0: ''}  # cache of strings with spaces

    # Could be PrintMessage or PrintJsonMessage()
    def _Print(self, val, buf, indent):
        # type: (value_t, mylib.BufWriter, int) -> None
        """
        Args:
          indent: number of spaces to indent, or -1 for everything on one line
        """
        p = InstancePrinter(buf, indent, self.options, self.spaces)
        p.Print(val)

    def PrintMessage(self, val, buf, indent):
        # type: (value_t, mylib.BufWriter, int) -> None
        """ For j8 write (x) """
        self._Print(val, buf, indent)

    def PrintJsonMessage(self, val, buf, indent):
        # type: (value_t, mylib.BufWriter, int) -> None
        """ For json write (x)

        Doesn't decay to b"" strings
        Either raise error.Decode() or use unicode replacement char
        """
        self._Print(val, buf, indent)

    def DebugPrint(self, val, f):
        # type: (value_t, mylib.Writer) -> None
        """
        For = operator.
        TODO: set options SHOW_CYCLES SHOW_NON_DATA
        """
        buf = mylib.BufWriter()
        self._Print(val, buf, -1)
        f.write(buf.getvalue())
        f.write('\n')

    def PrintLine(self, val, f):
        # type: (value_t, mylib.Writer) -> None
        """ For pp line (x) """
        buf = mylib.BufWriter()
        self._Print(val, buf, -1)
        f.write(buf.getvalue())
        f.write('\n')

    def MaybeEncodeString(self, s ):
        # type: (str) -> str
        """ For write --j8 $s 

        Do we also want write (x) to use J8 notation?  It's the default
        serialization.  But j8 write (x) is simple enough.
        """
        # There should be an option to not quote "plain words" like
        # /usr/local/foo-bar/x.y/a_b
        buf = mylib.BufWriter()
        self._Print(value.Str(s), buf, -1)
        return buf.getvalue()


class InstancePrinter(object):
    """Print a value tree as J8/JSON."""

    def __init__(self, buf, indent, options, spaces):
        # type: (mylib.BufWriter, int, int, Dict[int, str]) -> None
        self.buf = buf
        self.indent = indent
        self.options = options
        self.spaces = spaces

        # Key is vm.HeapValueId(val)
        # Value is always True
        # Dict[int, None] doesn't translate -- it would be nice to have a set()
        self.seen = {}  # type: Dict[int, bool]

    def _GetIndent(self, num_spaces):
        # type: (int) -> str
        if num_spaces not in self.spaces:
            self.spaces[num_spaces] = ' ' * num_spaces
        return self.spaces[num_spaces]

    def _StringToBuf(self, s):
        # type: (str) -> None

        if mylib.PYTHON:
            # TODO: port this to C++
            pyj8.WriteString(s, 0, self.buf)
        else:
            self.buf.write('"')
            valid_utf8 = qsn.EncodeRunes(s, qsn.BIT8_UTF8, self.buf)
            if not valid_utf8:
                pass
            self.buf.write('"')

    def Print(self, val, level=0):
        # type: (value_t, int) -> None

        #log('indent %r level %d', indent, level)

        # special value that means everything is on one line
        # It's like
        #    JSON.stringify(d, null, 0)
        # except we use -1, not 0.  0 can still have newlines.

        if self.indent == -1:
            bracket_indent = ''
            item_indent = ''
            maybe_newline = ''
            maybe_space = ''
        else:
            bracket_indent = self._GetIndent(level * self.indent)
            item_indent = self._GetIndent((level + 1) * self.indent)
            maybe_newline = '\n'
            maybe_space = ' '  # after colon

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Null):
                self.buf.write('null')

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                self.buf.write('true' if val.b else 'false')

            elif case(value_e.Int):
                val = cast(value.Int, UP_val)
                # TODO: use pyj8.WriteInt(val.i, self.buf)
                self.buf.write(str(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)

                # TODO: use pyj8.WriteFloat(val.f, self.buf)
                self.buf.write(str(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)

                # TODO: pyj8.WriteString(val.s, self.buf)
                self._StringToBuf(val.s)

            elif case(value_e.List):
                val = cast(value.List, UP_val)

                # Cycle detection, only for containers that can be in cycles
                heap_id = vm.HeapValueId(val)
                if heap_id in self.seen:
                    raise AssertionError()
                self.seen[heap_id] = True

                self.buf.write('[')
                self.buf.write(maybe_newline)
                for i, item in enumerate(val.items):
                    if i != 0:
                        self.buf.write(',')
                        self.buf.write(maybe_newline)

                    self.buf.write(item_indent)
                    self.Print(item, level + 1)
                self.buf.write(maybe_newline)

                self.buf.write(bracket_indent)
                self.buf.write(']')

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)

                # Cycle detection, only for containers that can be in cycles
                heap_id = vm.HeapValueId(val)
                if heap_id in self.seen:
                    raise AssertionError()
                self.seen[heap_id] = True

                self.buf.write('{')
                self.buf.write(maybe_newline)
                i = 0
                for k, v in iteritems(val.d):
                    if i != 0:
                        self.buf.write(',')
                        self.buf.write(maybe_newline)

                    self.buf.write(item_indent)

                    self._StringToBuf(k)

                    self.buf.write(':')
                    self.buf.write(maybe_space)

                    self.Print(v, level + 1)

                    i += 1

                self.buf.write(maybe_newline)
                self.buf.write(bracket_indent)
                self.buf.write('}')

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
                self.buf.write(maybe_newline)
                for i, s in enumerate(val.strs):
                    if i != 0:
                        self.buf.write(',')
                        self.buf.write(maybe_newline)

                    self.buf.write(item_indent)
                    if s is None:
                        self.buf.write('null')
                    else:
                        self._StringToBuf(s)

                self.buf.write(maybe_newline)

                self.buf.write(bracket_indent)
                self.buf.write(']')

            elif case(value_e.BashAssoc):
                val = cast(value.BashAssoc, UP_val)

                self.buf.write('{')
                self.buf.write(maybe_newline)
                i = 0
                for k2, v2 in iteritems(val.d):
                    if i != 0:
                        self.buf.write(',')
                        self.buf.write(maybe_newline)

                    self.buf.write(item_indent)

                    self._StringToBuf(k2)

                    self.buf.write(':')
                    self.buf.write(maybe_space)

                    self._StringToBuf(v2)

                    i += 1

                self.buf.write(maybe_newline)
                self.buf.write(bracket_indent)
                self.buf.write('}')

            else:
                # TODO: Option to use the <> format of = operator?
                pass


if mylib.PYTHON:

    class Parser(object):

        def __init__(self, s):
            # type: (str) -> None
            self.s = s
            self.lexer = pyj8.LexerDecoder(s)

            self.tok_id = Id.Undefined_Tok
            self.start_pos = 0
            self.end_pos = 0
            self.decoded = ''

        def _Next(self):
            # type: () -> None
            self.start_pos = self.end_pos
            self.tok_id, self.end_pos, self.decoded = self.lexer.Next()
            #log('NEXT %s %s %s', Id_str(self.tok_id), self.end_pos, self.decoded or '-')

        def _Eat(self, tok_id):
            # type: (Id_t) -> None

            # TODO: Need location info
            if self.tok_id != tok_id:
                #log('position %r %d-%d %r', self.s, self.start_pos,
                #    self.end_pos, self.s[self.start_pos:self.end_pos])
                raise AssertionError("Expected %s, got %s" % (Id_str(tok_id),
                                                              Id_str(self.tok_id)))
            self._Next()

        def _ParsePair(self):
            # type: () -> Tuple[str, value_t]
            if self.tok_id != Id.J8_AnyString:
                raise AssertionError(Id_str(self.tok_id))
            k = self.decoded
            self._Next()

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

            d = NewDict()  # type: Dict[str, value_t]

            self._Next()
            if self.tok_id == Id.J8_RBrace:
                return value.Dict(d)

            k, v = self._ParsePair()
            d[k] = v

            while self.tok_id == Id.J8_Comma:
                self._Next()
                k, v = self._ParsePair()
                d[k] = v

            self._Eat(Id.J8_RBrace)

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
                b = value.Bool(self.s[self.start_pos] == 't')
                self._Next()
                return b

            elif self.tok_id == Id.J8_Int:
                part = self.s[self.start_pos:self.end_pos]
                self._Next()
                return value.Int(int(part))

            elif self.tok_id == Id.J8_Float:
                part = self.s[self.start_pos:self.end_pos]
                self._Next()
                return value.Float(float(part))

            # UString, BString too
            elif self.tok_id == Id.J8_AnyString:
                str_val = value.Str(self.decoded)
                self._Next()
                return str_val

            else:
                part = self.s[self.start_pos:self.end_pos]
                raise AssertionError('Unexpected token %s %r' %
                                     (Id_str(self.tok_id), part))

        def ParseJ8(self):
            # type: () -> value_t
            """
            Raises exception on error?
            """
            self._Next()
            return self._ParseValue()

        def ParseJson(self):
            # type: () -> value_t

            # TODO: distinguish it with flags
            return self.ParseJ8()
