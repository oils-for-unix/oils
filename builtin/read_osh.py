from __future__ import print_function

from errno import EINTR

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import (span_e, cmd_value, scope_e)
from _devbuild.gen.syntax_asdl import source, loc
from _devbuild.gen.value_asdl import value
from core import alloc
from core import error
from core.error import e_usage, e_die
from core import pyos
from core import pyutil
from core import state
from core import ui
from core import vm
from data_lang import qsn_native
from frontend import flag_spec
from frontend import location
from frontend import reader
from mycpp import mylib
from mycpp.mylib import log, STDIN_FILENO
from osh import word_compile

import posix_ as posix

from typing import Tuple, List, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import span_t
    from frontend.parse_lib import ParseContext
    from osh.cmd_eval import CommandEvaluator
    from osh.split import SplitContext

_ = log

# The Read builtin splits using IFS.
#
# Summary:
# - Split with IFS, except \ can escape them!  This is different than the
#   algorithm for splitting words (at least the way I've represented it.)

# Bash manual:
# - If there are more words than names, the remaining words and their
#   intervening delimiters are assigned to the last name.
# - If there are fewer words read from the input stream than names, the
#   remaining names are assigned empty values.
# - The characters in the value of the IFS variable are used to split the line
#   into words using the same rules the shell uses for expansion (described
# above in Word Splitting).
# - The backslash character '\' may be used to remove any special meaning for
#   the next character read and for line continuation.


def _AppendParts(
        s,  # type: str
        spans,  # type: List[Tuple[span_t, int]]
        max_results,  # type: int
        join_next,  # type: bool
        parts,  # type: List[mylib.BufWriter]
):
    # type: (...) -> Tuple[bool, bool]
    """Append to 'parts', for the 'read' builtin.

    Similar to _SpansToParts in osh/split.py

    Args:
      s: The original string
      spans: List of (span, end_index)
      max_results: the maximum number of parts we want
      join_next: Whether to join the next span to the previous part.  This
      happens in two cases:
        - when we have '\ '
        - and when we have more spans # than max_results.
    """
    start_index = 0
    # If the last span was black, and we get a backslash, set join_next to merge
    # two black spans.
    last_span_was_black = False

    for span_type, end_index in spans:
        if span_type == span_e.Black:
            if join_next and len(parts):
                parts[-1].write(s[start_index:end_index])
                join_next = False
            else:
                buf = mylib.BufWriter()
                buf.write(s[start_index:end_index])
                parts.append(buf)
            last_span_was_black = True

        elif span_type == span_e.Delim:
            if join_next:
                parts[-1].write(s[start_index:end_index])
                join_next = False
            last_span_was_black = False

        elif span_type == span_e.Backslash:
            if last_span_was_black:
                join_next = True
            last_span_was_black = False

        if max_results and len(parts) >= max_results:
            join_next = True

        start_index = end_index

    done = True
    if len(spans):
        #log('%s %s', s, spans)
        #log('%s', spans[-1])
        last_span_type, _ = spans[-1]
        if last_span_type == span_e.Backslash:
            done = False

    #log('PARTS %s', parts)
    return done, join_next


#
# Three read() wrappers for 'read' builtin that RunPendingTraps: _ReadN,
# _ReadUntilDelim, and ReadLineSlowly
#


def _ReadN(num_bytes, cmd_ev):
    # type: (int, CommandEvaluator) -> str
    chunks = []  # type: List[str]
    bytes_left = num_bytes
    while bytes_left > 0:
        n, err_num = pyos.Read(STDIN_FILENO, bytes_left,
                               chunks)  # read up to n bytes

        if n < 0:
            if err_num == EINTR:
                cmd_ev.RunPendingTraps()
                # retry after running traps
            else:
                raise pyos.ReadError(err_num)

        elif n == 0:  # EOF
            break

        else:
            bytes_left -= n

    return ''.join(chunks)


def _ReadUntilDelim(delim_byte, cmd_ev):
    # type: (int, CommandEvaluator) -> Tuple[str, bool]
    """Read a portion of stdin.

    Read until that delimiter, but don't include it.
    """
    eof = False
    ch_array = []  # type: List[int]
    while True:
        ch, err_num = pyos.ReadByte(0)
        if ch < 0:
            if err_num == EINTR:
                cmd_ev.RunPendingTraps()
                # retry after running traps
            else:
                raise pyos.ReadError(err_num)

        elif ch == pyos.EOF_SENTINEL:
            eof = True
            break

        elif ch == delim_byte:
            break

        else:
            ch_array.append(ch)

    return pyutil.ChArrayToString(ch_array), eof


# sys.stdin.readline() in Python has its own buffering which is incompatible
# with shell semantics.  dash, mksh, and zsh all read a single byte at a
# time with read(0, 1).

# TODO:
# - ReadLineSlowly should have keep_newline (mapfile -t)
#   - this halves memory usage!


def ReadLineSlowly(cmd_ev):
    # type: (CommandEvaluator) -> str
    """Read a line from stdin."""
    ch_array = []  # type: List[int]
    while True:
        ch, err_num = pyos.ReadByte(0)

        if ch < 0:
            if err_num == EINTR:
                cmd_ev.RunPendingTraps()
                # retry after running traps
            else:
                raise pyos.ReadError(err_num)

        elif ch == pyos.EOF_SENTINEL:
            break

        else:
            ch_array.append(ch)

        # TODO: Add option to omit newline
        if ch == pyos.NEWLINE_CH:
            break

    return pyutil.ChArrayToString(ch_array)


def ReadAll():
    # type: () -> str
    """Read all of stdin.

    Similar to command sub in core/executor.py.
    """
    chunks = []  # type: List[str]
    while True:
        n, err_num = pyos.Read(0, 4096, chunks)

        if n < 0:
            if err_num == EINTR:
                # Retry only.  Like read --line (and command sub), read --all doesn't
                # run traps.  It would be a bit weird to run every 4096 bytes.
                pass
            else:
                raise pyos.ReadError(err_num)

        elif n == 0:  # EOF
            break

    return ''.join(chunks)


class ctx_TermAttrs(object):

    def __init__(self, fd, local_modes):
        # type: (int, int) -> None
        self.fd = fd

        # We change term_attrs[3] in Python, which is lflag "local modes"
        orig_local_modes, term_attrs = pyos.PushTermAttrs(fd, local_modes)

        # Workaround: destructured assignment into members doesn't work
        self.orig_local_modes = orig_local_modes
        self.term_attrs = term_attrs

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        pyos.PopTermAttrs(self.fd, self.orig_local_modes, self.term_attrs)


class Read(vm._Builtin):

    def __init__(
            self,
            splitter,  # type: SplitContext
            mem,  # type: state.Mem
            parse_ctx,  # type: ParseContext
            cmd_ev,  # type: CommandEvaluator
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.splitter = splitter
        self.mem = mem
        self.parse_ctx = parse_ctx
        self.cmd_ev = cmd_ev
        self.errfmt = errfmt
        self.stdin_ = mylib.Stdin()

    def _Line(self, arg, var_name):
        # type: (arg_types.read, str) -> int
        """For read --line."""

        # Use an optimized C implementation rather than ReadLineSlowly, which
        # calls ReadByte() over and over.
        line = pyos.ReadLine()
        if len(line) == 0:  # EOF
            return 1

        if not arg.with_eol:
            if line.endswith('\r\n'):
                line = line[:-2]
            elif line.endswith('\n'):
                line = line[:-1]

        # Lines that don't start with a single quote aren't QSN.  They may contain
        # a single quote internally, like:
        #
        # Fool's Gold
        if arg.q and line.startswith("'"):
            arena = self.parse_ctx.arena
            line_reader = reader.StringLineReader(line, arena)
            lexer = self.parse_ctx.MakeLexer(line_reader)

            # The parser only yields valid tokens:
            #     Char_Literals, Char_OneChar, Char_Hex, Char_UBraced
            # So we can use word_compile.EvalCStringToken, which is also used for
            # $''.
            # Important: we don't generate Id.Unknown_Backslash because that is valid
            # in echo -e.  We just make it Id.Unknown_Tok?
            try:
                # TODO: read should know about stdin, and redirects, and pipelines?
                with alloc.ctx_SourceCode(arena, source.Stdin('')):
                    tokens = qsn_native.Parse(lexer)
            except error.Parse as e:
                self.errfmt.PrettyPrintError(e)
                return 1
            tmp = [word_compile.EvalCStringToken(t) for t in tokens]
            line = ''.join(tmp)

        lhs = location.LName(var_name)
        self.mem.SetNamed(lhs, value.Str(line), scope_e.LocalOnly)
        return 0

    def _All(self, var_name):
        # type: (str) -> int
        contents = ReadAll()

        # No error conditions?

        lhs = location.LName(var_name)
        self.mem.SetNamed(lhs, value.Str(contents), scope_e.LocalOnly)
        return 0

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        try:
            status = self._Run(cmd_val)
        except pyos.ReadError as e:  # different paths for read -d, etc.
            # don't quote code since YSH errexit will likely quote
            self.errfmt.PrintMessage("read error: %s" %
                                     posix.strerror(e.err_num))
            status = 1
        return status

    def _Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_spec.ParseCmdVal('read', cmd_val)
        arg = arg_types.read(attrs.attrs)
        names = arg_r.Rest()

        # Don't respect any of the other options here?  This is buffered I/O.
        if arg.line:  # read --line
            var_name, var_loc = arg_r.Peek2()
            if var_name is None:
                var_name = '_line'
            else:
                if var_name.startswith(':'):  # optional : sigil
                    var_name = var_name[1:]
                arg_r.Next()

            next_arg, next_loc = arg_r.Peek2()
            if next_arg is not None:
                raise error.Usage('got extra argument', next_loc)

            return self._Line(arg, var_name)

        if arg.q:
            e_usage('--qsn can only be used with --line', loc.Missing)

        if arg.all:  # read --all
            var_name, var_loc = arg_r.Peek2()
            if var_name is None:
                var_name = '_all'
            else:
                if var_name.startswith(':'):  # optional : sigil
                    var_name = var_name[1:]
                arg_r.Next()

            next_arg, next_loc = arg_r.Peek2()
            if next_arg is not None:
                raise error.Usage('got extra argument', next_loc)

            return self._All(var_name)

        if arg.q:
            e_usage('--qsn not implemented yet', loc.Missing)

        if arg.t >= 0.0:
            if arg.t != 0.0:
                e_die("read -t isn't implemented (except t=0)")
            else:
                return 0 if pyos.InputAvailable(STDIN_FILENO) else 1

        bits = 0
        if self.stdin_.isatty():
            # -d and -n should be unbuffered
            if arg.d is not None or arg.n >= 0:
                bits |= pyos.TERM_ICANON
            if arg.s:  # silent
                bits |= pyos.TERM_ECHO

            if arg.p is not None:  # only if tty
                mylib.Stderr().write(arg.p)

        if bits == 0:
            status = self._Read(arg, names)
        else:
            with ctx_TermAttrs(STDIN_FILENO, ~bits):
                status = self._Read(arg, names)
        return status

    def _Read(self, arg, names):
        # type: (arg_types.read, List[str]) -> int

        if arg.n >= 0:  # read a certain number of bytes (-1 means unset)
            if len(names):
                name = names[0]
            else:
                name = 'REPLY'  # default variable name

            s = _ReadN(arg.n, self.cmd_ev)

            state.BuiltinSetString(self.mem, name, s)

            # Did we read all the bytes we wanted?
            return 0 if len(s) == arg.n else 1

        if len(names) == 0:
            names.append('REPLY')

        # leftover words assigned to the last name
        if arg.a is not None:
            max_results = 0  # no max
        else:
            max_results = len(names)

        if arg.Z:  # -0 is synonym for -r -d ''
            raw = True
            delim_byte = 0
        else:
            raw = arg.r
            if arg.d is not None:
                if len(arg.d):
                    delim_byte = ord(arg.d[0])
                else:
                    delim_byte = 0  # -d '' delimits by NUL
            else:
                delim_byte = pyos.NEWLINE_CH  # read a line

        # We have to read more than one line if there is a line continuation (and
        # it's not -r).
        parts = []  # type: List[mylib.BufWriter]
        join_next = False
        status = 0
        while True:
            line, eof = _ReadUntilDelim(delim_byte, self.cmd_ev)

            if eof:
                # status 1 to terminate loop.  (This is true even though we set
                # variables).
                status = 1

            #log('LINE %r', line)
            if len(line) == 0:
                break

            spans = self.splitter.SplitForRead(line, not raw)
            done, join_next = _AppendParts(line, spans, max_results, join_next,
                                           parts)

            #log('PARTS %s continued %s', parts, continued)
            if done:
                break

        entries = [buf.getvalue() for buf in parts]
        num_parts = len(entries)
        if arg.a is not None:
            state.BuiltinSetArray(self.mem, arg.a, entries)
        else:
            for i in xrange(max_results):
                if i < num_parts:
                    s = entries[i]
                else:
                    s = ''  # if there are too many variables
                var_name = names[i]
                if var_name.startswith(':'):
                    var_name = var_name[1:]
                #log('read: %s = %s', var_name, s)
                state.BuiltinSetString(self.mem, var_name, s)

        return status
