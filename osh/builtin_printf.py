#!/usr/bin/env python2
"""
builtin_printf
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.runtime_asdl import cmd_value__Argv, value_e, value__Str
from _devbuild.gen.syntax_asdl import (
    printf_part, printf_part_t,
    source, Token
)
from _devbuild.gen.types_asdl import lex_mode_e, lex_mode_t

import sys
import time
import os

from asdl import runtime
from core import error
from core import state
from core.util import p_die, e_die
from frontend import args
from frontend import arg_def
from frontend import consts
from frontend import match
from frontend import reader
from mycpp import mylib
from osh import string_ops
from osh import word_compile

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

    fmt           = Format_Percent Flag? Num? (Dot Num)? Type
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
    if self.token_type == Id.Format_Flag:
      part.flag = self.cur_token
      self._Next(lex_mode_e.PrintfPercent)

      # space and + could be implemented
      flag = part.flag.val
      if flag in '# +':
        p_die("osh printf doesn't support the %r flag", flag, token=part.flag)

    if self.token_type == Id.Format_Num:
      part.width = self.cur_token
      self._Next(lex_mode_e.PrintfPercent)

    if self.token_type == Id.Format_Dot:
      dot_spid = self.cur_token.span_id
      self._Next(lex_mode_e.PrintfPercent)  # past dot
      if self.token_type == Id.Format_Num or self.cur_token.val == '0':
        part.precision = self.cur_token
        self._Next(lex_mode_e.PrintfPercent)
      else:
        part.precision = Token(Id.Format_Num, dot_spid, '0')

    if self.token_type == Id.Format_Type:
      part.type = self.cur_token

      # ADDITIONAL VALIDATION outside the "grammar".
      if part.type.val in 'eEfFgG':
        p_die("osh printf doesn't support floating point", token=part.type)
      # These two could be implemented.  %c needs utf-8 decoding.
      if part.type.val == 'b':
        p_die("osh printf doesn't support backslash escaping (try $'\\n')", token=part.type)
      if part.type.val == 'c':
        p_die("osh printf doesn't support single characters (bytes)", token=part.type)

    else:
      if self.cur_token.val:
        msg = 'Invalid printf format character'
      else:  # for printf '%'
        msg = 'Expected a printf format character'
      p_die(msg, token=self.cur_token)

    # Do this check AFTER the floating point checks
    if part.precision and part.type.val not in 'fs':
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
          width = None
          if part.width:
            if part.width.val != '*':
              width = part.width.val
              width_spid = part.width.span_id
            elif arg_index < num_args:
              width = varargs[arg_index]
              width_spid = spids[arg_index]
              arg_index += 1
            else:
              width = ''
              width_spid = runtime.NO_SPID

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
            if part.precision.val != '*':
              precision = part.precision.val
              precision_spid = part.precision.span_id
            elif arg_index < num_args:
              precision = varargs[arg_index]
              precision_spid = spids[arg_index]
              arg_index += 1
            else:
              precision = ''
              precision_spid = runtime.NO_SPID

            try:
              precision = int(precision)
            except ValueError:
              if precision_spid == runtime.NO_SPID:
                precision_spid = part.precision.span_id
              self.errfmt.Print("printf got invalid number %r for the precision", s,
                                span_id = precision_spid)
              return 1

          try:
            s = varargs[arg_index]
            word_spid = spids[arg_index]
          except IndexError:
            s = ''
            word_spid = runtime.NO_SPID

          typ = part.type.val
          if typ == 's':
            if precision is not None:
              s = s[:precision]  # truncate
          elif typ == 'q':
            s = string_ops.ShellQuoteOneLine(s)
          elif typ in 'diouxX' or typ.endswith('T'):
            try:
              d = int(s)
            except ValueError:
              if len(s) >= 2 and s[0] in '\'"':
                # TODO: utf-8 decode s[1:] to be more correct.  Probably
                # depends on issue #366, a utf-8 library.
                d = ord(s[1])
              elif len(s) == 0 and typ.endswith('T'):
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
            elif typ.endswith('T'):
              # set timezone
              tzcell = self.mem.GetCell('TZ')
              if tzcell and tzcell.exported and tzcell.val.tag_() == value_e.Str:
                tzval = cast(value__Str, tzcell.val)
                os.environ['TZ'] = tzval.s
              elif 'TZ' in os.environ:
                del os.environ['TZ']
              time.tzset()

              if d == -1: # now
                d = None
              elif d == -2: # shell start time
                d = shell_start_time
              s = time.strftime(typ[1:-2], time.localtime(d));

            else:
              raise AssertionError()

          else:
            raise AssertionError()

          if width is not None:
            if part.flag:
              flag = part.flag.val
              if flag == '-':
                s = s.ljust(width, ' ')
              elif flag == '0':
                s = s.rjust(width, '0')
              else:
                pass
            else:
              s = s.rjust(width, ' ')

          out.append(s)
          arg_index += 1

        else:
          raise AssertionError()

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
