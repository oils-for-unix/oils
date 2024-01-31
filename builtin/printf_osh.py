#!/usr/bin/env python2
"""Builtin_printf.py."""
from __future__ import print_function

import time as time_  # avoid name conflict

from _devbuild.gen import arg_types
from _devbuild.gen.id_kind_asdl import Id, Kind, Id_t, Kind_t
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import (
    loc,
    loc_e,
    loc_t,
    source,
    Token,
    CompoundWord,
    printf_part,
    printf_part_e,
    printf_part_t,
)
from _devbuild.gen.types_asdl import lex_mode_e, lex_mode_t
from _devbuild.gen.value_asdl import (value, value_e)

from core import alloc
from core import error
from core.error import e_die, p_die
from core import state
from core import vm
from frontend import flag_spec
from frontend import consts
from frontend import lexer
from frontend import match
from frontend import reader
from mycpp import mylib
from mycpp.mylib import log
from osh import sh_expr_eval
from osh import word_compile
from data_lang import j8_lite

import posix_ as posix

from typing import Dict, List, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from core import ui
    from frontend import parse_lib

_ = log


class _FormatStringParser(object):
    """
  Grammar:

    width         = Num | Star
    precision     = Dot (Num | Star | Zero)?
    fmt           = Percent (Flag | Zero)* width? precision? (Type | Time)
    part          = Char_* | Format_EscapedPercent | fmt
    printf_format = part* Eof_Real   # we're using the main lexer

  Maybe: bash also supports %(strftime)T
  """

    def __init__(self, lexer):
        # type: (lexer.Lexer) -> None
        self.lexer = lexer

        # uninitialized values
        self.cur_token = None  # type: Token
        self.token_type = Id.Undefined_Tok  # type: Id_t
        self.token_kind = Kind.Undefined  # type: Kind_t

    def _Next(self, lex_mode):
        # type: (lex_mode_t) -> None
        """Advance a token."""
        self.cur_token = self.lexer.Read(lex_mode)
        self.token_type = self.cur_token.id
        self.token_kind = consts.GetKind(self.token_type)

    def _ParseFormatStr(self):
        # type: () -> printf_part_t
        """Fmt production."""
        self._Next(lex_mode_e.PrintfPercent)  # move past %

        part = printf_part.Percent.CreateNull(alloc_lists=True)
        while self.token_type in (Id.Format_Flag, Id.Format_Zero):
            # space and + could be implemented
            flag = lexer.TokenVal(self.cur_token)  # allocation will be cached
            if flag in '# +':
                p_die("osh printf doesn't support the %r flag" % flag,
                      self.cur_token)

            part.flags.append(self.cur_token)
            self._Next(lex_mode_e.PrintfPercent)

        if self.token_type in (Id.Format_Num, Id.Format_Star):
            part.width = self.cur_token
            self._Next(lex_mode_e.PrintfPercent)

        if self.token_type == Id.Format_Dot:
            part.precision = self.cur_token
            self._Next(lex_mode_e.PrintfPercent)  # past dot
            if self.token_type in (Id.Format_Num, Id.Format_Star,
                                   Id.Format_Zero):
                part.precision = self.cur_token
                self._Next(lex_mode_e.PrintfPercent)

        if self.token_type in (Id.Format_Type, Id.Format_Time):
            part.type = self.cur_token

            # ADDITIONAL VALIDATION outside the "grammar".
            type_val = lexer.TokenVal(part.type)  # allocation will be cached
            if type_val in 'eEfFgG':
                p_die("osh printf doesn't support floating point", part.type)
            # These two could be implemented.  %c needs utf-8 decoding.
            if type_val == 'c':
                p_die("osh printf doesn't support single characters (bytes)",
                      part.type)

        elif self.token_type == Id.Unknown_Tok:
            p_die('Invalid printf format character', self.cur_token)

        else:
            p_die('Expected a printf format character', self.cur_token)

        return part

    def Parse(self):
        # type: () -> List[printf_part_t]
        self._Next(lex_mode_e.PrintfOuter)
        parts = []  # type: List[printf_part_t]
        while True:
            if (self.token_kind == Kind.Char or
                    self.token_type == Id.Format_EscapedPercent or
                    self.token_type == Id.Unknown_Backslash):

                # Note: like in echo -e, we don't fail with Unknown_Backslash here
                # when shopt -u parse_backslash because it's at runtime rather than
                # parse time.
                # Users should use $'' or the future static printf ${x %.3f}.

                parts.append(printf_part.Literal(self.cur_token))

            elif self.token_type == Id.Format_Percent:
                parts.append(self._ParseFormatStr())

            elif self.token_type in (Id.Eof_Real, Id.Eol_Tok):
                # Id.Eol_Tok: special case for format string of '\x00'.
                break

            else:
                raise AssertionError(self.token_type)

            self._Next(lex_mode_e.PrintfOuter)

        return parts


class Printf(vm._Builtin):

    def __init__(
            self,
            mem,  # type: state.Mem
            parse_ctx,  # type: parse_lib.ParseContext
            unsafe_arith,  # type: sh_expr_eval.UnsafeArith
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.mem = mem
        self.parse_ctx = parse_ctx
        self.unsafe_arith = unsafe_arith
        self.errfmt = errfmt
        self.parse_cache = {}  # type: Dict[str, List[printf_part_t]]

        self.shell_start_time = time_.time(
        )  # this object initialized in main()

    def _Format(self, parts, varargs, locs, out):
        # type: (List[printf_part_t], List[str], List[CompoundWord], List[str]) -> int
        """Hairy printf formatting logic."""

        arg_index = 0
        num_args = len(varargs)
        backslash_c = False

        while True:  # loop over arguments
            for part in parts:  # loop over parsed format string
                UP_part = part
                if part.tag() == printf_part_e.Literal:
                    part = cast(printf_part.Literal, UP_part)
                    token = part.token
                    if token.id == Id.Format_EscapedPercent:
                        s = '%'
                    else:
                        s = word_compile.EvalCStringToken(token)
                    out.append(s)

                elif part.tag() == printf_part_e.Percent:
                    # Note: This case is very long, but hard to refactor because of the
                    # error cases and "recycling" of args!  (arg_index, return 1, etc.)
                    part = cast(printf_part.Percent, UP_part)

                    # TODO: These calculations are independent of the data, so could be
                    # cached
                    flags = []  # type: List[str]
                    if len(part.flags) > 0:
                        for flag_token in part.flags:
                            flags.append(lexer.TokenVal(flag_token))

                    width = -1  # nonexistent
                    if part.width:
                        if part.width.id in (Id.Format_Num, Id.Format_Zero):
                            width_str = lexer.TokenVal(part.width)
                            width_loc = part.width  # type: loc_t
                        elif part.width.id == Id.Format_Star:
                            if arg_index < num_args:
                                width_str = varargs[arg_index]
                                width_loc = locs[arg_index]
                                arg_index += 1
                            else:
                                width_str = ''  # invalid
                                width_loc = loc.Missing
                        else:
                            raise AssertionError()

                        try:
                            width = int(width_str)
                        except ValueError:
                            if width_loc.tag() == loc_e.Missing:
                                width_loc = part.width
                            self.errfmt.Print_("printf got invalid width %r" %
                                               width_str,
                                               blame_loc=width_loc)
                            return 1

                    precision = -1  # nonexistent
                    if part.precision:
                        if part.precision.id == Id.Format_Dot:
                            precision_str = '0'
                            precision_loc = part.precision  # type: loc_t
                        elif part.precision.id in (Id.Format_Num,
                                                   Id.Format_Zero):
                            precision_str = lexer.TokenVal(part.precision)
                            precision_loc = part.precision
                        elif part.precision.id == Id.Format_Star:
                            if arg_index < num_args:
                                precision_str = varargs[arg_index]
                                precision_loc = locs[arg_index]
                                arg_index += 1
                            else:
                                precision_str = ''
                                precision_loc = loc.Missing
                        else:
                            raise AssertionError()

                        try:
                            precision = int(precision_str)
                        except ValueError:
                            if precision_loc.tag() == loc_e.Missing:
                                precision_loc = part.precision
                            self.errfmt.Print_(
                                'printf got invalid precision %r' %
                                precision_str,
                                blame_loc=precision_loc)
                            return 1

                    if arg_index < num_args:
                        s = varargs[arg_index]
                        word_loc = locs[arg_index]  # type: loc_t
                        arg_index += 1
                        has_arg = True
                    else:
                        s = ''
                        word_loc = loc.Missing
                        has_arg = False

                    # Note: %s could be lexed into Id.Percent_S.  Although small string
                    # optimization would remove the allocation as well.
                    typ = lexer.TokenVal(part.type)
                    if typ == 's':
                        if precision >= 0:
                            s = s[:precision]  # truncate

                    elif typ == 'q':
                        # Most shells give \' for single quote, while OSH gives
                        # $'\'' this could matter when SSH'ing.
                        # Ditto for $'\\' vs. '\'

                        s = j8_lite.MaybeShellEncode(s)

                    elif typ == 'b':
                        # Process just like echo -e, except \c handling is simpler.

                        c_parts = []  # type: List[str]
                        lex = match.EchoLexer(s)
                        while True:
                            id_, tok_val = lex.Next()
                            if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
                                break

                            # Note: DummyToken is OK because EvalCStringToken() doesn't have
                            # any syntax errors.
                            tok = lexer.DummyToken(id_, tok_val)
                            p = word_compile.EvalCStringToken(tok)

                            # Unusual behavior: '\c' aborts processing!
                            if p is None:
                                backslash_c = True
                                break

                            c_parts.append(p)
                        s = ''.join(c_parts)

                    elif part.type.id == Id.Format_Time or typ in 'diouxX':
                        # %(...)T and %d share this complex integer conversion logic

                        try:
                            d = int(
                                s
                            )  # note: spaces like ' -42 ' accepted and normalized

                        except ValueError:
                            # 'a is interpreted as the ASCII value of 'a'
                            if len(s) >= 1 and s[0] in '\'"':
                                # TODO: utf-8 decode s[1:] to be more correct.  Probably
                                # depends on issue #366, a utf-8 library.
                                # Note: len(s) == 1 means there is a NUL (0) after the quote..
                                d = ord(s[1]) if len(s) >= 2 else 0

                            # No argument means -1 for %(...)T as in Bash Reference Manual
                            # 4.2 "If no argument is specified, conversion behaves as if -1
                            # had been given."
                            elif not has_arg and part.type.id == Id.Format_Time:
                                d = -1

                            else:
                                if has_arg:
                                    blame_loc = word_loc  # type: loc_t
                                else:
                                    blame_loc = part.type
                                self.errfmt.Print_(
                                    'printf expected an integer, got %r' % s,
                                    blame_loc)
                                return 1

                        if part.type.id == Id.Format_Time:
                            # Initialize timezone:
                            #   `localtime' uses the current timezone information initialized
                            #   by `tzset'.  The function `tzset' refers to the environment
                            #   variable `TZ'.  When the exported variable `TZ' is present,
                            #   its value should be reflected in the real environment
                            #   variable `TZ' before call of `tzset'.
                            #
                            # Note: unlike LANG, TZ doesn't seem to change behavior if it's
                            # not exported.
                            #
                            # TODO: In YSH, provide an API that doesn't rely on libc's global
                            # state.

                            tzcell = self.mem.GetCell('TZ')
                            if tzcell and tzcell.exported and tzcell.val.tag(
                            ) == value_e.Str:
                                tzval = cast(value.Str, tzcell.val)
                                posix.putenv('TZ', tzval.s)

                            time_.tzset()

                            # Handle special values:
                            #   User can specify two special values -1 and -2 as in Bash
                            #   Reference Manual 4.2: "Two special argument values may be
                            #   used: -1 represents the current time, and -2 represents the
                            #   time the shell was invoked." from
                            #   https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html#index-printf
                            if d == -1:  # the current time
                                ts = time_.time()
                            elif d == -2:  # the shell start time
                                ts = self.shell_start_time
                            else:
                                ts = d

                            s = time_.strftime(typ[1:-2], time_.localtime(ts))
                            if precision >= 0:
                                s = s[:precision]  # truncate

                        else:  # typ in 'diouxX'
                            # Disallowed because it depends on 32- or 64- bit
                            if d < 0 and typ in 'ouxX':
                                e_die(
                                    "Can't format negative number %d with %%%s"
                                    % (d, typ), part.type)

                            if typ == 'o':
                                s = mylib.octal(d)
                            elif typ == 'x':
                                s = mylib.hex_lower(d)
                            elif typ == 'X':
                                s = mylib.hex_upper(d)
                            else:  # diu
                                s = str(d)  # without spaces like ' -42 '

                            # There are TWO different ways to ZERO PAD, and they differ on
                            # the negative sign!  See spec/builtin-printf

                            zero_pad = 0  # no zero padding
                            if width >= 0 and '0' in flags:
                                zero_pad = 1  # style 1
                            elif precision > 0 and len(s) < precision:
                                zero_pad = 2  # style 2

                            if zero_pad:
                                negative = (s[0] == '-')
                                if negative:
                                    digits = s[1:]
                                    sign = '-'
                                    if zero_pad == 1:
                                        # [%06d] -42 becomes [-00042] (6 TOTAL)
                                        n = width - 1
                                    else:
                                        # [%6.6d] -42 becomes [-000042] (1 for '-' + 6)
                                        n = precision
                                else:
                                    digits = s
                                    sign = ''
                                    if zero_pad == 1:
                                        n = width
                                    else:
                                        n = precision
                                s = sign + digits.rjust(n, '0')

                    else:
                        raise AssertionError()

                    if width >= 0:
                        if '-' in flags:
                            s = s.ljust(width, ' ')
                        else:
                            s = s.rjust(width, ' ')

                    out.append(s)

                else:
                    raise AssertionError()

                if backslash_c:  # 'printf %b a\cb xx' - \c terminates processing!
                    break

            if arg_index == 0:
                # We went through ALL parts and didn't consume ANY arg.
                # Example: print x y
                break
            if arg_index >= num_args:
                # We printed all args
                break
            # There are more arg: Implement the 'arg recycling' behavior.

        return 0

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        """
    printf: printf [-v var] format [argument ...]
    """
        attrs, arg_r = flag_spec.ParseCmdVal('printf', cmd_val)
        arg = arg_types.printf(attrs.attrs)

        fmt, fmt_loc = arg_r.ReadRequired2('requires a format string')
        varargs, locs = arg_r.Rest2()

        #log('fmt %s', fmt)
        #log('vals %s', vals)

        arena = self.parse_ctx.arena
        if fmt in self.parse_cache:
            parts = self.parse_cache[fmt]
        else:
            line_reader = reader.StringLineReader(fmt, arena)
            # TODO: Make public
            lexer = self.parse_ctx.MakeLexer(line_reader)
            parser = _FormatStringParser(lexer)

            with alloc.ctx_SourceCode(arena,
                                      source.ArgvWord('printf', fmt_loc)):
                try:
                    parts = parser.Parse()
                except error.Parse as e:
                    self.errfmt.PrettyPrintError(e)
                    return 2  # parse error

            self.parse_cache[fmt] = parts

        if 0:
            print()
            for part in parts:
                part.PrettyPrint()
                print()

        out = []  # type: List[str]
        status = self._Format(parts, varargs, locs, out)
        if status != 0:
            return status  # failure

        result = ''.join(out)
        if arg.v is not None:
            # TODO: get the location for arg.v!
            v_loc = loc.Missing
            lval = self.unsafe_arith.ParseLValue(arg.v, v_loc)
            state.BuiltinSetValue(self.mem, lval, value.Str(result))
        else:
            mylib.Stdout().write(result)
        return 0
