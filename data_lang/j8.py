#!/usr/bin/env python2
"""
j8.py: J8 Notation and Related Utilities

Callers:

- the = operator
- write --j8 (x)
  - write --json
- read --j8 :x
  - read --json
- write --j8-str (x) calls data_lang/j8_str.py directly

TODO: Hook up CommandEvaluator, read, write


Meta-syntax:

   () is for statically typed ASDL data?

      (command.Simple blame_tok:(...) words:[ ])

   <> is for non-J8 errors?  For the = oeprator
"""

from _devbuild.gen.runtime_asdl import value, value_e, value_t

from data_lang import qsn
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, log

from typing import Optional

_ = log

from typing import cast

# Emit only JSON strings, not J8 strings
JSON_ONLY = 1 << 0

# {"key": <Dict 42> }
# for = operator
# default: raise exception
DETECT_CYCLES = 1 << 1

# {"key": (value.Slice start:3 end: 4) }
# for = operator
# default: raise exception
NON_DATA_TYPES = 1 << 2

# unicode options:
# \u \x or raw UTF8

# string prefix options
#
# "\n" or j"\n" etc.
#
# j"\u{123456}" always has the prefix?


class Printer(object):

    def __init__(self, flags, indent, max_width=0):
        # type: (int, Optional[str], int) -> None

        self.flags = flags
        # can be 2 spaces '  ', 4 spaces '    ', tab '\t',  etc. ?
        self.indent = indent
        self.max_width = max_width

        # TODO: 
        # - float format, like %.3f ?
        # - Look at what options yajl has

        # To detect cycles: by printing or by an error
        self.unique_objs = mylib.UniqueObjects()

    def Print(self, val, buf):
        # type: (value_t, mylib.BufWriter) -> None
        """
        Args:
            flags: see above
            max_width: Use ASDL algorithm for pretty printing
            indent: '  ' or '   ' or '\t', etc.?
        """
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

                # Use QSN for now
                out = qsn.encode(val.s)
                buf.write(out)

            elif case(value_e.List):
                val = cast(value.List, UP_val)

                # TODO: respect indent
                buf.write('[')
                for i, item in enumerate(val.items):
                    if i != 0:
                        buf.write(', ')

                    self.Print(item, buf)
                buf.write(']')

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)

                # TODO: respect indent
                buf.write('{')
                i = 0
                for k, v in iteritems(val.d):
                    if i != 0:
                        buf.write(', ')

                    buf.write(qsn.encode(k))
                    buf.write(': ')
                    self.Print(v, buf)

                    i += 1

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
