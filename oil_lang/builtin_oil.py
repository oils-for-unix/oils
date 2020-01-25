#!/usr/bin/env python2
"""
builtin_oil.py - Oil builtins.

See rfc/0024-oil-builtins.md for notes.

env: Should be in builtin_compat.py?

It's sort of like xargs too.
"""
from __future__ import print_function

import sys

from _devbuild.gen.runtime_asdl import value, value_e, scope_e
from _devbuild.gen.syntax_asdl import sh_lhs_expr

from core.util import log
from frontend import args
from frontend import match
from osh import builtin  # ReadLineFromStdin
from mycpp.mylib import tagswitch

import yajl
import posix_


class _Builtin(object):
  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt


class Repr(_Builtin):
  """Given a list of variable names, print their values.

  'repr a' is a lot easier to type than 'argv.py "${a[@]}"'.
  """
  def __call__(self, cmd_val):
    status = 0
    for i in xrange(1, len(cmd_val.argv)):
      name = cmd_val.argv[i]
      if name.startswith(':'):
        name = name[1:]

      if not match.IsValidVarName(name):
        raise args.UsageError('got invalid variable name %r' % name,
                              span_id=cmd_val.arg_spids[i])

      cell = self.mem.GetCell(name)
      if cell is None:
        self.errfmt.Print("Couldn't find a variable named %r" % name,
                          span_id=cmd_val.arg_spids[i])
        status = 1
      else:
        sys.stdout.write('%s = ' % name)
        cell.PrettyPrint()  # may be color
        sys.stdout.write('\n')
    return status


class Append(_Builtin):
  """Append to a string.
  
  The newer version of foo+='suffix'
  """


class Push(_Builtin):
  """Push args onto an array.

  Note: this could also be in builtins_pure.py?
  """
  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'push'

    var_name, var_spid = arg_r.ReadRequired2(
        'requires a variable name')

    if var_name.startswith(':'):  # optional : sigil
      var_name = var_name[1:]

    if not match.IsValidVarName(var_name):
      raise args.UsageError('got invalid variable name %r' % var_name,
                            span_id=var_spid)

    val = self.mem.GetVar(var_name)
    # TODO: value.Obj too
    if val.tag != value_e.MaybeStrArray:
      self.errfmt.Print("%r isn't an array", var_name, span_id=var_spid)
      return 1

    val.strs.extend(arg_r.Rest())
    return 0


class Use(_Builtin):
  """use lib, bin, env.  Respects namespaces.

  use lib foo.sh {  # "punning" on block syntax.  1 or 3 words.
    func1
    func2 as myalias
  }
  """
  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'use'

    # TODO:
    # - Does shopt -s namespaces have to be on?
    #   - I don't think so?  It only affects 'procs', not funcs.

    arg = arg_r.Peek()

    # 'use bin' and 'use env' are for static analysis.  No-ops at runtime.
    if arg in ('bin', 'env'):
      return 0

    if arg == 'lib':  # OPTIONAL lib
      arg_r.Next()

    # Cosmetic: separator for 'use bin __ grep sed'.  Allowed for 'lib' to be
    # consistent.
    arg = arg_r.Peek()
    if arg == '__':  # OPTIONAL __
      arg_r.Next()

    # Now import everything.
    rest = arg_r.Rest()
    for path in rest:
      log('path %s', path)

    return 0


class Env(_Builtin):
  """env {} blocks are preferred over 'export'.

  Should be compatible with POSIX, but also take a block.
  """
  pass


class Fork(_Builtin):
  """Replaces &.  Takes a block.

  Similar to Wait, which is in osh/builtin_process.py.
  """
  pass


class Opts(_Builtin):
  """getopts replacement.

  opts :grep_opts {
    flag -v --invert Bool "Invert"
    flag -A --after Int "Lines after"
    flag -t --timeout Float "Seconds to wait" { default = 1.0 }

    # / pattern file* /
    arg 1 pattern "Regular expression"
    arg 2- file "Regular expression"
  }
  var opt = grep_opts.Parse(ARGV)
  opt.invert
  opt.after
  opt.pattern
  opt.file
  """
  def __call__(self, cmd_val):
    raise NotImplementedError


JSON_WRITE_SPEC = args.OilFlags()
JSON_WRITE_SPEC.Flag('-pretty', args.Bool, default=True,
                     help='Whitespace in output (default true)')
JSON_WRITE_SPEC.Flag('-indent', args.Int, default=2,
                     help='Indent JSON by this amount')

JSON_READ_SPEC = args.OilFlags()
# yajl has this option
JSON_READ_SPEC.Flag('-validate', args.Bool, default=True,
                     help='Validate UTF-8')

_JSON_ACTION_ERROR = "builtin expects 'read' or 'write'"

class Json(object):
  """Json I/O.

  -indent pretty prints it.  Is the default indent 2?  -pretty=0 can turn it
  off.

  json echo :myobj

  json echo -indent 2 :myobj :other_obj {
    x = 1
    d = {name: 'andy'}
  }

  json read :x < foo.tsv2

  How about:
      json echo &myobj 
  Well that will get confused with a redirect.
  """
  def __init__(self, mem, ex, errfmt):
    self.mem = mem
    self.ex = ex
    self.errfmt = errfmt

  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'json'

    action, action_spid = arg_r.Peek2()
    if action is None:
      raise args.UsageError(_JSON_ACTION_ERROR)
    arg_r.Next()

    if action == 'write':
      arg, _ = JSON_WRITE_SPEC.Parse(arg_r)

      # GetVar() of each name and print it.

      for var_name in arg_r.Rest():
        if var_name.startswith(':'):
          var_name = var_name[1:]

        val = self.mem.GetVar(var_name)
        with tagswitch(val) as case:
          if case(value_e.Undef):
            # TODO: blame the right span_id
            self.errfmt.Print("no variable named %r is defined", var_name)
            return 1
          elif case(value_e.Str):
            obj = val.s
          elif case(value_e.MaybeStrArray):
            obj = val.strs
          elif case(value_e.AssocArray):
            obj = val.d
          elif case(value_e.Obj):
            obj = val.obj
          else:
            raise AssertionError(val)

        if arg.pretty:
          indent = arg.indent 
          extra_newline = False
        else:
          # How yajl works: if indent is -1, then everything is on one line.
          indent = -1
          extra_newline = True

        j = yajl.dump(obj, sys.stdout, indent=indent)
        if extra_newline:
          sys.stdout.write('\n')

      # TODO: Accept a block.  They aren't hooked up yet.
      if cmd_val.block:
        # TODO: flatten value.{Str,Obj} into a flat dict?
        namespace = self.ex.EvalBlock(cmd_val.block)

        print(yajl.dump(namespace))

    elif action == 'read':
      arg, _ = JSON_READ_SPEC.Parse(arg_r)
      # TODO:
      # Respect -validate=F

      var_name, name_spid = arg_r.ReadRequired2("expected variable name")
      if var_name.startswith(':'):
        var_name = var_name[1:]

      if not match.IsValidVarName(var_name):
        raise args.UsageError('got invalid variable name %r' % var_name,
                              span_id=name_spid)

      # Have to use this over sys.stdin because of redirects
      # TODO: change binding to yajl.readfd() ?
      stdin = posix_.fdopen(0)
      try:
        obj = yajl.load(stdin)
      except ValueError as e:
        self.errfmt.Print('json read: %s', e, span_id=action_spid)
        return 1

      self.mem.SetVar(
          sh_lhs_expr.Name(var_name), value.Obj(obj), (), scope_e.LocalOnly)

    else:
      raise args.UsageError(_JSON_ACTION_ERROR, span_id=action_spid)

    return 0


WRITE_SPEC = args.OilFlags()
WRITE_SPEC.Flag('-sep', args.Str, default='\n',
                    help='Characters to separate each argument')
WRITE_SPEC.Flag('-end', args.Str, default='\n',
                    help='Characters to terminate the whole invocation')
WRITE_SPEC.Flag('-n', args.Bool, default=False,
                    help="Omit newline (synonym for -end '')")


class Write(_Builtin):
  """
  write -- @strs
  write --sep ' ' --end '' -- @strs
  write -n -- @
  write --cstr -- @strs   # argv serialization
  write --cstr --sep $'\t' -- @strs   # this is like TSV2!
  """
  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()  # skip 'echo'

    arg, _ = WRITE_SPEC.Parse(arg_r)
    #print(arg)

    i = 0
    while not arg_r.AtEnd():
      if i != 0:
        sys.stdout.write(arg.sep)
      s = arg_r.Peek()
      sys.stdout.write(s)
      arg_r.Next()
      i += 1

    if arg.n:
      pass
    elif arg.end:
      sys.stdout.write(arg.end)

    return 0


GETLINE_SPEC = args.OilFlags()
GETLINE_SPEC.Flag('-cstr', args.Bool,
                    help='Decode the line in CSTR format')
GETLINE_SPEC.Flag('-end', args.Bool, default=False,
                    help='Whether to return the trailing newline, if any')

class Getline(_Builtin):
  """
  getline :mystr
  getline --cstr :mystr  # better version of read -r

  What if there are multiple vars?  Try TSV2 then?
  """
  def __call__(self, cmd_val):
    arg_r = args.Reader(cmd_val.argv, spids=cmd_val.arg_spids)
    arg_r.Next()
    arg, _ = GETLINE_SPEC.Parse(arg_r)
    if arg.cstr:
      # TODO: implement it
      # returns error if it can't decode
      raise NotImplementedError()

    var_name, var_spid = arg_r.ReadRequired2(
        'requires a variable name')

    if var_name.startswith(':'):  # optional : sigil
      var_name = var_name[1:]

    next_arg, next_spid = arg_r.Peek2()
    if next_arg is not None:
      raise args.UsageError('got extra argument', span_id=next_spid)

    # TODO: use a more efficient function in C
    line = builtin.ReadLineFromStdin()
    if not line:  # EOF
      return 1

    if not arg.end:
      if line.endswith('\r\n'):
        line = line[:-2]
      elif line.endswith('\n'):
        line = line[:-1]

    self.mem.SetVar(
        sh_lhs_expr.Name(var_name), value.Str(line), (), scope_e.LocalOnly)
    return 0


class Tsv2(_Builtin):
  """TSV2 I/O.

  # Takes a block.
  tsv2 echo :var1 :var2 {
    # Does this make sense?
    x = @(a b c)
    age = @[1 2 3]
  }

  tsv2 read :x < foo.tsv2
  """
  pass
