"""main_loop.py.

Variants:
  main_loop.Interactive()    calls ParseInteractiveLine() and ExecuteAndCatch()
  main_loop.Batch()          calls ParseLogicalLine() and ExecuteAndCatch()
  main_loop.Headless()       calls Batch() like eval and source.
                                   We want 'echo 1\necho 2\n' to work, so we
                                   don't bother with "the PS2 problem".
  main_loop.ParseWholeFile() calls ParseLogicalLine().  Used by osh -n.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import (command, command_t, parse_result,
                                       parse_result_e, source)
from core import alloc
from core import error
from core import process
from core import state
from core import util
from display import ui
from frontend import reader
from osh import cmd_eval
from mycpp import mylib
from mycpp.mylib import log, print_stderr, probe, tagswitch

import fanos
import posix_ as posix

from typing import cast, Any, List, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    from core.comp_ui import _IDisplay
    from core import process
    from frontend import parse_lib
    from osh import cmd_parse
    from osh import cmd_eval
    from osh.prompt import UserPlugin

_ = log


class ctx_Descriptors(object):
    """Save and restore descriptor state for the headless EVAL command."""

    def __init__(self, fds):
        # type: (List[int]) -> None

        self.saved0 = process.SaveFd(0)
        self.saved1 = process.SaveFd(1)
        self.saved2 = process.SaveFd(2)

        #ShowDescriptorState('BEFORE')
        posix.dup2(fds[0], 0)
        posix.dup2(fds[1], 1)
        posix.dup2(fds[2], 2)

        self.fds = fds

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None

        # Restore
        posix.dup2(self.saved0, 0)
        posix.dup2(self.saved1, 1)
        posix.dup2(self.saved2, 2)

        # Restoration done, so close
        posix.close(self.saved0)
        posix.close(self.saved1)
        posix.close(self.saved2)

        # And close descriptors we were passed
        posix.close(self.fds[0])
        posix.close(self.fds[1])
        posix.close(self.fds[2])


def fanos_log(msg):
    # type: (str) -> None
    print_stderr('[FANOS] %s' % msg)


def ShowDescriptorState(label):
    # type: (str) -> None
    if mylib.PYTHON:
        import os  # Our posix fork doesn't have os.system
        import time
        time.sleep(0.01)  # prevent interleaving

        pid = posix.getpid()
        print_stderr(label + ' (PID %d)' % pid)

        os.system('ls -l /proc/%d/fd >&2' % pid)

        time.sleep(0.01)  # prevent interleaving


class Headless(object):
    """Main loop for headless mode."""

    def __init__(self, cmd_ev, parse_ctx, errfmt):
        # type: (cmd_eval.CommandEvaluator, parse_lib.ParseContext, ui.ErrorFormatter) -> None
        self.cmd_ev = cmd_ev
        self.parse_ctx = parse_ctx
        self.errfmt = errfmt

    def Loop(self):
        # type: () -> int
        try:
            return self._Loop()
        except ValueError as e:
            fanos.send(1, 'ERROR %s' % e)
            return 1

    def EVAL(self, arg):
        # type: (str) -> str

        # This logic is similar to the 'eval' builtin in osh/builtin_meta.

        # Note: we're not using the InteractiveLineReader, so there's no history
        # expansion.  It would be nice if there was a way for the client to use
        # that.
        line_reader = reader.StringLineReader(arg, self.parse_ctx.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader)

        # Status is unused; $_ can be queried by the headless client
        unused_status = Batch(self.cmd_ev, c_parser, self.errfmt, 0)

        return ''  # result is always 'OK ' since there was no protocol error

    def _Loop(self):
        # type: () -> int
        fanos_log(
            'Connect stdin and stdout to one end of socketpair() and send control messages.  osh writes debug messages (like this one) to stderr.'
        )

        fd_out = []  # type: List[int]
        while True:
            try:
                blob = fanos.recv(0, fd_out)
            except ValueError as e:
                fanos_log('protocol error: %s' % e)
                raise  # higher level handles it

            if blob is None:
                fanos_log('EOF received')
                break

            fanos_log('received blob %r' % blob)
            if ' ' in blob:
                bs = blob.split(' ', 1)
                command = bs[0]
                arg = bs[1]
            else:
                command = blob
                arg = ''

            if command == 'GETPID':
                reply = str(posix.getpid())

            elif command == 'EVAL':
                #fanos_log('arg %r', arg)

                if len(fd_out) != 3:
                    raise ValueError('Expected 3 file descriptors')

                for fd in fd_out:
                    fanos_log('received descriptor %d' % fd)

                with ctx_Descriptors(fd_out):
                    reply = self.EVAL(arg)

                #ShowDescriptorState('RESTORED')

            # Note: lang == 'osh' or lang == 'ysh' puts this in different modes.
            # Do we also need 'complete --osh' and 'complete --ysh' ?
            elif command == 'PARSE':
                # Just parse
                reply = 'TODO:PARSE'

            else:
                fanos_log('Invalid command %r' % command)
                raise ValueError('Invalid command %r' % command)

            fanos.send(1, b'OK %s' % reply)
            del fd_out[:]  # reset for next iteration

        return 0


def Interactive(
        flag,  # type: arg_types.main
        cmd_ev,  # type: cmd_eval.CommandEvaluator 
        c_parser,  # type: cmd_parse.CommandParser
        display,  # type: _IDisplay
        prompt_plugin,  # type: UserPlugin
        waiter,  # type: process.Waiter
        errfmt,  # type: ui.ErrorFormatter
):
    # type: (...) -> int
    status = 0
    done = False
    while not done:
        mylib.MaybeCollect()  # manual GC point

        # - This loop has a an odd structure because we want to do cleanup
        #   after every 'break'.  (The ones without 'done = True' were
        #   'continue')
        # - display.EraseLines() needs to be called BEFORE displaying anything, so
        #   it appears in all branches.

        while True:  # ONLY EXECUTES ONCE
            quit = False
            prompt_plugin.Run()
            try:
                # may raise HistoryError or ParseError
                result = c_parser.ParseInteractiveLine()
                UP_result = result
                with tagswitch(result) as case:
                    if case(parse_result_e.EmptyLine):
                        display.EraseLines()
                        # POSIX shell behavior: waitpid(-1) and show job "Done"
                        # messages
                        waiter.PollForEvents()
                        quit = True
                    elif case(parse_result_e.Eof):
                        display.EraseLines()
                        done = True
                        quit = True
                    elif case(parse_result_e.Node):
                        result = cast(parse_result.Node, UP_result)
                        node = result.cmd
                    else:
                        raise AssertionError()

            except util.HistoryError as e:  # e.g. expansion failed
                # Where this happens:
                # for i in 1 2 3; do
                #   !invalid
                # done
                display.EraseLines()
                print(e.UserErrorString())
                quit = True
            except error.Parse as e:
                display.EraseLines()
                errfmt.PrettyPrintError(e)
                status = 2
                cmd_ev.mem.SetLastStatus(status)
                quit = True
            except KeyboardInterrupt:  # thrown by InteractiveLineReader._GetLine()
                # TODO: We probably want to change terminal settings so ^C is printed.
                # For now, just print a newline.
                #
                # WITHOUT GNU readline, the ^C is printed.  So we need to make
                # the 2 cases consistent.
                print('')

                if 0:
                    from core import pyos
                    pyos.FlushStdout()

                display.EraseLines()
                quit = True

            if quit:
                break

            display.EraseLines()  # Clear candidates right before executing

            # to debug the slightly different interactive prasing
            if cmd_ev.exec_opts.noexec():
                ui.PrintAst(node, flag)
                break

            try:
                is_return, _ = cmd_ev.ExecuteAndCatch(node, 0)
            except KeyboardInterrupt:  # issue 467, Ctrl-C during $(sleep 1)
                is_return = False
                display.EraseLines()

                # http://www.tldp.org/LDP/abs/html/exitcodes.html
                # bash gives 130, dash gives 0, zsh gives 1.
                status = 130  # 128 + 2

                cmd_ev.mem.SetLastStatus(status)
                break

            status = cmd_ev.LastStatus()

            waiter.PollForEvents()

            if is_return:
                done = True
                break

            break  # QUIT LOOP after one iteration.

        # After every "logical line", no lines will be referenced by the Arena.
        # Tokens in the LST still point to many lines, but lines with only comment
        # or whitespace won't be reachable, so the GC will free them.
        c_parser.arena.DiscardLines()

        cmd_ev.RunPendingTraps()  # Run trap handlers even if we get just ENTER

        # Cleanup after every command (or failed command).

        # Reset internal newline state.
        c_parser.Reset()
        c_parser.ResetInputObjects()

        display.Reset()  # clears dupes and number of lines last displayed

        # TODO: Replace this with a shell hook?  with 'trap', or it could be just
        # like command_not_found.  The hook can be 'echo $?' or something more
        # complicated, i.e. with timestamps.
        if flag.print_status:
            print('STATUS\t%r' % status)

    return status


def Batch(
        cmd_ev,  # type: cmd_eval.CommandEvaluator
        c_parser,  # type: cmd_parse.CommandParser
        errfmt,  # type: ui.ErrorFormatter
        cmd_flags=0,  # type: int
):
    # type: (...) -> int
    """
    source, eval, etc. treat parse errors as error code 2.  But the --eval flag does not.
    """
    was_parsed, status = Batch2(cmd_ev, c_parser, errfmt, cmd_flags=cmd_flags)
    if not was_parsed:
        return 2
    return status


def Batch2(
        cmd_ev,  # type: cmd_eval.CommandEvaluator
        c_parser,  # type: cmd_parse.CommandParser
        errfmt,  # type: ui.ErrorFormatter
        cmd_flags=0,  # type: int
):
    # type: (...) -> Tuple[bool, int]
    """Loop for batch execution.

    Returns:
      int status, e.g. 2 on parse error

    Can this be combined with interactive loop?  Differences:

    - Handling of parse errors.
    - Have to detect here docs at the end?

    Not a problem:
    - Get rid of --print-status and --show-ast for now
    - Get rid of EOF difference

    TODO:
    - Do source / eval need this?
      - 'source' needs to parse incrementally so that aliases are respected
      - I doubt 'eval' does!  You can test it.
    - In contrast, 'trap' should parse up front?
    - What about $() ?
    """
    was_parsed = True
    status = 0
    while True:
        probe('main_loop', 'Batch_parse_enter')
        try:
            node = c_parser.ParseLogicalLine()  # can raise ParseError
            if node is None:  # EOF
                c_parser.CheckForPendingHereDocs()  # can raise ParseError
                break
        except error.Parse as e:
            errfmt.PrettyPrintError(e)
            was_parsed = False
            status = -1  # invalid value
            break

        # After every "logical line", no lines will be referenced by the Arena.
        # Tokens in the LST still point to many lines, but lines with only comment
        # or whitespace won't be reachable, so the GC will free them.
        c_parser.arena.DiscardLines()

        # Only optimize if we're on the last line like -c "echo hi" etc.
        if (cmd_flags & cmd_eval.IsMainProgram and
                c_parser.line_reader.LastLineHint()):
            cmd_flags |= cmd_eval.OptimizeSubshells
            if not cmd_ev.exec_opts.verbose_errexit():
                cmd_flags |= cmd_eval.MarkLastCommands

        probe('main_loop', 'Batch_parse_exit')

        probe('main_loop', 'Batch_execute_enter')
        # can't optimize this because we haven't seen the end yet
        is_return, is_fatal = cmd_ev.ExecuteAndCatch(node, cmd_flags)
        status = cmd_ev.LastStatus()
        # e.g. 'return' in middle of script, or divide by zero
        if is_return or is_fatal:
            break
        probe('main_loop', 'Batch_execute_exit')

        probe('main_loop', 'Batch_collect_enter')
        mylib.MaybeCollect()  # manual GC point
        probe('main_loop', 'Batch_collect_exit')

    return was_parsed, status


def ParseWholeFile(c_parser):
    # type: (cmd_parse.CommandParser) -> command_t
    """Parse an entire shell script.

    This uses the same logic as Batch().  Used by:
    - osh -n
    - oshc translate
    - Used by 'trap' to store code.  But 'source' and 'eval' use Batch().

    Note: it does NOT call DiscardLines
    """
    children = []  # type: List[command_t]
    while True:
        node = c_parser.ParseLogicalLine()  # can raise ParseError
        if node is None:  # EOF
            c_parser.CheckForPendingHereDocs()  # can raise ParseError
            break
        children.append(node)

        mylib.MaybeCollect()  # manual GC point

    if len(children) == 1:
        return children[0]
    else:
        return command.CommandList(children)


def EvalFile(
        fs_path,  # type: str
        fd_state,  # type: process.FdState
        parse_ctx,  # type: parse_lib.ParseContext
        cmd_ev,  # type: cmd_eval.CommandEvaluator
        lang,  # type: str
):
    # type: (...) -> Tuple[bool, int]
    """Evaluate a disk file, for --eval --eval-pure

    Copied and adapted from the 'source' builtin in builtin/meta_oils.py.

    (Note that bind -x has to eval from a string, like Eval)

    Raises:
      util.UserExit
    Returns:
      ok: whether processing should continue
    """
    try:
        f = fd_state.Open(fs_path)
    except (IOError, OSError) as e:
        print_stderr("%s: Couldn't open %r for --eval: %s" %
                     (lang, fs_path, posix.strerror(e.errno)))
        return False, -1

    line_reader = reader.FileLineReader(f, cmd_ev.arena)
    c_parser = parse_ctx.MakeOshParser(line_reader)

    # TODO:
    # - Improve error locations
    # - parse error should be fatal

    with process.ctx_FileCloser(f):
        with state.ctx_Eval(cmd_ev.mem, fs_path, None,
                            None):  # set $0 to fs_path
            with state.ctx_ThisDir(cmd_ev.mem, fs_path):
                src = source.MainFile(fs_path)
                with alloc.ctx_SourceCode(cmd_ev.arena, src):
                    # May raise util.UserExit
                    was_parsed, status = Batch2(cmd_ev, c_parser,
                                                cmd_ev.errfmt)
                    if not was_parsed:
                        return False, -1

    return True, status
