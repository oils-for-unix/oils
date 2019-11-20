#!/usr/bin/env python2
"""
builtin_printf
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import (
    printf_part, #printf_part_t,
    source
)
from _devbuild.gen.types_asdl import lex_mode_e, lex_mode_t

import sys

from asdl import runtime
from core import error
from core.util import p_die, e_die
from frontend import args
from frontend import lookup
from frontend import match
from frontend import reader
from osh import builtin
from osh import state
from osh import string_ops
from osh import word_compile


PRINTF_SPEC = builtin._Register('printf')  # TODO: Don't need this?
PRINTF_SPEC.ShortFlag('-v', args.Str)


class _FormatStringParser(object):
  """
  Grammar:

    fmt           = Format_Percent Flag? Num? (Dot Num)? Type
    part          = Char_* | Format_EscapedPercent | fmt
    printf_format = part* Eof_Real   # we're using the main lexer

  Maybe: bash also supports %(strftime)T
  """
  def __init__(self, lexer):
    self.lexer = lexer

  def _Next(self, lex_mode):
    # type: (lex_mode_t) -> None
    """Set the next lex state, but don't actually read a token.

    We need this for proper interactive parsing.
    """
    self.cur_token = self.lexer.Read(lex_mode)
    self.token_type = self.cur_token.id
    self.token_kind = lookup.LookupKind(self.token_type)

  def _ParseFormatStr(self):
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
      self._Next(lex_mode_e.PrintfPercent)  # past dot
      part.precision = self.cur_token
      self._Next(lex_mode_e.PrintfPercent)

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
    self._Next(lex_mode_e.PrintfOuter)
    parts = []
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
    self.mem = mem
    self.parse_ctx = parse_ctx
    self.errfmt = errfmt
    self.parse_cache = {}  # Dict[str, printf_part]

  def __call__(self, arg_vec):
    """
    printf: printf [-v var] format [argument ...]
    """
    arg_r = args.Reader(arg_vec.strs, spids=arg_vec.spids)
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
          try:
            s = varargs[arg_index]
            word_spid = spids[arg_index]
          except IndexError:
            s = ''
            word_spid = runtime.NO_SPID

          typ = part.type.val
          if typ == 's':
            if part.precision:
              precision = int(part.precision.val)
              s = s[:precision]  # truncate
          elif typ == 'q':
            s = string_ops.ShellQuoteOneLine(s)
          elif typ in 'diouxX':
            try:
              d = int(s)
            except ValueError:
              if len(s) >= 2 and s[0] in '\'"':
                # TODO: utf-8 decode s[1:] to be more correct.  Probably
                # depends on issue #366, a utf-8 library.
                d = ord(s[1])
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
            else:
              raise AssertionError

          else:
            raise AssertionError

          if part.width:
            width = int(part.width.val)
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
          raise AssertionError

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
