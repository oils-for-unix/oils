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

from _devbuild.gen.runtime_asdl import value, value_e, value_t

from asdl import format as fmt
from data_lang import qsn
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, log

from typing import Optional

_ = log

from typing import cast


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

        # To detect cycles: by printing or by an error
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

        self.compact = False

        # To detect cycles: by printing or by an error
        self.unique_objs = mylib.UniqueObjects()

        self.spaces = {0: ''}  # Dic

    def _GetIndent(self, i):
        if not i in self.spaces:
            self.spaces[i] = i * ' '
        return self.spaces[i]

    def Print(self, val, buf, indent, level=0):
        # type: (value_t, mylib.BufWriter, int, int) -> None
        """
        Args:
          indent: number of spaces, or -1 for everything on one line
        """
        #log('indent %r level %d', indent, level)

        bracket_indent = self._GetIndent(level * indent)
        item_indent = self._GetIndent((level + 1) * indent)

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Null):
                buf.write('null')

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                buf.write('true' if val.b else 'false')

            elif case(value_e.Int):
                val = cast(value.Int, UP_val)
                # TODO: buf.write_int() would avoid allocation
                buf.write(str(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)

                # TODO: buf.write_float() would avoid allocation
                buf.write(str(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)

                buf.write('"')
                valid_utf8 = qsn.EncodeRunes(val.s, qsn.BIT8_UTF8, buf)

                # TODO: check errors
                # Is it possible to have invalid UTF-8 but valid JSON?
                # Surrogate pairs?
                if not valid_utf8:
                    pass

                buf.write('"')

            elif case(value_e.List):
                val = cast(value.List, UP_val)

                if self.compact:
                    buf.write('[')
                    for i, item in enumerate(val.items):
                        if i != 0:
                            buf.write(', ')

                        self.Print(item, buf, indent, level+1)
                    buf.write(']')
                else:
                    buf.write('[\n')
                    for i, item in enumerate(val.items):
                        if i != 0:
                            buf.write(',\n')

                        buf.write(item_indent)
                        self.Print(item, buf, indent, level+1)
                    buf.write('\n')

                    buf.write(bracket_indent)
                    buf.write(']')

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)

                if self.compact:
                    buf.write('{')
                    i = 0
                    for k, v in iteritems(val.d):
                        if i != 0:
                            buf.write(', ')

                        buf.write('"')
                        valid_utf8 = qsn.EncodeRunes(k, qsn.BIT8_UTF8, buf)
                        # TODO: check errors
                        if not valid_utf8:
                            pass
                        buf.write('": ')
                        self.Print(v, buf, indent, level+1)

                        i += 1
                    buf.write('}')

                else:
                    buf.write('{\n')
                    i = 0
                    for k, v in iteritems(val.d):
                        if i != 0:
                            buf.write(',\n')

                        buf.write(item_indent)
                        buf.write('"')
                        valid_utf8 = qsn.EncodeRunes(k, qsn.BIT8_UTF8, buf)
                        # TODO: check errors
                        if not valid_utf8:
                            pass
                        buf.write('": ')

                        self.Print(v, buf, indent, level+1)

                        i += 1

                    buf.write('\n')

                    buf.write(bracket_indent)
                    buf.write('}')

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
