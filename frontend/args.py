"""
args.py - Flag, option, and arg parsing for the shell.

All existing shells have their own flag parsing, rather than using libc.

We have 3 types of flag parsing here:

  FlagSpecAndMore() -- e.g. for 'sh +u -o errexit' and 'set +u -o errexit'
  FlagSpec() -- for echo -en, read -t1.0, etc.

Examples:
  set -opipefail  # not allowed, space required
  read -t1.0  # allowed

Things that getopt/optparse don't support:

- accepts +o +n for 'set' and bin/osh
  - pushd and popd also uses +, although it's not an arg.
- parses args -- well argparse is supposed to do this
- maybe: integrate with usage
- maybe: integrate with flags

optparse:
  - has option groups (Go flag package has flagset)

NOTES about builtins:
- eval and echo implicitly join their args.  We don't want that.
  - option strict-eval and strict-echo
- bash is inconsistent about checking for extra args
  - exit 1 2 complains, but pushd /lib /bin just ignores second argument
  - it has a no_args() function that isn't called everywhere.  It's not
    declarative.

TODO:
  - Autogenerate help from help='' fields.  Usage line like FlagSpec('echo [-en]')

GNU notes:

- Consider adding GNU-style option to interleave flags and args?
  - Not sure I like this.
- GNU getopt has fuzzy matching for long flags.  I think we should rely
  on good completion instead.

Bash notes:

bashgetopt.c codes:
  leading +: allow options
  : requires argument
  ; argument may be missing
  # numeric argument

However I don't see these used anywhere!  I only see ':' used.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc, loc_t, CompoundWord
from _devbuild.gen.value_asdl import (value, value_e, value_t)

from core.error import e_usage
from frontend import match
from mycpp import mops
from mycpp.mylib import log, tagswitch, iteritems

_ = log

from typing import (cast, Tuple, Optional, Dict, List, Any, TYPE_CHECKING)
if TYPE_CHECKING:
    from frontend import flag_spec
    OptChange = Tuple[str, bool]

# TODO: Move to flag_spec?  We use flag_type_t
String = 1
Int = 2
Float = 3  # e.g. for read -t timeout value
Bool = 4


class _Attributes(object):
    """Object to hold flags.

    TODO: FlagSpec doesn't need this; only FlagSpecAndMore.
    """

    def __init__(self, defaults):
        # type: (Dict[str, value_t]) -> None

        # New style
        self.attrs = {}  # type: Dict[str, value_t]

        self.opt_changes = []  # type: List[OptChange]  # -o errexit +o nounset
        self.shopt_changes = [
        ]  # type: List[OptChange]  # -O nullglob +O nullglob
        self.show_options = False  # 'set -o' without an argument
        self.actions = []  # type: List[str]  # for compgen -A
        self.saw_double_dash = False  # for set --
        for name, v in iteritems(defaults):
            self.Set(name, v)

    def SetTrue(self, name):
        # type: (str) -> None
        self.Set(name, value.Bool(True))

    def Set(self, name, val):
        # type: (str, value_t) -> None

        # debug-completion -> debug_completion
        name = name.replace('-', '_')

        # similar hack to avoid C++ keyword in frontend/flag_gen.py
        if name == 'extern':
            name = 'extern_'

        self.attrs[name] = val

        if 0:
            # Backward compatibility!
            with tagswitch(val) as case:
                if case(value_e.Undef):
                    py_val = None  # type: Any
                elif case(value_e.Bool):
                    py_val = cast(value.Bool, val).b
                elif case(value_e.Int):
                    py_val = cast(value.Int, val).i
                elif case(value_e.Float):
                    py_val = cast(value.Float, val).f
                elif case(value_e.Str):
                    py_val = cast(value.Str, val).s
                else:
                    raise AssertionError(val)

            setattr(self, name, py_val)

    def __repr__(self):
        # type: () -> str
        return '<_Attributes %s>' % self.__dict__


class Reader(object):
    """Wrapper for argv.

    Modified by both the parsing loop and various actions.

    The caller of the flags parser can continue to use it after flag parsing is
    done to get args.
    """

    def __init__(self, argv, locs=None):
        # type: (List[str], Optional[List[CompoundWord]]) -> None
        self.argv = argv
        self.locs = locs
        self.n = len(argv)
        self.i = 0

    def __repr__(self):
        # type: () -> str
        return '<args.Reader %r %d>' % (self.argv, self.i)

    def Next(self):
        # type: () -> None
        """Advance."""
        self.i += 1

    def Peek(self):
        # type: () -> Optional[str]
        """Return the next token, or None if there are no more.

        None is your SENTINEL for parsing.
        """
        if self.i >= self.n:
            return None
        else:
            return self.argv[self.i]

    def Peek2(self):
        # type: () -> Tuple[Optional[str], loc_t]
        """Return the next token, or None if there are no more.

        None is your SENTINEL for parsing.
        """
        if self.i >= self.n:
            return None, loc.Missing
        else:
            return self.argv[self.i], self.locs[self.i]

    def ReadRequired(self, error_msg):
        # type: (str) -> str
        arg = self.Peek()
        if arg is None:
            # point at argv[0]
            e_usage(error_msg, self._FirstLocation())
        self.Next()
        return arg

    def ReadRequired2(self, error_msg):
        # type: (str) -> Tuple[str, loc_t]
        arg = self.Peek()
        if arg is None:
            # point at argv[0]
            e_usage(error_msg, self._FirstLocation())
        location = self.locs[self.i]
        self.Next()
        return arg, location

    def Rest(self):
        # type: () -> List[str]
        """Return the rest of the arguments."""
        return self.argv[self.i:]

    def Rest2(self):
        # type: () -> Tuple[List[str], List[CompoundWord]]
        """Return the rest of the arguments."""
        return self.argv[self.i:], self.locs[self.i:]

    def AtEnd(self):
        # type: () -> bool
        return self.i >= self.n  # must be >= and not ==

    def Done(self):
        # type: () -> None
        if not self.AtEnd():
            e_usage('got too many arguments', self.Location())

    def _FirstLocation(self):
        # type: () -> loc_t
        if self.locs is not None and self.locs[0] is not None:
            return self.locs[0]
        else:
            return loc.Missing

    def Location(self):
        # type: () -> loc_t
        if self.locs is not None:
            if self.i == self.n:
                i = self.n - 1  # if the last arg is missing, point at the one before
            else:
                i = self.i
            if self.locs[i] is not None:
                return self.locs[i]
            else:
                return loc.Missing
        else:
            return loc.Missing


class _Action(object):
    """What is done when a flag or option is detected."""

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches.

        Args:
          prefix: '-' or '+'
          suffix: ',' for -d,
          arg_r: Reader() (rename to Input or InputReader?)
          out: _Attributes() -- the thing we want to set

        Returns:
          True if flag parsing should be aborted.
        """
        raise NotImplementedError()


class _ArgAction(_Action):

    def __init__(self, name, quit_parsing_flags, valid=None):
        # type: (str, bool, Optional[List[str]]) -> None
        """
        Args:
          quit_parsing_flags: Stop parsing args after this one.  for sh -c.
            python -c behaves the same way.
        """
        self.name = name
        self.quit_parsing_flags = quit_parsing_flags
        self.valid = valid

    def _Value(self, arg, location):
        # type: (str, loc_t) -> value_t
        raise NotImplementedError()

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches."""
        if attached_arg is not None:  # for the ',' in -d,
            arg = attached_arg
        else:
            arg_r.Next()
            arg = arg_r.Peek()
            if arg is None:
                e_usage('expected argument to %r' % ('-' + self.name),
                        arg_r.Location())

        val = self._Value(arg, arg_r.Location())
        out.Set(self.name, val)
        return self.quit_parsing_flags


class SetToInt(_ArgAction):

    def __init__(self, name):
        # type: (str) -> None
        # repeat defaults for C++ translation
        _ArgAction.__init__(self, name, False, valid=None)

    def _Value(self, arg, location):
        # type: (str, loc_t) -> value_t
        if match.LooksLikeInteger(arg):
            ok, i = mops.FromStr2(arg)
            if not ok:
                e_usage('Integer too big: %s' % arg, location)
        else:
            e_usage(
                'expected integer after %s, got %r' % ('-' + self.name, arg),
                location)

        # So far all our int values are > 0, so use -1 as the 'unset' value
        # corner case: this treats -0 as 0!
        if mops.Greater(mops.BigInt(0), i):
            e_usage('got invalid integer for %s: %s' % ('-' + self.name, arg),
                    location)
        return value.Int(i)


class SetToFloat(_ArgAction):

    def __init__(self, name):
        # type: (str) -> None
        # repeat defaults for C++ translation
        _ArgAction.__init__(self, name, False, valid=None)

    def _Value(self, arg, location):
        # type: (str, loc_t) -> value_t
        try:
            f = float(arg)
        except ValueError:
            e_usage(
                'expected number after %r, got %r' % ('-' + self.name, arg),
                location)
        # So far all our float values are > 0, so use -1.0 as the 'unset' value
        # corner case: this treats -0.0 as 0.0!
        if f < 0:
            e_usage('got invalid float for %s: %s' % ('-' + self.name, arg),
                    location)
        return value.Float(f)


class SetToString(_ArgAction):

    def __init__(self, name, quit_parsing_flags, valid=None):
        # type: (str, bool, Optional[List[str]]) -> None
        _ArgAction.__init__(self, name, quit_parsing_flags, valid=valid)

    def _Value(self, arg, location):
        # type: (str, loc_t) -> value_t
        if self.valid is not None and arg not in self.valid:
            e_usage(
                'got invalid argument %r to %r, expected one of: %s' %
                (arg, ('-' + self.name), '|'.join(self.valid)), location)
        return value.Str(arg)


class SetAttachedBool(_Action):

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches."""

        # TODO: Delete this part?  Is this eqvuivalent to SetToTrue?
        #
        # We're not using Go-like --verbose=1, --verbose, or --verbose=0
        #
        # 'attached_arg' is also used for -t0 though, which is weird

        if attached_arg is not None:  # '0' in --verbose=0
            if attached_arg in ('0', 'F', 'false',
                                'False'):  # TODO: incorrect translation
                b = False
            elif attached_arg in ('1', 'T', 'true', 'Talse'):
                b = True
            else:
                e_usage(
                    'got invalid argument to boolean flag: %r' % attached_arg,
                    loc.Missing)
        else:
            b = True

        out.Set(self.name, value.Bool(b))
        return False


class SetToTrue(_Action):

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches."""
        out.SetTrue(self.name)
        return False


class SetOption(_Action):
    """Set an option to a boolean, for 'set +e'."""

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches."""
        b = (attached_arg == '-')
        out.opt_changes.append((self.name, b))
        return False


class SetNamedOption(_Action):
    """Set a named option to a boolean, for 'set +o errexit'."""

    def __init__(self, shopt=False):
        # type: (bool) -> None
        self.names = []  # type: List[str]
        self.shopt = shopt  # is it sh -o (set) or sh -O (shopt)?

    def ArgName(self, name):
        # type: (str) -> None
        self.names.append(name)

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches."""
        b = (attached_arg == '-')
        #log('SetNamedOption %r %r %r', prefix, suffix, arg_r)
        arg_r.Next()  # always advance
        arg = arg_r.Peek()
        if arg is None:
            # triggers on 'set -O' in addition to 'set -o' (meh OK)
            out.show_options = True
            return True  # quit parsing

        attr_name = arg  # Note: validation is done elsewhere
        if len(self.names) and attr_name not in self.names:
            e_usage('Invalid option %r' % arg, loc.Missing)
        changes = out.shopt_changes if self.shopt else out.opt_changes
        changes.append((attr_name, b))
        return False


class SetAction(_Action):
    """For compgen -f."""

    def __init__(self, name):
        # type: (str) -> None
        self.name = name

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        out.actions.append(self.name)
        return False


class SetNamedAction(_Action):
    """For compgen -A file."""

    def __init__(self):
        # type: () -> None
        self.names = []  # type: List[str]

    def ArgName(self, name):
        # type: (str) -> None
        self.names.append(name)

    def OnMatch(self, attached_arg, arg_r, out):
        # type: (Optional[str], Reader, _Attributes) -> bool
        """Called when the flag matches."""
        arg_r.Next()  # always advance
        arg = arg_r.Peek()
        if arg is None:
            e_usage('Expected argument for action', loc.Missing)

        attr_name = arg
        # Validate the option name against a list of valid names.
        if len(self.names) and attr_name not in self.names:
            e_usage('Invalid action name %r' % arg, loc.Missing)
        out.actions.append(attr_name)
        return False


def Parse(spec, arg_r):
    # type: (flag_spec._FlagSpec, Reader) -> _Attributes

    # NOTE about -:
    # 'set -' ignores it, vs set
    # 'unset -' or 'export -' seems to treat it as a variable name
    out = _Attributes(spec.defaults)

    while not arg_r.AtEnd():
        arg = arg_r.Peek()
        if arg == '--':
            out.saw_double_dash = True
            arg_r.Next()
            break

        # Only accept -- if there are any long flags defined
        if len(spec.actions_long) and arg.startswith('--'):
            pos = arg.find('=', 2)
            if pos == -1:
                suffix = None  # type: Optional[str]
                flag_name = arg[2:]  # strip off --
            else:
                suffix = arg[pos + 1:]
                flag_name = arg[2:pos]

            action = spec.actions_long.get(flag_name)
            if action is None:
                e_usage('got invalid flag %r' % arg, arg_r.Location())

            action.OnMatch(suffix, arg_r, out)
            arg_r.Next()
            continue

        elif arg.startswith('-') and len(arg) > 1:
            n = len(arg)
            for i in xrange(1, n):  # parse flag combos like -rx
                ch = arg[i]

                if ch == '0':
                    ch = 'Z'  # hack for read -0

                if ch in spec.plus_flags:
                    out.Set(ch, value.Str('-'))
                    continue

                if ch in spec.arity0:  # e.g. read -r
                    out.SetTrue(ch)
                    continue

                if ch in spec.arity1:  # e.g. read -t1.0
                    action = spec.arity1[ch]
                    # make sure we don't pass empty string for read -t
                    attached_arg = arg[i + 1:] if i < n - 1 else None
                    action.OnMatch(attached_arg, arg_r, out)
                    break

                e_usage("doesn't accept flag %s" % ('-' + ch),
                        arg_r.Location())

            arg_r.Next()  # next arg

        # Only accept + if there are ANY options defined, e.g. for declare +rx.
        elif len(spec.plus_flags) and arg.startswith('+') and len(arg) > 1:
            n = len(arg)
            for i in xrange(1, n):  # parse flag combos like -rx
                ch = arg[i]
                if ch in spec.plus_flags:
                    out.Set(ch, value.Str('+'))
                    continue

                e_usage("doesn't accept option %s" % ('+' + ch),
                        arg_r.Location())

            arg_r.Next()  # next arg

        else:  # a regular arg
            break

    return out


def ParseLikeEcho(spec, arg_r):
    # type: (flag_spec._FlagSpec, Reader) -> _Attributes
    """Echo is a special case.  These work: echo -n echo -en.

    - But don't respect --
    - doesn't fail when an invalid flag is passed
    """
    out = _Attributes(spec.defaults)

    while not arg_r.AtEnd():
        arg = arg_r.Peek()
        chars = arg[1:]
        if arg.startswith('-') and len(chars):
            # Check if it looks like -en or not.  TODO: could optimize this.
            done = False
            for c in chars:
                if c not in spec.arity0:
                    done = True
                    break
            if done:
                break

            for ch in chars:
                out.SetTrue(ch)

        else:
            break  # Looks like an arg

        arg_r.Next()  # next arg

    return out


def ParseMore(spec, arg_r):
    # type: (flag_spec._FlagSpecAndMore, Reader) -> _Attributes
    """Return attributes and an index.

    Respects +, like set +eu

    We do NOT respect:

    WRONG: sh -cecho    OK: sh -c echo
    WRONG: set -opipefail     OK: set -o pipefail

    But we do accept these

    set -euo pipefail
    set -oeu pipefail
    set -oo pipefail errexit
    """
    out = _Attributes(spec.defaults)

    quit = False
    while not arg_r.AtEnd():
        arg = arg_r.Peek()
        if arg == '--':
            out.saw_double_dash = True
            arg_r.Next()
            break

        if arg.startswith('--'):
            action = spec.actions_long.get(arg[2:])
            if action is None:
                e_usage('got invalid flag %r' % arg, arg_r.Location())

            # Note: not parsing --foo=bar as attached_arg, as above
            action.OnMatch(None, arg_r, out)
            arg_r.Next()
            continue

        # corner case: sh +c is also accepted!
        if (arg.startswith('-') or arg.startswith('+')) and len(arg) > 1:
            # note: we're not handling sh -cecho  (no space) as an argument
            # It complains about a missing argument

            char0 = arg[0]

            # TODO: set - - empty
            for ch in arg[1:]:
                #log('ch %r arg_r %s', ch, arg_r)
                action = spec.actions_short.get(ch)
                if action is None:
                    e_usage('got invalid flag %r' % ('-' + ch),
                            arg_r.Location())

                attached_arg = char0 if ch in spec.plus_flags else None
                quit = action.OnMatch(attached_arg, arg_r, out)
            arg_r.Next()  # process the next flag

            if quit:
                break
            else:
                continue

        break  # it's a regular arg

    return out
