from __future__ import print_function

from errno import EINTR

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import (span_e, cmd_value)
from _devbuild.gen.syntax_asdl import source, loc_t
from _devbuild.gen.value_asdl import value, LeftName
from core import alloc
from core import error
from core.error import e_die
from core import pyos
from core import pyutil
from core import state
from display import ui
from core import vm
from frontend import flag_util
from frontend import reader
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, STDIN_FILENO

import posix_ as posix

from typing import Tuple, List, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import span_t
    from frontend.parse_lib import ParseContext
    from frontend import args
    from osh.cmd_eval import CommandEvaluator
    from osh.split import SplitContext

_ = log

# The read builtin splits using IFS.
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
# _ReadPortion, and ReadLineSlowly
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


def _ReadPortion(delim_byte, max_chars, cmd_ev):
    # type: (int, int, CommandEvaluator) -> Tuple[str, bool]
    """Read a portion of stdin.

    Reads until delimiter or max_chars, which ever comes first. Will ignore
    max_chars if it's set to -1.

    The delimiter is not included in the result.
    """
    eof = False
    ch_array = []  # type: List[int]
    bytes_read = 0
    while True:
        if max_chars >= 0 and bytes_read >= max_chars:
            break

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

        bytes_read += 1

    return pyutil.ChArrayToString(ch_array), eof


def ReadLineSlowly(cmd_ev, with_eol=True):
    # type: (CommandEvaluator, bool) -> Tuple[str, bool]
    """Read a line from stdin, unbuffered 

    sys.stdin.readline() in Python has its own buffering which is incompatible
    with shell semantics.  dash, mksh, and zsh all read a single byte at a time
    with read(0, 1).
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

        else:
            ch_array.append(ch)

        if ch == pyos.NEWLINE_CH:
            if not with_eol:
                ch_array.pop()
            break

    return pyutil.ChArrayToString(ch_array), eof


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
                # Retry only.  Like read --line (and command sub), read --all
                # doesn't run traps.  It would be a bit weird to run every 4096
                # bytes.
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

    # Was --qsn, might be restored as --j8-word or --j8-line
    if 0:
        #from data_lang import qsn_native
        def _MaybeDecodeLine(self, line):
            # type: (str) -> str
            """Raises error.Parse if line isn't valid."""

            # Lines that don't start with a single quote aren't QSN.  They may
            # contain a single quote internally, like:
            #
            # Fool's Gold
            if not line.startswith("'"):
                return line

            arena = self.parse_ctx.arena
            line_reader = reader.StringLineReader(line, arena)
            lexer = self.parse_ctx.MakeLexer(line_reader)

            # The parser only yields valid tokens:
            #     Char_OneChar, Char_Hex, Char_UBraced
            # So we can use word_compile.EvalCStringToken, which is also used for
            # $''.
            # Important: we don't generate Id.Unknown_Backslash because that is valid
            # in echo -e.  We just make it Id.Unknown_Tok?

            # TODO: read location info should know about stdin, and redirects, and
            # pipelines?
            with alloc.ctx_SourceCode(arena, source.Stdin('')):
                #tokens = qsn_native.Parse(lexer)
                pass
            #tmp = [word_compile.EvalCStringToken(t) for t in tokens]
            #return ''.join(tmp)
            return ''

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        try:
            status = self._Run(cmd_val)
        except pyos.ReadError as e:  # different paths for read -d, etc.
            # don't quote code since YSH errexit will likely quote
            self.errfmt.PrintMessage("Oils read error: %s" %
                                     posix.strerror(e.err_num))
            status = 1
        except (IOError, OSError) as e:  # different paths for read -d, etc.
            self.errfmt.PrintMessage("Oils read I/O error: %s" %
                                     pyutil.strerror(e))
            status = 1
        return status

    def _ReadYsh(self, arg, arg_r, cmd_val):
        # type: (arg_types.read, args.Reader, cmd_value.Argv) -> int
        """
        Usage:

          read --all        # sets _reply
          read --all (&x)   # sets x

        Invalid for now:

          read (&x)         # YSH doesn't have token splitting
                            # we probably want read --row too
        """
        place = None  # type: value.Place

        if cmd_val.proc_args:  # read --flag (&x)
            rd = typed_args.ReaderForProc(cmd_val)
            place = rd.PosPlace()
            rd.Done()

            blame_loc = cmd_val.proc_args.typed_args.left  # type: loc_t

        else:  # read --flag
            var_name = '_reply'

            #log('VAR %s', var_name)
            blame_loc = cmd_val.arg_locs[0]
            place = value.Place(LeftName(var_name, blame_loc),
                                self.mem.TopNamespace())

        next_arg, next_loc = arg_r.Peek2()
        if next_arg is not None:
            raise error.Usage('got extra argument', next_loc)

        num_bytes = mops.BigTruncate(arg.num_bytes)
        if num_bytes != -1:  # read --num-bytes
            contents = _ReadN(num_bytes, self.cmd_ev)
            status = 0

        elif arg.raw_line:  # read --raw-line is unbuffered
            contents, eof = ReadLineSlowly(self.cmd_ev, with_eol=arg.with_eol)
            status = 1 if eof else 0

        elif arg.all:  # read --all
            contents = ReadAll()
            status = 0

        else:
            raise AssertionError()

        self.mem.SetPlace(place, value.Str(contents), blame_loc)
        return status

    def _Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('read',
                                             cmd_val,
                                             accept_typed_args=True)
        arg = arg_types.read(attrs.attrs)
        names = arg_r.Rest()

        if arg.raw_line or arg.all or mops.BigTruncate(arg.num_bytes) != -1:
            return self._ReadYsh(arg, arg_r, cmd_val)

        if cmd_val.proc_args:
            raise error.Usage(
                "doesn't accept typed args without --all, or --num-bytes",
                cmd_val.proc_args.typed_args.left)

        if arg.t >= 0.0:
            if arg.t != 0.0:
                e_die("read -t isn't implemented (except t=0)")
            else:
                return 0 if pyos.InputAvailable(STDIN_FILENO) else 1

        bits = 0
        if self.stdin_.isatty():
            # -d and -n should be unbuffered
            if arg.d is not None or mops.BigTruncate(arg.n) >= 0:
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

        # read a certain number of bytes, NOT respecting delimiter (-1 means
        # unset)
        arg_N = mops.BigTruncate(arg.N)
        if arg_N >= 0:
            s = _ReadN(arg_N, self.cmd_ev)

            if len(names):
                name = names[0]  # ignore other names

                # Clear extra names, as bash does
                for i in xrange(1, len(names)):
                    state.BuiltinSetString(self.mem, names[i], '')
            else:
                name = 'REPLY'  # default variable name

            state.BuiltinSetString(self.mem, name, s)

            # Did we read all the bytes we wanted?
            return 0 if len(s) == arg_N else 1

        do_split = False

        if len(names):
            do_split = True  # read myvar does word splitting
        else:
            # read without args does NOT split, and fills in $REPLY
            names.append('REPLY')

        if arg.a is not None:
            max_results = 0  # array can hold all parts
            do_split = True
        else:
            # Assign one part to each variable name; leftovers are assigned to
            # the last name
            max_results = len(names)

        if arg.Z:  # -0 is synonym for IFS= read -r -d ''
            do_split = False
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

        # Read MORE THAN ONE line for \ line continuation (and not read -r)
        parts = []  # type: List[mylib.BufWriter]
        join_next = False
        status = 0
        while True:
            chunk, eof = _ReadPortion(delim_byte, mops.BigTruncate(arg.n),
                                      self.cmd_ev)

            if eof:
                # status 1 to terminate loop.  (This is true even though we set
                # variables).
                status = 1

            #log('LINE %r', chunk)
            if len(chunk) == 0:
                break

            spans = self.splitter.SplitForRead(chunk, not raw, do_split)
            done, join_next = _AppendParts(chunk, spans, max_results,
                                           join_next, parts)

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
                #log('read: %s = %s', var_name, s)
                state.BuiltinSetString(self.mem, var_name, s)

        return status
