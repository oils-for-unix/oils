# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
state.py - Interpreter state
"""
from __future__ import print_function

import cStringIO

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import sh_lhs_expr
from _devbuild.gen.runtime_asdl import (
    value, value_e, lvalue_e, scope_e, var_flags_e, value__Str
)
from _devbuild.gen import runtime_asdl  # for cell

from asdl import runtime
from core.util import log, e_die
from frontend import args
from osh import split
from pylib import os_path
from pylib import path_stat

import libc
import posix_ as posix

from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.id_kind_asdl import Id_t
    from _devbuild.gen.runtime_asdl import lvalue_t, value_t, scope_t, var_flags_t


# This was derived from bash --norc -c 'argv "$COMP_WORDBREAKS".
# Python overwrites this to something Python-specific in Modules/readline.c, so
# we have to set it back!
# Used in both core/competion.py and osh/state.py
_READLINE_DELIMS = ' \t\n"\'><=;|&(:'


class SearchPath(object):
  """For looking up files in $PATH."""

  def __init__(self, mem):
    # type: (Mem) -> None
    self.mem = mem
    self.cache = {}

  def Lookup(self, name, exec_required=True):
    # type: (str, bool) -> Optional[str]
    """
    Returns the path itself (for relative path), the resolve path, or None.
    """
    if '/' in name:
      if path_stat.exists(name):
        return name
      else:
        return None

    # TODO: Could cache this computation to avoid allocating every time for all
    # the splitting.
    path_val = self.mem.GetVar('PATH')
    if path_val.tag == value_e.Str and path_val.s:
      path_list = path_val.s.split(':')
    else:
      path_list = []  # treat as empty path

    for path_dir in path_list:
      full_path = os_path.join(path_dir, name)

      # NOTE: dash and bash only check for EXISTENCE in 'command -v' (and 'type
      # -t').  OSH follows mksh and zsh.  Note that we can still get EPERM if
      # the permissions are changed between check and use.
      if exec_required:
        found = posix.access(full_path, posix.X_OK)
      else:
        found = path_stat.exists(full_path)  # for 'source'

      if found:
        return full_path

    return None

  def CachedLookup(self, name):
    # type: (str) -> Optional[str]
    if name in self.cache:
      return self.cache[name]

    full_path = self.Lookup(name)
    if full_path is not None:
      self.cache[name] = full_path
    return full_path

  def MaybeRemoveEntry(self, name):
    """When the file system changes."""
    try:
      del self.cache[name]
    except KeyError:
      pass

  def ClearCache(self):
    """For hash -r."""
    self.cache.clear()

  def CachedCommands(self):
    """For hash -r."""
    return sorted(self.cache.values())


class _ErrExit(object):
  """Manages the errexit setting.

  - The user can change it with builtin 'set' at any point in the code.
  - These constructs implicitly disable 'errexit':
    - if / while / until conditions
    - ! (part of pipeline)
    - && ||

  An _ErrExit object prevents these two mechanisms from clobbering each other.
  """
  def __init__(self):
    # type: () -> None
    self.errexit = False  # the setting
    # SUBTLE INVARIANT: There's only ONE valid integer in the stack that's not
    # runtime.NO_SPID, and it's either a valid span_id or 0.  Push() and Set()
    # enforce this.
    self.stack = []

  def Push(self, span_id):
    # type: (int) -> None
    """Temporarily disable errexit."""
    assert span_id != runtime.NO_SPID
    if self.errexit:
      self.errexit = False
      self.stack.append(span_id)  # value to restore
    else:
      self.stack.append(runtime.NO_SPID)  # INVALID span ID / "False"

  def Pop(self):
    # type: () -> None
    """Restore the previous value."""
    self.errexit = (self.stack.pop() != runtime.NO_SPID)

  def SpidIfDisabled(self):
    # type: () -> int
    for n in self.stack:
      if n != runtime.NO_SPID:  # set -e will be restored later
        return n
    return runtime.NO_SPID

  def Set(self, b):
    # type: (bool) -> None
    """Set the errexit flag.

    Callers: set -o errexit, shopt -s oil:all, strict:all.
    """
    for i, n in enumerate(self.stack):
      if n != runtime.NO_SPID:  # set -e will be restored later
        # Ignore set -e or set +e now, but its effect becomes visible LATER.
        # This is confusing behavior that all shells implement!  strict_errexit
        # makes it a non-issue.

        # SUBTLE: 0 isn't a valid span_id, but we will never use it for the
        # strict_errexit message.
        self.stack[i] = 0 if b else runtime.NO_SPID
        return

    self.errexit = b  # Otherwise just set it

  def Disable(self):
    # type: () -> None
    """For bash compatibility in command sub."""
    self.errexit = False


# Used by builtin
SET_OPTIONS = [
    # NOTE: set -i and +i is explicitly disallowed.  Only osh -i or +i is valid
    # https://unix.stackexchange.com/questions/339506/can-an-interactive-shell-become-non-interactive-or-vice-versa

    ('e', 'errexit'),
    ('n', 'noexec'),
    ('u', 'nounset'),
    ('x', 'xtrace'),
    ('v', 'verbose'),
    ('f', 'noglob'),
    ('C', 'noclobber'),
    ('h', 'hashall'),
    (None, 'pipefail'),
    # A no-op for modernish.
    (None, 'posix'),

    (None, 'vi'),
    (None, 'emacs'),

    # TODO: Add strict_arg_parse?  For example, 'trap 1 2 3' shouldn't be
    # valid, because it has an extra argument.  Builtins are inconsistent about
    # checking this.
]

# Used by core/builtin_comp.py too.
SET_OPTION_NAMES = set(name for _, name in SET_OPTIONS)

_STRICT_OPTION_NAMES = [
    # NOTE:
    # - some are PARSING: strict_glob, strict_backslash
    # - some are runtime: strict_arith, strict_word_eval

    'strict_argv',  # empty argv not allowed
    'strict_arith',  # string to integer conversions
    'strict_array',  # no implicit conversion between string and array
    'strict_control_flow',  # break/continue at top level is fatal
    'strict_errexit',  # errexit can't be disabled during function body execution
    'strict_eval_builtin',  # single arg
    'strict_word_eval',  # negative slices, unicode

    # Not implemented
    'strict_backslash',  # BadBackslash
    'strict_glob',  # GlobParser
]

# These will break some programs, but the fix should be simple.
_BASIC_RUNTIME_OPTIONS = [
    'simple_word_eval',  # No splitting (arity isn't data-dependent)
                         # Don't reparse program data as globs
    'more_errexit',  # check after command sub
    'simple_test_builtin',  # only file tests (no strings), remove [, status 2
]

_AGGRESSIVE_RUNTIME_OPTIONS = [
]

# No-ops for bash compatibility
_NO_OPS = [
    'expand_aliases', 'extglob', 'lastpipe',  # language features always on

    # Handled one by one
    'progcomp',
    'histappend',  # stubbed out for issue #218
    'hostcomplete',  # complete words with '@' ?
    'cmdhist',  # multi-line commands in history

    # Copied from https://www.gnu.org/software/bash/manual/bash.txt
    # except 'compat*' because they were deemed too ugly
    'assoc_expand_once', 'autocd', 'cdable_vars',
    'cdspell', 'checkhash', 'checkjobs', 'checkwinsize',
    'complete_fullquote',  # Set by default
         # If set, Bash quotes all shell metacharacters in filenames and
         # directory names when performing completion.  If not set, Bash
         # removes metacharacters such as the dollar sign from the set of
         # characters that will be quoted in completed filenames when
         # these metacharacters appear in shell variable references in
         # words to be completed.  This means that dollar signs in
         # variable names that expand to directories will not be quoted;
         # however, any dollar signs appearing in filenames will not be
         # quoted, either.  This is active only when bash is using
         # backslashes to quote completed filenames.  This variable is
         # set by default, which is the default Bash behavior in versions
         # through 4.2.

    'direxpand', 'dirspell', 'dotglob', 'execfail',
    'extdebug',  # for --debugger?
    'extquote', 'force_fignore', 'globasciiranges',
    'globstar',  # TODO:  implement **
    'gnu_errfmt', 'histreedit', 'histverify', 'huponexit',
    'interactive_comments', 'lithist', 'localvar_inherit', 'localvar_unset',
    'login_shell', 'mailwarn', 'no_empty_cmd_completion', 'nocaseglob',
    'nocasematch', 'progcomp_alias', 'promptvars', 'restricted_shell',
    'shift_verbose', 'sourcepath', 'xpg_echo',
]

# Used by core/builtin_comp.py too.
SHOPT_OPTION_NAMES = [
    'nullglob', 'failglob',
    'inherit_errexit',
] + _NO_OPS + _STRICT_OPTION_NAMES + _BASIC_RUNTIME_OPTIONS + \
    _AGGRESSIVE_RUNTIME_OPTIONS

# Oil parse options only.
_BASIC_PARSE_OPTIONS = [
    'parse_at',
    'parse_brace',
    'parse_index_expr',
    'parse_paren',
    'parse_rawc',
]

# Extra stuff that breaks too many programs.
_AGGRESSIVE_PARSE_OPTIONS = [
    'parse_set',
    'parse_equals',
    'parse_do',
]

_PARSE_OPTION_NAMES = _BASIC_PARSE_OPTIONS + _AGGRESSIVE_PARSE_OPTIONS

_OIL_AGGRESSIVE = _AGGRESSIVE_PARSE_OPTIONS + _AGGRESSIVE_RUNTIME_OPTIONS

# errexit is also set, but handled separately
_MORE_STRICT = ['nounset', 'pipefail', 'inherit_errexit']

_OIL_BASIC = (
    _STRICT_OPTION_NAMES + _MORE_STRICT + _BASIC_PARSE_OPTIONS +
    _BASIC_RUNTIME_OPTIONS
)
# nullglob instead of simple-word-eval
_ALL_STRICT = _STRICT_OPTION_NAMES + _MORE_STRICT + ['nullglob']

# Used in builtin_pure.py
ALL_SHOPT_OPTIONS = SHOPT_OPTION_NAMES + _PARSE_OPTION_NAMES

META_OPTIONS = ['strict:all', 'oil:basic', 'oil:all']  # Passed to flag parser


class ExecOpts(object):

  def __init__(self, mem, parse_opts, readline):
    """
    Args:
      mem: state.Mem, for SHELLOPTS
    """
    self.mem = mem
    self.parse_opts = parse_opts
    # Used for 'set -o vi/emacs'
    self.readline = readline

    # Depends on the shell invocation (sh -i, etc.)  This is not technically an
    # 'set' option, but it appears in $-.
    self.interactive = False

    # set -o / set +o
    self.errexit = _ErrExit()  # -e
    self.nounset = False  # -u
    self.pipefail = False
    self.xtrace = False  # NOTE: uses PS4
    self.verbose = False  # like xtrace, but prints unevaluated commands
    self.noglob = False  # -f
    self.noexec = False  # -n
    self.noclobber = False  # -C
    self.posix = False
    # We don't do anything with this yet.  But Aboriginal calls 'set +h'.
    self.hashall = True  # -h is true by default.

    # OSH-specific options.

    # e.g. x=foo; echo $(( x )) is fatal
    self.strict_arith = False

    self.strict_argv = False

    # No implicit conversions between string and array.
    # - foo="$@" not allowed because it decays.  Should be foo=( "$@" ).
    # - ${a} not ${a[0]} (not implemented)
    self.strict_array = False

    # sane-array: compare arrays like [[ "$@" == "${a[@]}" ]], which is
    #             incompatible because bash coerces
    # default:    do not allow

    self.strict_control_flow = False  # break at top level is fatal, etc.
    self.strict_errexit = False
    self.strict_eval_builtin = False  # only accepts single arg
    self.strict_word_eval = False  # Bad slices and bad unicode

    # This comes after all the 'set' options.
    shellopts = self.mem.GetVar('SHELLOPTS')
    assert shellopts.tag == value_e.Str, shellopts
    self._InitOptionsFromEnv(shellopts.s)

    # shopt -s / -u.  NOTE: bash uses $BASHOPTS rather than $SHELLOPTS for
    # these.
    self.nullglob = False
    self.failglob = False
    self.inherit_errexit = False

    for attr_name in _NO_OPS:
      setattr(self, attr_name, False)

    self.vi = False
    self.emacs = False

    # 
    # Turned on with shopt -s all:oil
    #
    self.simple_word_eval = False

    # more_errexit makes 'local foo=$(false)' and echo $(false) fail.
    # By default, we have mimic bash's undesirable behavior of ignoring
    # these failures, since ash copied it, and Alpine's abuild relies on it.
    #
    # bash 4.4 also has shopt -s inherit_errexit, which says that command subs
    # inherit the value of errexit.  # I don't believe it is strict enough --
    # local still needs to fail.
    self.more_errexit = False

    self.simple_test_builtin = False

    #
    # OSH-specific options that are NOT YET IMPLEMENTED.
    #

    self.strict_glob = False  # glob_.py GlobParser has warnings
    self.strict_backslash = False  # BadBackslash for echo -e, printf, PS1, etc.

  def _InitOptionsFromEnv(self, shellopts):
    # e.g. errexit:nounset:pipefail
    lookup = set(shellopts.split(':'))
    for _, name in SET_OPTIONS:
      if name in lookup:
        self._SetOption(name, True)

  def ErrExit(self):
    # type: () -> bool
    return self.errexit.errexit

  def GetDollarHyphen(self):
    # type: () -> str
    chars = []
    if self.interactive:
      chars.append('i')

    if self.ErrExit():
      chars.append('e')
    if self.nounset:
      chars.append('u')
    # NO letter for pipefail?
    if self.xtrace:
      chars.append('x')
    if self.noexec:
      chars.append('n')

    # bash has:
    # - c for sh -c, i for sh -i (mksh also has this)
    # - h for hashing (mksh also has this)
    # - B for brace expansion
    return ''.join(chars)

  def _SetOption(self, opt_name, b):
    """Private version for synchronizing from SHELLOPTS."""
    assert '_' not in opt_name
    if opt_name not in SET_OPTION_NAMES:
      raise args.UsageError('got invalid option %r' % opt_name)
    if opt_name == 'errexit':
      self.errexit.Set(b)
    elif opt_name in ('vi', 'emacs'):
      if self.readline:
        self.readline.parse_and_bind("set editing-mode " + opt_name);
      else:
        e_die("Can't set option %r because Oil wasn't built with the readline "
              "library.", opt_name)
    else:
      if opt_name == 'verbose' and b:
        log('Warning: set -o verbose not implemented')
      setattr(self, opt_name, b)

  def _SetParseOption(self, attr, b):
    if not self.mem.InGlobalNamespace():
      e_die('Syntax options must be set at the top level '
            '(outside any function)')
    setattr(self.parse_opts, attr, b)

  def SetOption(self, opt_name, b):
    """ For set -o, set +o, or shopt -s/-u -o. """
    self._SetOption(opt_name, b)

    val = self.mem.GetVar('SHELLOPTS')
    assert val.tag == value_e.Str
    shellopts = val.s

    # Now check if SHELLOPTS needs to be updated.  It may be exported.
    #
    # NOTE: It might be better to skip rewriting SEHLLOPTS in the common case
    # where it is not used.  We could do it lazily upon GET.

    # Also, it would be slightly more efficient to update SHELLOPTS if
    # settings were batched, Examples:
    # - set -eu
    # - shopt -s foo bar
    if b:
      if opt_name not in shellopts:
        new_val = value.Str('%s:%s' % (shellopts, opt_name))
        self.mem.InternalSetGlobal('SHELLOPTS', new_val)
    else:
      if opt_name in shellopts:
        names = [n for n in shellopts.split(':') if n != opt_name]
        new_val = value.Str(':'.join(names))
        self.mem.InternalSetGlobal('SHELLOPTS', new_val)

  def SetShoptOption(self, opt_name, b):
    """ For shopt -s/-u. """

    # shopt -s all:oil turns on all Oil options, which includes all strict #
    # options
    if opt_name == 'oil:basic':
      for attr in _OIL_BASIC:
        if attr in _PARSE_OPTION_NAMES:
          self._SetParseOption(attr, b)
        else:
          setattr(self, attr, b)

      self.errexit.Set(b)  # Special case
      return

    if opt_name == 'oil:all':
      for attr in _OIL_BASIC + _OIL_AGGRESSIVE:
        self._SetParseOption(attr, b)
        setattr(self, attr, b)

      self.errexit.Set(b)  # Special case
      return

    if opt_name == 'strict:all':
      for attr in _ALL_STRICT:
        setattr(self, attr, b)

      self.errexit.Set(b)  # Special case
      return

    if opt_name in SHOPT_OPTION_NAMES:
      setattr(self, opt_name, b)
    elif opt_name in _PARSE_OPTION_NAMES:
      self._SetParseOption(opt_name, b)
    else:
      raise args.UsageError('got invalid option %r' % opt_name)

  def ShowOptions(self, opt_names):
    """ For 'set -o' and 'shopt -p -o' """
    # TODO: Maybe sort them differently?
    opt_names = opt_names or SET_OPTION_NAMES
    for opt_name in opt_names:
      if opt_name not in SET_OPTION_NAMES:
        raise args.UsageError('got invalid option %r' % opt_name)

      if opt_name == 'errexit':
        b = self.errexit.errexit
      else:
        b = getattr(self, opt_name)
      print('set %so %s' % ('-' if b else '+', opt_name))

  def ShowShoptOptions(self, opt_names):
    """ For 'shopt -p' """
    opt_names = opt_names or ALL_SHOPT_OPTIONS  # show all
    for opt_name in opt_names:
      if opt_name in SHOPT_OPTION_NAMES:
        b = getattr(self, opt_name)
      elif opt_name in _PARSE_OPTION_NAMES:
        b = getattr(self.parse_opts, opt_name)
      else:
        raise args.UsageError('got invalid option %r' % opt_name)
      print('shopt -%s %s' % ('s' if b else 'u', opt_name))


class _ArgFrame(object):
  """Stack frame for arguments array."""

  def __init__(self, argv):
    # type: (List[str]) -> None
    self.argv = argv
    self.num_shifted = 0

  def __repr__(self):
    return '<_ArgFrame %s %d at %x>' % (self.argv, self.num_shifted, id(self))

  def Dump(self):
    return {
        'argv': self.argv,
        'num_shifted': self.num_shifted,
    }

  def GetArgNum(self, arg_num):
    index = self.num_shifted + arg_num - 1
    if index >= len(self.argv):
      return value.Undef()

    return value.Str(str(self.argv[index]))

  def GetArgv(self):
    # () -> List[str]
    return self.argv[self.num_shifted : ]

  def GetNumArgs(self):
    return len(self.argv) - self.num_shifted

  def SetArgv(self, argv):
    self.argv = argv
    self.num_shifted = 0


def _DumpVarFrame(frame):
  """Dump the stack frame as reasonably compact and readable JSON."""

  vars_json = {}
  for name, cell in frame.iteritems():
    cell_json = {}

    flags = ''
    if cell.exported:
      flags += 'x'
    if cell.readonly:
      flags += 'r'
    if flags:
      cell_json['flags'] = flags

    # For compactness, just put the value right in the cell.
    tag = cell.val.tag
    if tag == value_e.Undef:
      cell_json['type'] = 'Undef'
    elif tag == value_e.Str:
      cell_json['type'] = 'Str'
      cell_json['value'] = cell.val.s
    elif tag == value_e.MaybeStrArray:
      cell_json['type'] = 'MaybeStrArray'
      cell_json['value'] = cell.val.strs

    vars_json[name] = cell_json

  return vars_json


class DirStack(object):
  """For pushd/popd/dirs."""
  def __init__(self):
    self.stack = []
    self.Reset()  # Invariant: it always has at least ONE entry.

  def Reset(self):
    del self.stack[:] 
    self.stack.append(posix.getcwd())

  def Push(self, entry):
    self.stack.append(entry)

  def Pop(self):
    if len(self.stack) <= 1:
      return None
    self.stack.pop()  # remove last
    return self.stack[-1]  # return second to last

  def Iter(self):
    """Iterate in reverse order."""
    return reversed(self.stack)


def _FormatStack(var_stack):
  """Temporary debugging.

  TODO: Turn this into a real JSON dump or something.
  """
  f = cStringIO.StringIO()
  for i, entry in enumerate(var_stack):
    f.write('[%d] %s' % (i, entry))
    f.write('\n')
  return f.getvalue()


def _GetWorkingDir():
  """Fallback for pwd and $PWD when there's no 'cd' and no inherited $PWD."""
  try:
    return posix.getcwd()
  except OSError as e:
    e_die("Can't determine working directory: %s", posix.strerror(e.errno))


class Mem(object):
  """For storing variables.

  Mem is better than "Env" -- Env implies OS stuff.

  Callers:
    User code: assigning and evaluating variables, in command context or
      arithmetic context.
    Completion engine: for COMP_WORDS, etc.
    Builtins call it implicitly: read, cd for $PWD, $OLDPWD, etc.

  Modules: cmd_exec, word_eval, expr_eval, completion
  """
  def __init__(self, dollar0, argv, environ, arena, has_main=False):
    self.dollar0 = dollar0
    self.argv_stack = [_ArgFrame(argv)]
    self.var_stack = [{}]

    # The debug_stack isn't strictly necessary for execution.  We use it for
    # crash dumps and for 3 parallel arrays: FUNCNAME, CALL_SOURCE,
    # BASH_LINENO.  The First frame points at the global vars and argv.
    self.debug_stack = [(None, None, runtime.NO_SPID, 0, 0)]

    self.bash_source = []  # for implementing BASH_SOURCE
    self.has_main = has_main
    if has_main:
      self.bash_source.append(dollar0)  # e.g. the filename

    self.current_spid = runtime.NO_SPID

    # Note: we're reusing these objects because they change on every single
    # line!  Don't want to allocate more than necsesary.
    self.source_name = value.Str('')
    self.line_num = value.Str('')

    self.last_status = [0]  # type: List[int]  # a stack
    self.pipe_status = [[]]  # type: List[List[int]]  # stack
    self.last_bg_pid = -1  # Uninitialized value mutable public variable

    # Done ONCE on initialization
    self.root_pid = posix.getpid()

    self._InitDefaults()
    self._InitVarsFromEnv(environ)
    # MUTABLE GLOBAL that's SEPARATE from $PWD.  Used by the 'pwd' builtin, but
    # it can't be modified by users.
    self.pwd = self.GetVar('PWD').s

    self.arena = arena

  def __repr__(self):
    parts = []
    parts.append('<Mem')
    for i, frame in enumerate(self.var_stack):
      parts.append('  -- %d --' % i)
      for n, v in frame.iteritems():
        parts.append('  %s %s' % (n, v))
    parts.append('>')
    return '\n'.join(parts) + '\n'

  def SetPwd(self, pwd):
    """Used by builtins."""
    self.pwd = pwd

  def InGlobalNamespace(self):
    """For checking that syntax options are only used at the top level."""
    return len(self.argv_stack) == 1

  def Dump(self):
    """Copy state before unwinding the stack."""
    var_stack = [_DumpVarFrame(frame) for frame in self.var_stack]
    argv_stack = [frame.Dump() for frame in self.argv_stack]
    debug_stack = []
    for func_name, source_name, call_spid, argv_i, var_i in self.debug_stack:
      d = {}
      if func_name:
        d['func_called'] = func_name
      elif source_name:
        d['file_sourced'] = source_name
      else:
        pass  # It's a frame for FOO=bar?  Or the top one?

      d['call_spid'] = call_spid
      if call_spid != runtime.NO_SPID:  # first frame has this issue
        span = self.arena.GetLineSpan(call_spid)
        line_id = span.line_id
        d['call_source'] = self.arena.GetLineSourceString(line_id)
        d['call_line_num'] = self.arena.GetLineNumber(line_id)
        d['call_line'] = self.arena.GetLine(line_id)

      d['argv_frame'] = argv_i
      d['var_frame'] = var_i
      debug_stack.append(d)

    return var_stack, argv_stack, debug_stack

  def _InitDefaults(self):

    # Default value; user may unset it.
    # $ echo -n "$IFS" | python -c 'import sys;print repr(sys.stdin.read())'
    # ' \t\n'
    SetGlobalString(self, 'IFS', split.DEFAULT_IFS)

    # NOTE: Should we put these in a namespace for Oil?
    SetGlobalString(self, 'UID', str(posix.getuid()))
    SetGlobalString(self, 'EUID', str(posix.geteuid()))
    SetGlobalString(self, 'PPID', str(posix.getppid()))

    SetGlobalString(self, 'HOSTNAME', str(libc.gethostname()))

    # In bash, this looks like 'linux-gnu', 'linux-musl', etc.  Scripts test
    # for 'darwin' and 'freebsd' too.  They generally don't like at 'gnu' or
    # 'musl'.  We don't have that info, so just make it 'linux'.
    SetGlobalString(self, 'OSTYPE', str(posix.uname()[0].lower()))

    # For getopts builtin
    SetGlobalString(self, 'OPTIND', '1')

    # For xtrace
    SetGlobalString(self, 'PS4', '+ ')

    # bash-completion uses this.  Value copied from bash.  It doesn't integrate
    # with 'readline' yet.
    SetGlobalString(self, 'COMP_WORDBREAKS', _READLINE_DELIMS)

    # TODO on $HOME: bash sets it if it's a login shell and not in POSIX mode!
    # if (login_shell == 1 && posixly_correct == 0)
    #   set_home_var ();

  def _InitVarsFromEnv(self, environ):
    # This is the way dash and bash work -- at startup, they turn everything in
    # 'environ' variable into shell variables.  Bash has an export_env
    # variable.  Dash has a loop through environ in init.c
    for n, v in environ.iteritems():
      self.SetVar(sh_lhs_expr.Name(n), value.Str(v),
                 (var_flags_e.Exported,), scope_e.GlobalOnly)

    # If it's not in the environment, initialize it.  This makes it easier to
    # update later in ExecOpts.

    # TODO: IFS, etc. should follow this pattern.  Maybe need a SysCall
    # interface?  self.syscall.getcwd() etc.

    v = self.GetVar('SHELLOPTS')
    if v.tag == value_e.Undef:
      SetGlobalString(self, 'SHELLOPTS', '')
    # Now make it readonly
    self.SetVar(
        sh_lhs_expr.Name('SHELLOPTS'), None, (var_flags_e.ReadOnly,),
        scope_e.GlobalOnly)

    # Usually we inherit PWD from the parent shell.  When it's not set, we may
    # compute it.
    v = self.GetVar('PWD')
    if v.tag == value_e.Undef:
      SetGlobalString(self, 'PWD', _GetWorkingDir())
    # Now mark it exported, no matter what.  This is one of few variables
    # EXPORTED.  bash and dash both do it.  (e.g. env -i -- dash -c env)
    self.SetVar(
        sh_lhs_expr.Name('PWD'), None, (var_flags_e.Exported,),
        scope_e.GlobalOnly)

  def SetCurrentSpanId(self, span_id):
    # type: (int) -> None
    """Set the current source location, for BASH_SOURCE, BASH_LINENO, LINENO,
    etc.

    It's also set on SimpleCommand, ShAssignment, ((, [[, etc. and used as
    a fallback when e_die() didn't set any location information.
    """
    if span_id == runtime.NO_SPID:
      # NOTE: This happened in the osh-runtime benchmark for yash.
      log('Warning: span_id undefined in SetCurrentSpanId')

      #import traceback
      #traceback.print_stack()
      return
    self.current_spid = span_id

  def CurrentSpanId(self):
    # type: () -> int
    return self.current_spid

  #
  # Status Variable Stack (for isolating $PS1 and $PS4)
  #

  def PushStatusFrame(self):
    # type: () -> None
    self.last_status.append(0)
    self.pipe_status.append([])

  def PopStatusFrame(self):
    # type: () -> None
    self.last_status.pop()
    self.pipe_status.pop()

  def LastStatus(self):
    # type: () -> int
    return self.last_status[-1]

  def PipeStatus(self):
    # type: () -> List[int]
    return self.pipe_status[-1]

  def SetLastStatus(self, x):
    # type: (int) -> None
    self.last_status[-1] = x

  def SetPipeStatus(self, x):
    # type: (List[int]) -> None
    self.pipe_status[-1] = x

  #
  # Call Stack
  #

  def PushCall(self, func_name, def_spid, argv):
    # type: (str, int, List[str]) -> None
    """For function calls."""
    self.argv_stack.append(_ArgFrame(argv))
    self.var_stack.append({})

    # bash uses this order: top of stack first.
    self._PushDebugStack(func_name, None)

    span = self.arena.GetLineSpan(def_spid)
    source_str = self.arena.GetLineSourceString(span.line_id)
    self.bash_source.append(source_str)

  def PopCall(self):
    # type: () -> None
    self.bash_source.pop()
    self._PopDebugStack()

    self.var_stack.pop()
    self.argv_stack.pop()

  def PushSource(self, source_name, argv):
    # type: (str, List[str]) -> None
    """For 'source foo.sh 1 2 3."""
    if argv:
      self.argv_stack.append(_ArgFrame(argv))
    # Match bash's behavior for ${FUNCNAME[@]}.  But it would be nicer to add
    # the name of the script here?
    self._PushDebugStack(None, source_name)
    self.bash_source.append(source_name)

  def PopSource(self, argv):
    # type: (List[str]) -> None
    self.bash_source.pop()
    self._PopDebugStack()
    if argv:
      self.argv_stack.pop()

  def PushTemp(self):
    # type: () -> None
    """For the temporary scope in 'FOO=bar BAR=baz echo'."""
    # We don't want the 'read' builtin to write to this frame!
    self.var_stack.append({})
    self._PushDebugStack(None, None)

  def PopTemp(self):
    # type: () -> None
    self._PopDebugStack()
    self.var_stack.pop()

  def TopNamespace(self):
    # type: () -> Dict[str, runtime_asdl.cell]
    """For evalblock()."""
    return self.var_stack[-1]

  def _PushDebugStack(self, func_name, source_name):
    # self.current_spid is set before every SimpleCommand, ShAssignment, [[, ((,
    # etc.  Function calls and 'source' are both SimpleCommand.

    # These integers are handles/pointers, for use in CrashDumper.
    argv_i = len(self.argv_stack) - 1
    var_i = len(self.var_stack) - 1

    # The stack is a 5-tuple, where func_name and source_name are optional.  If
    # both are unset, then it's a "temp frame".
    self.debug_stack.append(
        (func_name, source_name, self.current_spid, argv_i, var_i)
    )

  def _PopDebugStack(self):
    self.debug_stack.pop()

  #
  # Argv
  #

  def Shift(self, n):
    frame = self.argv_stack[-1]
    num_args = len(frame.argv)

    if (frame.num_shifted + n) <= num_args:
      frame.num_shifted += n
      return 0  # success
    else:
      return 1  # silent error

  def GetArgNum(self, arg_num):
    # type: (int) -> value__Str
    if arg_num == 0:
      return value.Str(self.dollar0)

    return self.argv_stack[-1].GetArgNum(arg_num)

  def GetArgv(self):
    # type: () -> List[str]
    """For $* and $@."""
    return self.argv_stack[-1].GetArgv()

  def SetArgv(self, argv):
    """For set -- 1 2 3."""
    # from set -- 1 2 3
    self.argv_stack[-1].SetArgv(argv)

  #
  # Special Vars
  #

  def GetSpecialVar(self, op_id):
    # type: (int) -> value_t
    if op_id == Id.VSub_Bang:  # $!
      n = self.last_bg_pid
      if n == -1:
        return value.Undef()  # could be an error

    elif op_id == Id.VSub_QMark:  # $?
      # External commands need WIFEXITED test.  What about subshells?
      n = self.last_status[-1]

    elif op_id == Id.VSub_Pound:  # $#
      n = self.argv_stack[-1].GetNumArgs()

    elif op_id == Id.VSub_Dollar:  # $$
      n = self.root_pid

    else:
      raise NotImplementedError(op_id)

    return value.Str(str(n))

  #
  # Named Vars
  #

  def _FindCellAndNamespace(self, name, lookup_mode):
    """Helper for getting and setting variable.

    Args:
      name: the variable name
      lookup_mode: scope_e

    Returns:
      cell: The cell corresponding to looking up 'name' with the given mode, or
        None if it's not found.
      namespace: The namespace it should be set to or deleted from.
    """
    if lookup_mode == scope_e.Dynamic:
      for i in xrange(len(self.var_stack) - 1, -1, -1):
        namespace = self.var_stack[i]
        if name in namespace:
          cell = namespace[name]
          return cell, namespace
      return None, self.var_stack[0]  # set in global namespace

    elif lookup_mode == scope_e.LocalOnly:
      namespace = self.var_stack[-1]
      return namespace.get(name), namespace

    elif lookup_mode == scope_e.GlobalOnly:
      namespace = self.var_stack[0]
      return namespace.get(name), namespace

    else:
      raise AssertionError(lookup_mode)

  def IsAssocArray(self, name, lookup_mode):
    """Returns whether a name resolve to a cell with an associative array.
    
    We need to know this to evaluate the index expression properly -- should it
    be coerced to an integer or not?
    """
    cell, _ = self._FindCellAndNamespace(name, lookup_mode)
    if cell:
      if cell.val.tag == value_e.AssocArray:  # foo=([key]=value)
        return True
    return False

  def _CheckOilKeyword(self, keyword_id, lval, cell):
    """Check that 'var' and setvar/set are used correctly.

    NOTE: These are dynamic checks, but the syntactic difference between
    definition and mutation will help translate the Oil subset of OSH to static
    languages.
    """

    if cell and keyword_id == Id.KW_Var:
      # TODO: Point at the ORIGINAL declaration!
      e_die("%r has already been declared", lval.name)

    if cell is None and keyword_id in (Id.KW_Set, Id.KW_SetVar):
      # NOTE: all 3 variants of 'lvalue' have 'name'
      e_die("%r hasn't been declared", lval.name)

  def SetVar(self, lval, val, flags_to_set, lookup_mode, flags_to_clear=(),
             keyword_id=None):
    # type: (lvalue_t, value_t, Tuple[var_flags_t, ...], scope_t, Tuple[var_flags_t, ...], Optional[Id_t]) -> None
    """
    Args:
      lval: lvalue
      val: value, or None if only changing flags
      flags_to_set: tuple of flags to set: ReadOnly | Exported
        () means no flags to start with

      lookup_mode:
        Local | Global | Dynamic - for builtins, PWD, etc.

      NOTE: in bash, PWD=/ changes the directory.  But not in dash.
    """
    # STRICTNESS / SANENESS:
    #
    # 1) Don't create arrays automatically, e.g. a[1000]=x
    # 2) Never change types?  yeah I think that's a good idea, at least for oil
    # (not sh, for compatibility).  set -o strict_types or something.  That
    # means arrays have to be initialized with let arr = [], which is fine.
    # This helps with stuff like IFS.  It starts off as a string, and assigning
    # it to a list is an error.  I guess you will have to turn this no for
    # bash?
    #
    # TODO:
    # - COMPUTED_VARS can't be set
    # - What about PWD / OLDPWD / UID / EUID ?  You can simply make them
    # readonly.
    # - $PS1 and $PS4 should be PARSED when they are set, to avoid the error on use
    # - Other validity: $HOME could be checked for existence

    assert flags_to_set is not None
    if lval.tag == lvalue_e.Named:
      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      self._CheckOilKeyword(keyword_id, lval, cell)
      if cell:
        # Clear before checking readonly bit.
        # NOTE: Could be cell.flags &= flag_clear_mask 
        if var_flags_e.Exported in flags_to_clear:
          cell.exported = False
        if var_flags_e.ReadOnly in flags_to_clear:
          cell.readonly = False

        if val is not None:  # e.g. declare -rx existing
          if cell.readonly:
            # TODO: error context
            e_die("Can't assign to readonly value %r", lval.name)
          cell.val = val

        # NOTE: Could be cell.flags |= flag_set_mask 
        if var_flags_e.Exported in flags_to_set:
          cell.exported = True
        if var_flags_e.ReadOnly in flags_to_set:
          cell.readonly = True

      else:
        if val is None:  # declare -rx nonexistent
          # set -o nounset; local foo; echo $foo  # It's still undefined!
          val = value.Undef()  # export foo, readonly foo

        cell = runtime_asdl.cell(val,
                                 var_flags_e.Exported in flags_to_set,
                                 var_flags_e.ReadOnly in flags_to_set)
        namespace[lval.name] = cell

      # Maintain invariant that only strings and undefined cells can be
      # exported.
      if (cell.val is not None and
          cell.val.tag not in (value_e.Undef, value_e.Str) and
          cell.exported):
        e_die("Can't export array")  # TODO: error context

    elif lval.tag == lvalue_e.Indexed:
      # There is no syntax 'declare a[x]'
      assert val is not None, val

      # TODO: All paths should have this?  We can get here by a[x]=1 or
      # (( a[ x ] = 1 )).  Maybe we should make them different?
      left_spid = lval.spids[0] if lval.spids else runtime.NO_SPID

      # bash/mksh have annoying behavior of letting you do LHS assignment to
      # Undef, which then turns into an INDEXED array.  (Undef means that set
      # -o nounset fails.)
      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      self._CheckOilKeyword(keyword_id, lval, cell)
      if not cell:
        self._BindNewArrayWithEntry(namespace, lval, val, flags_to_set)
        return

      if cell.readonly:
        e_die("Can't assign to readonly array", span_id=left_spid)

      cell_tag = cell.val.tag

      # undef[0]=y is allowed
      if cell_tag == value_e.Undef:
        self._BindNewArrayWithEntry(namespace, lval, val, flags_to_set)
        return

      if cell_tag == value_e.Str:
        # s=x
        # s[1]=y  # invalid
        e_die("Entries in value of type %s can't be assigned to",
              cell.val.__class__.__name__, span_id=left_spid)

      if cell_tag == value_e.MaybeStrArray:
        strs = cell.val.strs
        try:
          strs[lval.index] = val.s
        except IndexError:
          # Fill it in with None.  It could look like this:
          # ['1', 2, 3, None, None, '4', None]
          # Then ${#a[@]} counts the entries that are not None.
          #
          # TODO: strict_array for Oil arrays won't auto-fill.
          n = lval.index - len(strs) + 1
          strs.extend([None] * n)
          strs[lval.index] = val.s
        return

      # AssocArray shouldn't happen because we query IsAssocArray before
      # evaluating sh_lhs_expr.
      e_die("Object of this type can't be indexed: %s", cell.val)

    elif lval.tag == lvalue_e.Keyed:
      # There is no syntax 'declare A["x"]'
      assert val is not None, val

      left_spid = lval.spids[0] if lval.spids else runtime.NO_SPID

      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      self._CheckOilKeyword(keyword_id, lval, cell)
      # We already looked it up before making the lvalue
      assert cell.val.tag == value_e.AssocArray, cell
      if cell.readonly:
        e_die("Can't assign to readonly associative array", span_id=left_spid)

      cell.val.d[lval.key] = val.s

    else:
      raise AssertionError(lval.__class__.__name__)

  def _BindNewArrayWithEntry(self, namespace, lval, val, flags_to_set):
    """Fill 'namespace' with a new indexed array entry."""
    items = [None] * lval.index
    items.append(val.s)
    new_value = value.MaybeStrArray(items)

    # arrays can't be exported; can't have AssocArray flag
    readonly = var_flags_e.ReadOnly in flags_to_set
    namespace[lval.name] = runtime_asdl.cell(new_value, False, readonly)

  def InternalSetGlobal(self, name, new_val):
    """For setting read-only globals internally.

    Args:
      name: string (not Lhs)
      new_val: value

    The variable must already exist.

    Use case: SHELLOPTS.
    """
    cell = self.var_stack[0][name]
    cell.val = new_val

  def GetVar(self, name, lookup_mode=scope_e.Dynamic):
    # type: (str, scope_t) -> value_t
    assert isinstance(name, str), name

    # TODO: Short-circuit down to _FindCellAndNamespace by doing a single hash
    # lookup:
    # COMPUTED_VARS = {'PIPESTATUS': 1, 'FUNCNAME': 1, ...}
    # if name not in COMPUTED_VARS: ...

    if name == 'ARGV':
      # TODO:
      # - Reuse the MaybeStrArray?
      # - @@ could be an alias for ARGV (in command mode, but not expr mode)
      return value.MaybeStrArray(self.GetArgv())

    if name == 'PIPESTATUS':
      return value.MaybeStrArray([str(i) for i in self.pipe_status[-1]])

    # Do lookup of system globals before looking at user variables.  Note: we
    # could optimize this at compile-time like $?.  That would break
    # ${!varref}, but it's already broken for $?.
    if name == 'FUNCNAME':
      # bash wants it in reverse order.  This is a little inefficient but we're
      # not depending on deque().
      strs = []
      for func_name, source_name, _, _, _ in reversed(self.debug_stack):
        if func_name:
          strs.append(func_name)
        if source_name:
          strs.append('source')  # bash doesn't give name
        # Temp stacks are ignored

      if self.has_main:
        strs.append('main')  # bash does this
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    # This isn't the call source, it's the source of the function DEFINITION
    # (or the sourced # file itself).
    if name == 'BASH_SOURCE':
      return value.MaybeStrArray(list(reversed(self.bash_source)))

    # This is how bash source SHOULD be defined, but it's not!
    if name == 'CALL_SOURCE':
      strs = []
      for func_name, source_name, call_spid, _, _ in reversed(self.debug_stack):
        # should only happen for the first entry
        if call_spid == runtime.NO_SPID:
          continue
        span = self.arena.GetLineSpan(call_spid)
        source_str = self.arena.GetLineSourceString(span.line_id)
        strs.append(source_str)
      if self.has_main:
        strs.append('-')  # Bash does this to line up with main?
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    if name == 'BASH_LINENO':
      strs = []
      for _, _, call_spid, _, _ in reversed(self.debug_stack):
        # should only happen for the first entry
        if call_spid == runtime.NO_SPID:
          continue
        span = self.arena.GetLineSpan(call_spid)
        line_num = self.arena.GetLineNumber(span.line_id)
        strs.append(str(line_num))
      if self.has_main:
        strs.append('0')  # Bash does this to line up with main?
      return value.MaybeStrArray(strs)  # TODO: Reuse this object too?

    if name == 'LINENO':
      assert self.current_spid != -1, self.current_spid
      span = self.arena.GetLineSpan(self.current_spid)
      # TODO: maybe use interned GetLineNumStr?
      self.line_num.s = str(self.arena.GetLineNumber(span.line_id))
      return self.line_num

    # This is OSH-specific.  Get rid of it in favor of ${BASH_SOURCE[0]} ?
    if name == 'SOURCE_NAME':
      # Update and reuse an object.
      span = self.arena.GetLineSpan(self.current_spid)
      self.source_name.s = self.arena.GetLineSourceString(span.line_id)
      return self.source_name

    cell, _ = self._FindCellAndNamespace(name, lookup_mode)

    if cell:
      return cell.val

    return value.Undef()

  def GetCell(self, name):
    """For the 'repr' builtin."""
    cell, _ = self._FindCellAndNamespace(name, scope_e.Dynamic)
    return cell

  def Unset(self, lval, lookup_mode):
    """
    Returns:
      ok bool, found bool.

      ok is false if the cell is read-only.
      found is false if the name is not there.
    """
    if lval.tag == lvalue_e.Named:  # unset x
      cell, namespace = self._FindCellAndNamespace(lval.name, lookup_mode)
      if cell:
        found = True
        if cell.readonly:
          return False, found
        namespace[lval.name].val = value.Undef()
        cell.exported = False
        return True, found # found
      else:
        return True, False

    elif lval.tag == lvalue_e.Indexed:  # unset a[1]
      raise NotImplementedError

    else:
      raise AssertionError

  def ClearFlag(self, name, flag, lookup_mode):
    """Used for export -n.

    We don't use SetVar() because even if rval is None, it will make an Undef
    value in a scope.
    """
    cell, namespace = self._FindCellAndNamespace(name, lookup_mode)
    if cell:
      if flag == var_flags_e.Exported:
        cell.exported = False
      else:
        raise AssertionError
      return True
    else:
      return False

  def GetExported(self):
    # type: () -> List[str]
    """Get all the variables that are marked exported."""
    # TODO: This is run on every SimpleCommand.  Should we have a dirty flag?
    # We have to notice these things:
    # - If an exported variable is changed.
    # - If the set of exported variables changes.

    exported = {}
    # Search from globals up.  Names higher on the stack will overwrite names
    # lower on the stack.
    for scope in self.var_stack:
      for name, cell in scope.iteritems():
        # TODO: Disallow exporting at assignment time.  If an exported Str is
        # changed to MaybeStrArray, also clear its 'exported' flag.
        if cell.exported and cell.val.tag == value_e.Str:
          exported[name] = cell.val.s
    return exported

  def VarNames(self):
    """For internal OSH completion and compgen -A variable.

    NOTE: We could also add $? $$ etc.?
    """
    # Look up the stack, yielding all variables.  Bash seems to do this.
    for scope in self.var_stack:
      for name, _ in scope.iteritems():
        yield name

  def VarNamesStartingWith(self, prefix):
    # type: (str) -> List[str]
    """For ${!prefix@}"""
    # Look up the stack, yielding all variables.  Bash seems to do this.
    names = []
    for scope in self.var_stack:
      for name, _ in scope.iteritems():
        if name.startswith(prefix):
          names.append(name)
    return names

  def GetAllVars(self):
    """Get all variables and their values, for 'set' builtin. """
    result = {}
    for scope in self.var_stack:
      for name, cell in scope.iteritems():
        if isinstance(cell.val, value__Str):
          result[name] = cell.val.s
    return result


def SetLocalString(mem, name, s):
  # type: (Mem, str, str) -> None
  """Set a local string.

  Used for:
  1) for loop iteration variables
  2) temporary environments like FOO=bar BAR=$FOO cmd,
  3) read builtin
  """
  assert isinstance(s, str)
  mem.SetVar(sh_lhs_expr.Name(name), value.Str(s), (), scope_e.LocalOnly)


def SetStringDynamic(mem, name, s):
  """Set a string by looking up the stack.

  Used for getopts.
  """
  assert isinstance(s, str)
  mem.SetVar(sh_lhs_expr.Name(name), value.Str(s), (), scope_e.Dynamic)


def SetArrayDynamic(mem, name, a):
  """Set an array by looking up the stack.

  Used for _init_completion.
  """
  assert isinstance(a, list)
  mem.SetVar(sh_lhs_expr.Name(name), value.MaybeStrArray(a), (), scope_e.Dynamic)


def SetGlobalString(mem, name, s):
  """Helper for completion, etc."""
  assert isinstance(s, str)
  val = value.Str(s)
  mem.SetVar(sh_lhs_expr.Name(name), val, (), scope_e.GlobalOnly)


def SetGlobalArray(mem, name, a):
  """Helper for completion."""
  assert isinstance(a, list)
  mem.SetVar(sh_lhs_expr.Name(name), value.MaybeStrArray(a), (), scope_e.GlobalOnly)


def SetLocalArray(mem, name, a):
  """Helper for completion."""
  assert isinstance(a, list)
  mem.SetVar(sh_lhs_expr.Name(name), value.MaybeStrArray(a), (), scope_e.LocalOnly)


def ExportGlobalString(mem, name, s):
  """Helper for completion, $PWD, $OLDPWD, etc."""
  assert isinstance(s, str)
  val = value.Str(s)
  mem.SetVar(sh_lhs_expr.Name(name), val, (var_flags_e.Exported,),
             scope_e.GlobalOnly)


def GetGlobal(mem, name):
  assert isinstance(name, str), name
  return mem.GetVar(name, scope_e.GlobalOnly)
