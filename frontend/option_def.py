#!/usr/bin/env python2
"""
option_def.py
"""
from __future__ import print_function

from typing import List, Dict, Optional, Any


class Option(object):

  def __init__(self, index, name, short_flag=None, builtin='shopt',
               default=False, implemented=True, groups=None):
    # type: (int, str, str, Optional[str], bool, bool, List[str]) -> None
    self.index = index
    self.name = name  # e.g. 'errexit'
    self.short_flag = short_flag  # 'e' for -e

    if short_flag:
      self.builtin = 'set'
    else:
      # The 'interactive' option is the only one where builtin is None.  It has
      # a cell but you can't change it.  Only the shell can.
      self.builtin = builtin

    self.default = default  # default value is True in some cases
    self.implemented = implemented
    self.groups = groups or []  # list of groups

    # for optview
    self.is_parse = name.startswith('parse_') or name == 'expand_aliases'
    # interactive() is an accessor
    self.is_exec = implemented and not self.is_parse


class _OptionDef(object):
  """Description of all shell options.

  Similar to id_kind_def.IdSpec
  """
  def __init__(self):
    # type: () -> None
    self.opts = []  # type: List[Option]
    self.index = 1  # start with 1
    self.array_size = -1

  def Add(self, *args, **kwargs):
    # type: (Any, Any) -> None
    self.opts.append(Option(self.index, *args, **kwargs))
    self.index += 1

  def DoneWithImplementedOptions(self):
    # type: () -> None
    self.array_size = self.index


# Used by builtin
_OTHER_SET_OPTIONS = [
    # NOTE: set -i and +i is explicitly disallowed.  Only osh -i or +i is valid
    # https://unix.stackexchange.com/questions/339506/can-an-interactive-shell-become-non-interactive-or-vice-versa

    ('n', 'noexec'),
    ('x', 'xtrace'),
    ('v', 'verbose'),  # like xtrace, but prints unevaluated commands
    ('f', 'noglob'),
    ('C', 'noclobber'),

    # A no-op for modernish.
    (None, 'posix'),

    (None, 'vi'),
    (None, 'emacs'),
]

# These are RUNTIME strict options.  We also have parse time ones like
# parse_backslash.
_STRICT_OPTION_NAMES = [
    'strict_argv',  # empty argv not allowed
    'strict_arith',  # string to integer conversions, e.g. x=foo; echo $(( x ))

    # No implicit conversions between string and array.
    # - foo="$@" not allowed because it decays.  Should be foo=( "$@" ).
    # - ${a} not ${a[0]} (not implemented)
    # sane-array?  compare arrays like [[ "$@" == "${a[@]}" ]], which is
    #              incompatible because bash coerces
    # default:    do not allow
    'strict_array',
    'strict_control_flow',  # break/continue at top level is fatal
                            # 'return $empty' and return "" are NOT accepted
    'strict_errexit',       # errexit can't be disabled in compound commands
    'strict_nameref',       # trap invalid variable names
    'strict_word_eval',     # negative slices, unicode
    'strict_tilde',         # ~nonexistent is an error (like zsh)

    # Not implemented
    'strict_glob',          # glob_.py GlobParser has warnings
]

# These will break some programs, but the fix should be simple.

# command_sub_errexit makes 'local foo=$(false)' and echo $(false) fail.
# By default, we have mimic bash's undesirable behavior of ignoring
# these failures, since ash copied it, and Alpine's abuild relies on it.
#
# Note that inherit_errexit is a strict option.

_BASIC_RUNTIME_OPTIONS = [
    ('simple_word_eval', False),     # No splitting; arity isn't data-dependent
                                     # Don't reparse program data as globs
    ('dashglob', True),              # do globs return files starting with - ?

    # Turn this off so we can statically parse.  Because bash has it off
    # non-interactively, this shouldn't break much.
    ('expand_aliases', True),

    # TODO: Should these be in strict mode?
    # The logic was that strict_errexit improves your bash programs, but these
    # would lead you to remove error handling.  But the same could be said for
    # strict_array?

    ('command_sub_errexit', False),  # check after command sub
    ('process_sub_fail', False),     # like pipefail, but for <(sort foo.txt)
    ('xtrace_rich', False),          # Hierarchical trace with PIDs
    ('xtrace_details', True),        # Legacy set -x stuff

    # Whether status 141 in pipelines is turned into 0
    ('sigpipe_status_ok', False),

    # Can procs and shell functions be redefined?  On in shell, off in Oil
    # batch, on in interactive shell
    ('redefine_proc', True),
]

# TODO: Add strict_arg_parse?  For example, 'trap 1 2 3' shouldn't be
# valid, because it has an extra argument.  Builtins are inconsistent about
# checking this.

_AGGRESSIVE_RUNTIME_OPTIONS = [
    ('simple_echo', False),          # echo takes 0 or 1 arguments
    ('simple_eval_builtin', False),  # eval takes exactly 1 argument

    # only file tests (no strings), remove [, status 2
    ('simple_test_builtin', False),

    # TODO: simple_trap
]


# Stuff that doesn't break too many programs.
_BASIC_PARSE_OPTIONS = [
    'parse_at',  # @foo, @array(a, b)
    'parse_proc',  # proc p { ... }
    'parse_brace',  # cd /bin { ... }

    # bare assignment 'x = 42' is allowed in Hay { } blocks, but disallowed
    # everywhere else.  It's not a command 'x' with arg '='.
    'parse_equals',

    'parse_paren',  # if (x > 0) ...
    'parse_raw_string',  # echo r'\'
    'parse_triple_quote',  # for ''' and """
]

# Extra stuff that breaks too many programs.
_AGGRESSIVE_PARSE_OPTIONS = [
    ('parse_at_all', False),   # @ starting any word, e.g. @[] @{} @@ @_ @-

    # Legacy syntax that is removed.  These options are distinct from strict_*
    # because they don't help you avoid bugs in bash programs.  They just makes
    # the language more consistent.
    ('parse_backslash', True),
    ('parse_backticks', True),
    ('parse_dollar', True),
    ('parse_ignored', True),

    ('parse_sh_assign', True),    # disallow x=y and PYTHONPATH=y
    ('parse_dparen', True),       # disallow bash's ((
    ('parse_bare_word', True),    # 'case bare' and 'for x in bare'
    ('parse_sloppy_case', True),  # case patterns must be (*.py), not *.py)
]

# No-ops for bash compatibility
_NO_OPS = [
    'lastpipe',  # this feature is always on

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

def _Init(opt_def):
  # type: (_OptionDef) -> None

  opt_def.Add('errexit', short_flag='e', builtin='set',
              groups=['oil:upgrade', 'oil:all'])
  opt_def.Add('nounset', short_flag='u', builtin='set', 
              groups=['oil:upgrade', 'oil:all'])
  opt_def.Add('pipefail', builtin='set', 
              groups=['oil:upgrade', 'oil:all'])

  opt_def.Add('inherit_errexit',
              groups=['oil:upgrade', 'oil:all'])
  # Hm is this subsumed by simple_word_eval?
  opt_def.Add('nullglob',
              groups=['oil:upgrade', 'oil:all'])
  opt_def.Add('verbose_errexit',
              groups=['oil:upgrade', 'oil:all'])

  # set -o noclobber, etc.
  for short_flag, name in _OTHER_SET_OPTIONS:
    opt_def.Add(name, short_flag=short_flag, builtin='set')

  # The only one where builtin=None.  Only the shell can change it.
  opt_def.Add('interactive', builtin=None)

  # bash --norc -c 'set -o' shows this is on by default
  opt_def.Add('hashall', short_flag='h', builtin='set', default=True)

  #
  # shopt
  # (bash uses $BASHOPTS rather than $SHELLOPTS)
  #

  # shopt options that aren't in any groups.
  opt_def.Add('failglob')
  opt_def.Add('extglob')

  # Compatibility
  opt_def.Add('eval_unsafe_arith')  # recursive parsing and evaluation (ble.sh)
  opt_def.Add('parse_dynamic_arith')  # dynamic LHS
  opt_def.Add('compat_array')  # ${array} is ${array[0]}

  # For implementing strict_errexit
  opt_def.Add('allow_csub_psub', default=True)
  # For implementing 'proc'
  opt_def.Add('dynamic_scope', default=True)

  # On in interactive shell
  opt_def.Add('redefine_module', default=False)

  # For disabling strict_errexit while running traps.  Because we run in the
  # main loop, the value can be "off".  Prefix with _ because it's undocumented
  # and users shouldn't fiddle with it.  We need a stack so this is a
  # convenient place.
  opt_def.Add('_running_trap')
  opt_def.Add('_running_hay')

  # shopt -s strict_arith, etc.
  for name in _STRICT_OPTION_NAMES:
    opt_def.Add(name, groups=['strict:all', 'oil:all'])

  #
  # Options that enable Oil language features
  #

  for name in _BASIC_PARSE_OPTIONS:
    opt_def.Add(name, groups=['oil:upgrade', 'oil:all'])
  # shopt -s simple_word_eval, etc.
  for name, default in _BASIC_RUNTIME_OPTIONS:
    opt_def.Add(name, default=default, groups=['oil:upgrade', 'oil:all'])

  for name, default in _AGGRESSIVE_PARSE_OPTIONS:
    opt_def.Add(name, default=default, groups=['oil:all'])
  for name, default in _AGGRESSIVE_RUNTIME_OPTIONS:
    opt_def.Add(name, default=default, groups=['oil:all'])

  # Off by default.
  opt_def.Add('parse_tea')

  opt_def.DoneWithImplementedOptions()

  # NO_OPS

  # Stubs for shopt -s xpg_echo, etc.
  for name in _NO_OPS:
    opt_def.Add(name, implemented=False)


def All():
  # type: () -> List[Option]
  """Return a list of options with metadata.

  - Used by osh/builtin_pure.py to construct the arg spec.
  - Used by frontend/lexer_gen.py to construct the lexer/matcher
  """
  return _OPTION_DEF.opts


def ArraySize():
  # type: () -> int
  """
  Unused now, since we use opt_num::ARRAY_SIZE.  We could get rid of
  unimplemented options and shrink the array.
  """
  return _OPTION_DEF.array_size


def OptionDict():
  # type: () -> Dict[str, int]
  """For the slow path in frontend/match.py."""
  return dict((opt.name, opt.index) for opt in _OPTION_DEF.opts)


def ParseOptNames():
  # type: () -> List[str]
  """Used by core/optview*.py"""
  return [opt.name for opt in _OPTION_DEF.opts if opt.is_parse]


def ExecOptNames():
  # type: () -> List[str]
  """Used by core/optview*.py"""
  return [opt.name for opt in _OPTION_DEF.opts if opt.is_exec]


_OPTION_DEF = _OptionDef()

_Init(_OPTION_DEF)

# Sort by name because we print options.
# TODO: for MEMBERSHIP queries, we could sort by the most common?  errexit
# first?
_SORTED = sorted(_OPTION_DEF.opts, key=lambda opt: opt.name)

PARSE_OPTION_NUMS = [opt.index for opt in _SORTED if opt.is_parse]

# Sorted because 'shopt -o -p' should be sorted, etc.
VISIBLE_SHOPT_NUMS = [
    opt.index for opt in _SORTED
    if opt.builtin == 'shopt' and opt.implemented
]

OIL_UPGRADE = [opt.index for opt in _SORTED if 'oil:upgrade' in opt.groups]
OIL_ALL = [opt.index for opt in _SORTED if 'oil:all' in opt.groups]
STRICT_ALL = [opt.index for opt in _SORTED if 'strict:all' in opt.groups]
DEFAULT_TRUE = [opt.index for opt in _SORTED if opt.default]
#print([opt.name for opt in _SORTED if opt.default])


META_OPTIONS = ['strict:all', 'oil:upgrade', 'oil:all']  # Passed to flag parser

# For printing option names to stdout.  Wrapped by frontend/consts.
OPTION_NAMES = dict((opt.index, opt.name) for opt in _SORTED)
