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
    self.is_parse = name.startswith('parse_')
    # errexit is a special case for now
    # interactive() is an accessor
    self.is_exec = (
        implemented and not self.is_parse and name != 'errexit'
    )


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

    # TODO: Add strict_arg_parse?  For example, 'trap 1 2 3' shouldn't be
    # valid, because it has an extra argument.  Builtins are inconsistent about
    # checking this.
]

_STRICT_OPTION_NAMES = [
    # NOTE:
    # - some are PARSING: strict_glob, strict_backslash
    # - some are runtime: strict_arith, strict_word_eval

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
    'strict_echo',          # echo takes 0 or 1 arguments
    'strict_errexit',       # errexit can't be disabled in compound commands
    'strict_eval_builtin',  # eval takes exactly 1 argument
    'strict_nameref',       # trap invalid variable names
    'strict_word_eval',     # negative slices, unicode

    # Not implemented
    'strict_backslash',  # BadBackslash for echo -e, printf, PS1, etc.
    'strict_glob',       # glob_.py GlobParser has warnings
]

# These will break some programs, but the fix should be simple.

# more_errexit makes 'local foo=$(false)' and echo $(false) fail.
# By default, we have mimic bash's undesirable behavior of ignoring
# these failures, since ash copied it, and Alpine's abuild relies on it.
#
# bash 4.4 also has shopt -s inherit_errexit, which says that command subs
# inherit the value of errexit.  # I don't believe it is strict enough --
# local still needs to fail.
_BASIC_RUNTIME_OPTIONS = [
    ('simple_word_eval', False),  # No splitting (arity isn't data-dependent)
                                  # Don't reparse program data as globs
    ('dashglob', True),           # do globs return results starting with - ?
    ('more_errexit', False),      # check after command sub

    # TODO: Move this?  (not implemented yet) Anything that removes
    # functionality sould be in oil:all or oil:pure
    # only file tests (no strings), remove [, status 2
    ('simple_test_builtin', False),
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


# Oil parse options only.
_BASIC_PARSE_OPTIONS = [
    'parse_at',  # @foo, @array(a, b)
    'parse_brace',  # cd /bin { ... }
    'parse_index_expr',  # ${a[1 + f(x)]}  -- can this just be $[]?
     
    # TODO: also allow bare (x > 0) for awk dialect?
    'parse_paren',  # if (x > 0) ...

    # Should this also change r''' c''' and and c"""?  Those are hard to
    # do in command mode without changing the lexer, but useful because of
    # redirects.  Maybe r' and c' are tokens, and then you look for '' after
    # it?  If it's off and you get the token, then you change it into
    # word_part::Literal and start parsing.
    #
    # proc foo {
    #   cat << c'''
    #   hello\n
    #   '''
    # }
    'parse_rawc',  # echo r'' c''
]

# Extra stuff that breaks too many programs.
_AGGRESSIVE_PARSE_OPTIONS = [
    'parse_set',  # set x = 'var'
    'parse_equals',  # x = 'var'
]


def _Init(opt_def):
  # type: (_OptionDef) -> None

  # Note: this is in all three groups, but it's handled explicitly in
  # core/state.py.
  opt_def.Add('errexit', short_flag='e', builtin='set')

  # Two more strict options from bash's set
  opt_def.Add('nounset', short_flag='u', builtin='set', 
              groups=['strict:all', 'oil:basic', 'oil:all'])

  # bash --norc -c 'set -o' shows this is on by default
  opt_def.Add('hashall', short_flag='h', builtin='set', default=True,
              groups=['strict:all', 'oil:basic', 'oil:all'])

  opt_def.Add('pipefail', builtin='set', 
              groups=['strict:all', 'oil:basic', 'oil:all'])

  # set -o noclobber, etc.
  for short_flag, name in _OTHER_SET_OPTIONS:
    opt_def.Add(name, short_flag=short_flag, builtin='set')

  # The only one where builtin=None.  Only the shell can change it.
  opt_def.Add('interactive', builtin=None)

  #
  # shopt
  # (bash uses $BASHOPTS rather than $SHELLOPTS)
  #

  # shopt option that's not in any groups.  Note: not implemented.
  for name in ['failglob']:
    opt_def.Add(name)

  # Two strict options that from bash's shopt
  for name in ['nullglob', 'inherit_errexit']:
    opt_def.Add(name, groups=['strict:all', 'oil:basic', 'oil:all'])

  # shopt -s strict_arith, etc.
  # TODO: Some of these shouldn't be in oil:basic, like maybe strict_echo.
  for name in _STRICT_OPTION_NAMES:
    opt_def.Add(name, groups=['strict:all', 'oil:basic', 'oil:all'])

  #
  # Options that enable Oil language features
  #

  # shopt -s simple_word_eval, etc.
  for name, default in _BASIC_RUNTIME_OPTIONS:
    opt_def.Add(name, default=default, groups=['oil:basic', 'oil:all'])

  for name in _BASIC_PARSE_OPTIONS:
    opt_def.Add(name, groups=['oil:basic', 'oil:all'])

  # By default we parse 'return 2>&1', even though it does nothing in Oil.
  opt_def.Add('parse_ignored', groups=['strict:all', 'oil:basic', 'oil:all'],
              default=True)

  # Undocumented option to parse things that won't run.  For ble.sh's dynamic
  # LHS arithmetic, but can be used for other things too.
  opt_def.Add('parse_unimplemented', default=False)

  for name in _AGGRESSIVE_PARSE_OPTIONS:
    opt_def.Add(name, groups=['oil:all'])

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

# Used by core/state.py.

# TODO: Change all of these to numbers.
SET_OPTION_NAMES = sorted(
    opt.name for opt in _OPTION_DEF.opts if opt.builtin == 'set'
)

# Include the unimplemented ones
SHOPT_OPTION_NAMES = sorted(
    opt.name for opt in _OPTION_DEF.opts if opt.builtin == 'shopt'
)

PARSE_OPTION_NAMES = ParseOptNames()

# Sorted because 'shopt -o -p' should be sorted, etc.
VISIBLE_SHOPT_NAMES = sorted(
    opt.name for opt in _OPTION_DEF.opts
    if opt.builtin == 'shopt' and opt.implemented
)

OIL_BASIC = [opt.index for opt in _OPTION_DEF.opts if 'oil:basic' in opt.groups]
OIL_ALL = [opt.index for opt in _OPTION_DEF.opts if 'oil:all' in opt.groups]
STRICT_ALL = [opt.index for opt in _OPTION_DEF.opts if 'strict:all' in opt.groups]
DEFAULT_TRUE = [opt.index for opt in _OPTION_DEF.opts if opt.default]

META_OPTIONS = ['strict:all', 'oil:basic', 'oil:all']  # Passed to flag parser

