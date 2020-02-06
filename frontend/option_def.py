#!/usr/bin/env python2
"""
option_def.py
"""
from __future__ import print_function

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
SET_OPTION_NAMES = [name for _, name in SET_OPTIONS]

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

# Used to be simple_echo -- do we need it?
_AGGRESSIVE_RUNTIME_OPTIONS = []  # type: List[str]

# No-ops for bash compatibility
NO_OPS = [
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
] + NO_OPS + _STRICT_OPTION_NAMES + _BASIC_RUNTIME_OPTIONS + \
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

PARSE_OPTION_NAMES = _BASIC_PARSE_OPTIONS + _AGGRESSIVE_PARSE_OPTIONS

OIL_AGGRESSIVE = _AGGRESSIVE_PARSE_OPTIONS + _AGGRESSIVE_RUNTIME_OPTIONS

# errexit is also set, but handled separately
_MORE_STRICT = ['nounset', 'pipefail', 'inherit_errexit']

OIL_BASIC = (
    _STRICT_OPTION_NAMES + _MORE_STRICT + _BASIC_PARSE_OPTIONS +
    _BASIC_RUNTIME_OPTIONS
)
# nullglob instead of simple-word-eval
ALL_STRICT = _STRICT_OPTION_NAMES + _MORE_STRICT + ['nullglob']

# Used in builtin_pure.py
ALL_SHOPT_OPTIONS = SHOPT_OPTION_NAMES + PARSE_OPTION_NAMES

META_OPTIONS = ['strict:all', 'oil:basic', 'oil:all']  # Passed to flag parser
