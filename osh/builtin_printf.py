#!/usr/bin/env python2
"""
builtin_printf
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.runtime_asdl import cmd_value__Argv, value_e, value__Str
from _devbuild.gen.syntax_asdl import (
    printf_part, printf_part_t,
    source,
)
from _devbuild.gen.types_asdl import lex_mode_e, lex_mode_t

import sys
import time

from asdl import runtime
from core import error
from qsn_ import qsn
from core import state
from core.util import p_die, e_die
from frontend import args
from frontend import arg_def
from frontend import consts
from frontend import match
from frontend import reader
from mycpp import mylib
from osh import word_compile

import posix_ as posix

from typing import Dict, List, TYPE_CHECKING, cast

if TYPE_CHECKING:
  from frontend.lexer import Lexer
  from frontend.parse_lib import ParseContext
  from core.state import Mem
  from core.ui import ErrorFormatter


if mylib.PYTHON:
  PRINTF_SPEC = arg_def.Register('printf')  # TODO: Don't need this?
  PRINTF_SPEC.ShortFlag('-v', args.Str)

shell_start_time = time.time()

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
    # type: (Lexer) -> None
    self.lexer = lexer

  def _Next(self, lex_mode):
    # type: (lex_mode_t) -> None
    """Set the next lex state, but don't actually read a token.

    We need this for proper interactive parsing.
    """
    self.cur_token = self.lexer.Read(lex_mode)
    self.token_type = self.cur_token.id
    self.token_kind = consts.GetKind(self.token_type)

  def _ParseFormatStr(self):
    # type: () -> printf_part_t
    self._Next(lex_mode_e.PrintfPercent)  # move past %

    part = printf_part.Percent()
    while self.token_type in (Id.Format_Flag, Id.Format_Zero):
      # space and + could be implemented
      flag = self.cur_token.val
      if flag in '# +':
        p_die("osh printf doesn't support the %r flag", flag, token=self.cur_token)

      part.flags.append(self.cur_token)
      self._Next(lex_mode_e.PrintfPercent)

    if self.token_type in (Id.Format_Num, Id.Format_Star):
      part.width = self.cur_token
      self._Next(lex_mode_e.PrintfPercent)

    if self.token_type == Id.Format_Dot:
      part.precision = self.cur_token
      self._Next(lex_mode_e.PrintfPercent)  # past dot
      if self.token_type in (Id.Format_Num, Id.Format_Star, Id.Format_Zero):
        part.precision = self.cur_token
        self._Next(lex_mode_e.PrintfPercent)

    if self.token_type in (Id.Format_Type, Id.Format_Time):
      part.type = self.cur_token

      # ADDITIONAL VALIDATION outside the "grammar".
      if part.type.val in 'eEfFgG':
        p_die("osh printf doesn't support floating point", token=part.type)
      # These two could be implemented.  %c needs utf-8 decoding.
      if part.type.val == 'c':
        p_die("osh printf doesn't support single characters (bytes)", token=part.type)

    else:
      if self.cur_token.val:
        msg = 'Invalid printf format character'
      else:  # for printf '%'
        msg = 'Expected a printf format character'
      p_die(msg, token=self.cur_token)

    # Do this check AFTER the floating point checks
    if part.precision and part.type.val[-1] not in 'fsT':
      p_die("precision can't be specified when here",
            token=part.precision)

    return part

  def Parse(self):
    # type: () -> List[printf_part_t]
    self._Next(lex_mode_e.PrintfOuter)
    parts = []  # type: List[printf_part_t]
    while True:
      if (self.token_kind == Kind.Char or
          self.token_type == Id.Format_EscapedPercent):

        # TODO: Could handle Char_BadBackslash.
        # Maybe make that a different kind?

        parts.append(printf_part.Literal(self.cur_token))

      elif self.token_type == Id.Format_Percent:
        parts.append(self._ParseFormatStr())

      elif self.token_type == Id.Eof_Real:
        break

      else:
        p_die('Invalid token %r', token=self.cur_token)

      self._Next(lex_mode_e.PrintfOuter)

    return parts


class Printf(object):

  def __init__(self, mem, parse_ctx, errfmt):
    # type: (Mem, ParseContext, ErrorFormatter) -> None
    self.mem = mem
    self.parse_ctx = parse_ctx
    self.errfmt = errfmt
    self.parse_cache = {}  # type: Dict[str, List[printf_part_t]]

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    """
    printf: printf [-v var] format [argument ...]
    """
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip argv[0]
    arg, _ = PRINTF_SPEC.Parse(arg_r)

    fmt, fmt_spid = arg_r.ReadRequired2('requires a format string')
    varargs, spids = arg_r.Rest2()

    #log('fmt %s', fmt)
    #log('vals %s', vals)

    arena = self.parse_ctx.arena
    if fmt in self.parse_cache:
      parts = self.parse_cache[fmt]
    else:
      line_reader = reader.StringLineReader(fmt, arena)
      # TODO: Make public
      lexer = self.parse_ctx._MakeLexer(line_reader)
      p = _FormatStringParser(lexer)
      arena.PushSource(source.ArgvWord(fmt_spid))
      try:
        parts = p.Parse()
      except error.Parse as e:
        self.errfmt.PrettyPrintError(e)
        return 2  # parse error
      finally:
        arena.PopSource()

      self.parse_cache[fmt] = parts

    if 0:
      print()
      for part in parts:
        part.PrettyPrint()
        print()

    out = []
    arg_index = 0
    num_args = len(varargs)
    backslash_c = False

    while True:
      for part in parts:
        if isinstance(part, printf_part.Literal):
          token = part.token
          if token.id == Id.Format_EscapedPercent:
            s = '%'
          else:
            s = word_compile.EvalCStringToken(token.id, token.val)
          out.append(s)

        elif isinstance(part, printf_part.Percent):
          flags = None
          if len(part.flags) > 0:
            flags = ''
            for flag_token in part.flags:
              flags += flag_token.val

          width = None
          if part.width:
            if part.width.id in (Id.Format_Num, Id.Format_Zero):
              width = part.width.val
              width_spid = part.width.span_id
            elif part.width.id == Id.Format_Star:
              if arg_index < num_args:
                width = varargs[arg_index]
                width_spid = spids[arg_index]
                arg_index += 1
              else:
                width = ''
                width_spid = runtime.NO_SPID
            else:
              raise AssertionError()

            try:
              width = int(width)
            except ValueError:
              if width_spid == runtime.NO_SPID:
                width_spid = part.width.span_id
              self.errfmt.Print("printf got invalid number %r for the width", s,
                                span_id = width_spid)
              return 1

          precision = None
          if part.precision:
            if part.precision.id == Id.Format_Dot:
              precision = '0'
              precision_spid = part.precision.span_id
            elif part.precision.id in (Id.Format_Num, Id.Format_Zero):
              precision = part.precision.val
              precision_spid = part.precision.span_id
            elif part.precision.id == Id.Format_Star:
              if arg_index < num_args:
                precision = varargs[arg_index]
                precision_spid = spids[arg_index]
                arg_index += 1
              else:
                precision = ''
                precision_spid = runtime.NO_SPID
            else:
              raise AssertionError()

            try:
              precision = int(precision)
            except ValueError:
              if precision_spid == runtime.NO_SPID:
                precision_spid = part.precision.span_id
              self.errfmt.Print("printf got invalid number %r for the precision", s,
                                span_id = precision_spid)
              return 1

          if arg_index < num_args:
            s = varargs[arg_index]
            word_spid = spids[arg_index]
            arg_index += 1
          else:
            s = ''
            word_spid = runtime.NO_SPID

          typ = part.type.val
          if typ == 's':
            if precision is not None:
              s = s[:precision]  # truncate

          elif typ == 'q':
            s = qsn.maybe_shell_encode(s)

          elif typ == 'b':
            # Process just like echo -e, except \c handling is simpler.

            parts = []  # type: List[str]
            lex = match.EchoLexer(s)
            while True:
              id_, value = lex.Next()
              if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
                break

              p = word_compile.EvalCStringToken(id_, value)

              # Unusual behavior: '\c' aborts processing!
              if p is None:
                backslash_c = True
                break

              parts.append(p)
            s = ''.join(parts)

          elif typ in 'diouxX' or part.type.id == Id.Format_Time:
            try:
              d = int(s)
            except ValueError:
              if len(s) >= 2 and s[0] in '\'"':
                # TODO: utf-8 decode s[1:] to be more correct.  Probably
                # depends on issue #366, a utf-8 library.
                d = ord(s[1])
              elif part.type.id == Id.Format_Time and len(s) == 0 and word_spid == runtime.NO_SPID:
                # Note: No argument means -1 for %(...)T as in Bash Reference
                #   Manual 4.2 "If no argument is specified, conversion behaves
                #   as if -1 had been given."
                d = -1
              else:
                # This works around the fact that in the arg recycling case, you have no spid.
                if word_spid == runtime.NO_SPID:
                  self.errfmt.Print("printf got invalid number %r for this substitution", s,
                                    span_id=part.type.span_id)
                else:
                  self.errfmt.Print("printf got invalid number %r", s,
                                    span_id=word_spid)

                return 1

            if typ in 'di':
              s = str(d)
            elif typ in 'ouxX':
              if d < 0:
                e_die("Can't format negative number %d with %%%s",
                      d, typ, span_id=part.type.span_id)
              if typ == 'u':
                s = str(d)
              elif typ == 'o':
                s = '%o' % d
              elif typ == 'x':
                s = '%x' % d
              elif typ == 'X':
                s = '%X' % d
            elif part.type.id == Id.Format_Time:
              # %(...)T

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
              # TODO: In Oil, provide an API that doesn't rely on libc's
              # global state.

              tzcell = self.mem.GetCell('TZ')
              if tzcell and tzcell.exported and tzcell.val.tag_() == value_e.Str:
                tzval = cast(value__Str, tzcell.val)
                posix.putenv('TZ', tzval.s)

              time.tzset()

              # Handle special values:
              #   User can specify two special values -1 and -2 as in Bash
              #   Reference Manual 4.2: "Two special argument values may be
              #   used: -1 represents the current time, and -2 represents the
              #   time the shell was invoked." from
              #   https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html#index-printf
              if d == -1: # the current time
                d = time.time()
              elif d == -2: # the shell start time
                d = shell_start_time

              s = time.strftime(typ[1:-2], time.localtime(d))
              if precision is not None:
                s = s[:precision]  # truncate

            else:
              raise AssertionError()

          else:
            raise AssertionError()

          if width is not None:
            if flags:
              if '-' in flags:
                s = s.ljust(width, ' ')
              elif '0' in flags:
                s = s.rjust(width, '0')
              else:
                pass
            else:
              s = s.rjust(width, ' ')

          out.append(s)

        else:
          raise AssertionError()

        if backslash_c:  # 'printf %b a\cb xx' - \c terminates processing!
          break

      if arg_index >= num_args:
        break
      # Otherwise there are more args.  So cycle through the loop once more to
      # implement the 'arg recycling' behavior.

    result = ''.join(out)
    if arg.v:
      var_name = arg.v

      # Notes:
      # - bash allows a[i] here (as in unset and ${!x}), but we haven't
      # implemented it.
      # - TODO: get the span_id for arg.v!
      if not match.IsValidVarName(var_name):
        raise args.UsageError('got invalid variable name %r' % var_name)
      state.SetStringDynamic(self.mem, var_name, result)
    else:
      sys.stdout.write(result)
    return 0
