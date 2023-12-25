#!/usr/bin/env python2
"""
j8.py: J8 Notation and Related Utilities

Callers:

- the = operator
- write (x)
  - Flags --lines --j8 --json
- read --j8 :x
  - read --json

TODO:

- PrettyPrinter uses hnode.asdl?
- Harmonize the API in data_lang/qsn.py 
  - use mylib.BufWriter output
  - use u_style.LiteralUtf8 instead of BIT8_UTF8, etc.

- QSN maybe_shell_encode() is used for bash features
  - Remove shell_compat which does \\x00 instead of \\0


Meta-syntax:

   () is for statically typed ASDL data?

      (command.Simple blame_tok:(...) words:[ ])

   <> is for non-J8 errors?  For the = oeprator
"""

from _devbuild.gen.value_asdl import (value, value_e, value_t)

from asdl import format as fmt
from core import vm
from data_lang import pyj8
from data_lang import qsn
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, log

_ = log
unused = pyj8

from typing import cast, Dict


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


class Printer(object):
    """
    For write --j8 (x) .  Output to monomorphic mylib.BufWriter.

    Options:
    - Control over escaping: \\u \\x raw UTF-8
    - Control over j prefix: when necessary, or always
    - Control over strict JSON subset (--json vs --j8)
    - Dumb indentation, not smart line wrapping

    Maybe:
    - float format, like %.3f ?

    Fixed behavior:
    - Always fails on cycles
    - Always on non-data types

    Conflict:

    $ write -- foo bar j"\n"
    foo
    bar
    <raw newline>

    $ write --j8 foo bar j"\n"
    "foo"
    "bar"
    j"\n"

    # I guess this makes sense?  lines are escaped?
    $ write --lines foo bar j"\n"
    foo   # unquoted
    bar
    j"\n"

    # inverse is read --line --j8 or read --lines j8

    # One per line
    $ write ({k: "v"}, [2, 3])
    {"k": "v"}
    [2, 3]
    """

    def __init__(self, options):
        # type: (int) -> None
        """
        Args:
          # These can all be packed into the same byte.  ASDL needs bit_set
          # support I think?
          options:
            j_prefix.WhenJ8  # default,  
            j_prefix.Always  # when do we need this?

            u_style.LiteralUtf8         # raw or \\x
            u_style.UEscape      # \\u{} or \\x
            u_style.XEscapeOnly  # always \\x escape, NO DECODING
            u_style.JsonEscape   # \\u1234 only - Implement LAST

            dialect.J8  # default
            dialect.Json

            pretty.UnquotedKeys - ASDL uses this?

          indent: if None, then we print everything on one line
        """
        self.options = options

        # This could be an optimized set an C++ bit set like mark_sweep_heap.h,
        # rather than a Dict
        self.unique_objs = mylib.UniqueObjects()
        self.spaces = {0: ''}  # cache of strings with spaces

    def Print(self, val, buf, indent):
        # type: (value_t, mylib.BufWriter, int) -> None
        """
        Args:
          indent: number of spaces to indent, or -1 for everything on one line
        """
        p = InstancePrinter(buf, indent, self.options, self.spaces)
        p.Print(val)


class InstancePrinter(object):

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

        self.buf.write('"')
        valid_utf8 = qsn.EncodeRunes(s, qsn.BIT8_UTF8, self.buf)

        # TODO: check errors
        # Is it possible to have invalid UTF-8 but valid JSON?
        # Surrogate pairs?
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
                # TODO: buf.write_int() would avoid allocation
                self.buf.write(str(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)

                # TODO: buf.write_float() would avoid allocation
                self.buf.write(str(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)

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
                # Print statically typed () depending on flags
                # Or <> for invalid
                pass


class Parser(object):

    def Parse(self, s):
        # type: (str) -> value_t
        """
        Raises exception on error?

        - Can parse either J8 or JSON strings

        """
        # TODO: feed it to lexer first, then parser
        return None
