"""
dev.py - Devtools / introspection.
"""
from __future__ import print_function

from _devbuild.gen.option_asdl import option_i, builtin_i, builtin_t
from _devbuild.gen.runtime_asdl import (cmd_value, scope_e, trace, trace_e,
                                        trace_t)
from _devbuild.gen.syntax_asdl import assign_op_e, Token
from _devbuild.gen.value_asdl import (value, value_e, value_t, sh_lvalue,
                                      sh_lvalue_e, LeftName)

from core import bash_impl
from core import error
from core import bash_impl
from core import optview
from core import num
from core import state
from display import ui
from data_lang import j8
from frontend import location
from osh import word_
from data_lang import j8_lite
from pylib import os_path
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, print_stderr, log

import posix_ as posix

from typing import List, Dict, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import assign_op_t, CompoundWord
    from _devbuild.gen.runtime_asdl import scope_t
    from _devbuild.gen.value_asdl import sh_lvalue_t
    from core import alloc
    from core.error import _ErrorWithLocation
    from core import process
    from core import util
    from frontend.parse_lib import ParseContext
    from osh.word_eval import NormalWordEvaluator
    from osh.cmd_eval import CommandEvaluator

_ = log


class CrashDumper(object):
    """Controls if we collect a crash dump, and where we write it to.

    An object that can be serialized to JSON.

    trap CRASHDUMP upload-to-server

    # it gets written to a file first
    upload-to-server() {
      local path=$1
      curl -X POST https://osh-trace.oilshell.org  < $path
    }

    Things to dump:
    CommandEvaluator
      functions, aliases, traps, completion hooks, fd_state, dir_stack

    debug info for the source?  Or does that come elsewhere?

    Yeah I think you should have two separate files.
    - debug info for a given piece of code (needs hash)
      - this could just be the raw source files?  Does it need anything else?
      - I think it needs a hash so the VM dump can refer to it.
    - vm dump.
    - Combine those and you get a UI.

    One is constant at build time; the other is constant at runtime.
    """

    def __init__(self, crash_dump_dir, fd_state):
        # type: (str, process.FdState) -> None
        self.crash_dump_dir = crash_dump_dir
        self.fd_state = fd_state

        # whether we should collect a dump, at the highest level of the stack
        self.do_collect = bool(crash_dump_dir)
        self.collected = False  # whether we have anything to dump

        self.var_stack = None  # type: List[value_t]
        self.argv_stack = None  # type: List[value_t]
        self.debug_stack = None  # type: List[value_t]
        self.error = None  # type: Dict[str, value_t]

    def MaybeRecord(self, cmd_ev, err):
        # type: (CommandEvaluator, _ErrorWithLocation) -> None
        """Collect data for a crash dump.

        Args:
          cmd_ev: CommandEvaluator instance
          error: _ErrorWithLocation (ParseError or error.FatalRuntime)
        """
        if not self.do_collect:  # Either we already did it, or there is no file
            return

        self.var_stack, self.argv_stack, self.debug_stack = cmd_ev.mem.Dump()
        blame_tok = location.TokenFor(err.location)

        self.error = {
            'msg': value.Str(err.UserErrorString()),
        }

        if blame_tok:
            # Could also do msg % args separately, but JavaScript won't be able to
            # render that.
            self.error['source'] = value.Str(
                ui.GetLineSourceString(blame_tok.line))
            self.error['line_num'] = num.ToBig(blame_tok.line.line_num)
            self.error['line'] = value.Str(blame_tok.line.content)

        # TODO: Collect functions, aliases, etc.
        self.do_collect = False
        self.collected = True

    def MaybeDump(self, status):
        # type: (int) -> None
        """Write the dump as JSON.

        User can configure it two ways:
        - dump unconditionally -- a daily cron job.  This would be fine.
        - dump on non-zero exit code

        OILS_FAIL
        Maybe counters are different than failure

        OILS_CRASH_DUMP='function alias trap completion stack' ?
        OILS_COUNTER_DUMP='function alias trap completion'
        and then
        I think both of these should dump the (path, mtime, checksum) of the source
        they ran?  And then you can match those up with source control or whatever?
        """
        if not self.collected:
            return

        my_pid = posix.getpid()  # Get fresh PID here

        # Other things we need: the reason for the crash!  _ErrorWithLocation is
        # required I think.
        d = {
            'var_stack': value.List(self.var_stack),
            'argv_stack': value.List(self.argv_stack),
            'debug_stack': value.List(self.debug_stack),
            'error': value.Dict(self.error),
            'status': num.ToBig(status),
            'pid': num.ToBig(my_pid),
        }  # type: Dict[str, value_t]

        path = os_path.join(self.crash_dump_dir,
                            '%d-osh-crash-dump.json' % my_pid)

        # TODO: This should be JSON with unicode replacement char?
        buf = mylib.BufWriter()
        j8.PrintMessage(value.Dict(d), buf, 2)
        json_str = buf.getvalue()

        try:
            f = self.fd_state.OpenForWrite(path)
        except (IOError, OSError) as e:
            # Ignore error
            return

        f.write(json_str)

        # TODO: mylib.Writer() needs close()?  Also for DebugFile()
        #f.close()

        print_stderr('[%d] Wrote crash dump to %s' % (my_pid, path))


class ctx_Tracer(object):
    """A stack for tracing synchronous constructs."""

    def __init__(self, tracer, label, argv):
        # type: (Tracer, str, Optional[List[str]]) -> None
        self.arg = None  # type: Optional[str]
        if label in ('proc', 'module-invoke'):
            self.arg = argv[0]
        elif label in ('source', 'use'):
            self.arg = argv[1]

        tracer.PushMessage(label, argv)
        self.label = label
        self.tracer = tracer

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.tracer.PopMessage(self.label, self.arg)


def _PrintShValue(val, buf):
    # type: (value_t, mylib.BufWriter) -> None
    """Print ShAssignment values.

    NOTE: This is a bit like _PrintVariables for declare -p
    """
    # I think this should never happen because it's for ShAssignment
    result = '?'

    # Using maybe_shell_encode() because it's shell
    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Str):
            val = cast(value.Str, UP_val)
            result = j8_lite.MaybeShellEncode(val.s)

        elif case(value_e.BashArray):
            val = cast(value.BashArray, UP_val)
            result = bash_impl.BashArray_ToStrForShellPrint(val, None)

        elif case(value_e.BashAssoc):
            val = cast(value.BashAssoc, UP_val)
            result = bash_impl.BashAssoc_ToStrForShellPrint(val)

        elif case(value_e.SparseArray):
            val = cast(value.SparseArray, UP_val)
            result = bash_impl.SparseArray_ToStrForShellPrint(val)

    buf.write(result)


def PrintShellArgv(argv, buf):
    # type: (List[str], mylib.BufWriter) -> None
    for i, arg in enumerate(argv):
        if i != 0:
            buf.write(' ')
        buf.write(j8_lite.MaybeShellEncode(arg))


def _PrintYshArgv(argv, buf):
    # type: (List[str], mylib.BufWriter) -> None

    # We're printing $'hi\n' for OSH, but we might want to print u'hi\n' or
    # b'\n' for YSH.  We could have a shopt --set xtrace_j8 or something.
    #
    # This used to be xtrace_rich, but I think that was too subtle.

    for arg in argv:
        buf.write(' ')
        # TODO: use unquoted -> POSIX '' -> b''
        # This would use JSON "", which CONFLICTS with shell.  So we need
        # another function.
        #j8.EncodeString(arg, buf, unquoted_ok=True)

        buf.write(j8_lite.MaybeShellEncode(arg))
    buf.write('\n')


class MultiTracer(object):
    """ Manages multi-process tracing and dumping.

    Use case:

    TODO: write a shim for everything that autoconf starts out with

    (1) How do you discover what is shelled out to? 
        - you need a MULTIPROCESS tracing and MULTIPROCESS errors

    OILS_TRACE_DIR=_tmp/foo OILS_TRACE_STREAMS=xtrace:completion:gc \
    OILS_TRACE_DUMPS=crash:argv0 \
      osh ./configure

    - Streams are written continuously, they are O(n)
    - Dumps are written once per shell process, they are O(1). This includes metrics.

    (2) Use that dump to generate stubs in _tmp/stubs
        They will invoke benchmarks/time-helper, so we get timing and memory use
        for each program. 

    (3) ORIG_PATH=$PATH PATH=_tmp/stubs:$PATH osh ./configure

    THen the stub looks like this?

    #!/bin/sh 
    # _tmp/stubs/cc1

    PATH=$ORIG_PATH time-helper -x -e -- cc1 "$@"
    """

    def __init__(self, shell_pid, out_dir, dumps, streams, fd_state):
        # type: (int, str, str, str, process.FdState) -> None
        """
        out_dir could be auto-generated from root PID?
        """
        # All of these may be empty string
        self.out_dir = out_dir
        self.dumps = dumps
        self.streams = streams
        self.fd_state = fd_state

        self.this_pid = shell_pid

        # This is what we consider an O(1) metric.  Technically a shell program
        # could run forever and keep invoking different binaries, but that is
        # unlikely.  I guess we could limit it to 1,000 or 10,000 artifically
        # or something.
        self.hist_argv0 = {}  # type: Dict[str, int]

    def OnNewProcess(self, child_pid):
        # type: (int) -> None
        """
        Right now we call this from
           Process::StartProcess -> tracer.SetChildPid()
        It would be more accurate to call it from SubProgramThunk.

        TODO: do we need a compound PID?
        """
        self.this_pid = child_pid
        # each process keep track of direct children
        self.hist_argv0.clear()

    def EmitArgv0(self, argv0):
        # type: (str) -> None

        # TODO: Should we have word 0 in the source, and the FILE the $PATH
        # lookup resolved to?

        if argv0 not in self.hist_argv0:
            self.hist_argv0[argv0] = 1
        else:
            # TODO: mycpp doesn't allow +=
            self.hist_argv0[argv0] = self.hist_argv0[argv0] + 1

    def WriteDumps(self):
        # type: () -> None
        if len(self.out_dir) == 0:
            return

        # TSV8 table might be nicer for this

        metric_argv0 = []  # type: List[value_t]
        for argv0, count in iteritems(self.hist_argv0):
            a = value.Str(argv0)
            c = value.Int(mops.IntWiden(count))
            d = {'argv0': a, 'count': c}
            metric_argv0.append(value.Dict(d))

        # Other things we need: the reason for the crash!  _ErrorWithLocation is
        # required I think.
        j = {
            'pid': value.Int(mops.IntWiden(self.this_pid)),
            'metric_argv0': value.List(metric_argv0),
        }  # type: Dict[str, value_t]

        # dumps are named $PID.$channel.json
        path = os_path.join(self.out_dir, '%d.argv0.json' % self.this_pid)

        buf = mylib.BufWriter()
        j8.PrintMessage(value.Dict(j), buf, 2)
        json8_str = buf.getvalue()

        try:
            f = self.fd_state.OpenForWrite(path)
        except (IOError, OSError) as e:
            # Ignore error
            return

        f.write(json8_str)
        f.close()

        print_stderr('[%d] Wrote metrics dump to %s' % (self.this_pid, path))


class Tracer(object):
    """For OSH set -x, and YSH hierarchical, parsable tracing.

    See doc/xtrace.md for details.

    - TODO: Connect it somehow to tracers for other processes.  So you can make
      an HTML report offline.
      - Could inherit SHX_*

    https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html#Bash-Variables

    Other hooks:

    - Command completion starts other processes
    - YSH command constructs: BareDecl, VarDecl, Mutation, Expr
    """

    def __init__(
            self,
            parse_ctx,  # type: ParseContext
            exec_opts,  # type: optview.Exec
            mutable_opts,  # type: state.MutableOpts
            mem,  # type: state.Mem
            f,  # type: util._DebugFile
            multi_trace,  # type: MultiTracer
    ):
        # type: (...) -> None
        """
        trace_dir comes from OILS_TRACE_DIR
        """
        self.parse_ctx = parse_ctx
        self.exec_opts = exec_opts
        self.mutable_opts = mutable_opts
        self.mem = mem
        self.f = f  # can be stderr, the --debug-file, etc.
        self.multi_trace = multi_trace

        self.word_ev = None  # type: NormalWordEvaluator

        self.ind = 0  # changed by process, proc, source, eval
        self.indents = ['']  # "pooled" to avoid allocations

        # PS4 value -> CompoundWord.  PS4 is scoped.
        self.parse_cache = {}  # type: Dict[str, CompoundWord]

        # Mutate objects to save allocations
        self.val_indent = value.Str('')
        self.val_punct = value.Str('')
        # TODO: show something for root process by default?  INTERLEAVED output
        # can be confusing, e.g. debugging traps in forkred subinterpreter
        # created by a pipeline.
        self.val_pid_str = value.Str('')  # mutated by SetProcess

        # Can these be global constants?  I don't think we have that in ASDL yet.
        self.lval_indent = location.LName('SHX_indent')
        self.lval_punct = location.LName('SHX_punct')
        self.lval_pid_str = location.LName('SHX_pid_str')

    def CheckCircularDeps(self):
        # type: () -> None
        assert self.word_ev is not None

    def _EvalPS4(self, punct):
        # type: (str) -> str
        """The prefix of each line."""
        val = self.mem.GetValue('PS4')
        if val.tag() == value_e.Str:
            ps4 = cast(value.Str, val).s
        else:
            ps4 = ''

        # NOTE: This cache is slightly broken because aliases are mutable!  I think
        # that is more or less harmless though.
        ps4_word = self.parse_cache.get(ps4)
        if ps4_word is None:
            # We have to parse this at runtime.  PS4 should usually remain constant.
            w_parser = self.parse_ctx.MakeWordParserForPlugin(ps4)

            # NOTE: could use source.Variable, like $PS1 prompt does
            try:
                ps4_word = w_parser.ReadForPlugin()
            except error.Parse as e:
                ps4_word = word_.ErrorWord("<ERROR: Can't parse PS4: %s>" %
                                           e.UserErrorString())
            self.parse_cache[ps4] = ps4_word

        # Mutate objects to save allocations
        if self.exec_opts.xtrace_rich():
            self.val_indent.s = self.indents[self.ind]
        else:
            self.val_indent.s = ''
        self.val_punct.s = punct

        # Prevent infinite loop when PS4 has command sub!
        assert self.exec_opts.xtrace()  # We shouldn't call this unless it's on

        # TODO: Remove allocation for [] ?
        with state.ctx_Option(self.mutable_opts, [option_i.xtrace], False):
            with state.ctx_Temp(self.mem):
                self.mem.SetNamed(self.lval_indent, self.val_indent,
                                  scope_e.LocalOnly)
                self.mem.SetNamed(self.lval_punct, self.val_punct,
                                  scope_e.LocalOnly)
                self.mem.SetNamed(self.lval_pid_str, self.val_pid_str,
                                  scope_e.LocalOnly)
                prefix = self.word_ev.EvalForPlugin(ps4_word)
        return prefix.s

    def _Inc(self):
        # type: () -> None
        self.ind += 1
        if self.ind >= len(self.indents):  # make sure there are enough
            self.indents.append('  ' * self.ind)

    def _Dec(self):
        # type: () -> None
        self.ind -= 1

    def _ShTraceBegin(self):
        # type: () -> Optional[mylib.BufWriter]
        if not self.exec_opts.xtrace() or not self.exec_opts.xtrace_details():
            return None

        # Note: bash repeats the + for command sub, eval, source.  Other shells
        # don't do it.  Leave this out for now.
        prefix = self._EvalPS4('+')
        buf = mylib.BufWriter()
        buf.write(prefix)
        return buf

    def _RichTraceBegin(self, punct):
        # type: (str) -> Optional[mylib.BufWriter]
        """For the stack printed by xtrace_rich."""
        if not self.exec_opts.xtrace() or not self.exec_opts.xtrace_rich():
            return None

        prefix = self._EvalPS4(punct)
        buf = mylib.BufWriter()
        buf.write(prefix)
        return buf

    def OnProcessStart(self, pid, why):
        # type: (int, trace_t) -> None
        """
        In parent, Process::StartProcess calls us with child PID
        """
        UP_why = why
        with tagswitch(why) as case:
            if case(trace_e.External):
                why = cast(trace.External, UP_why)

                # There is the empty argv case of $(true), but it's never external
                assert len(why.argv) > 0
                self.multi_trace.EmitArgv0(why.argv[0])

        buf = self._RichTraceBegin('|')
        if not buf:
            return

        # TODO: ProcessSub and PipelinePart are commonly command.Simple, and also
        # Fork/ForkWait through the BraceGroup.  We could print those argv arrays.

        with tagswitch(why) as case:
            # Synchronous cases
            if case(trace_e.External):
                why = cast(trace.External, UP_why)
                buf.write('command %d:' % pid)
                _PrintYshArgv(why.argv, buf)

            # Everything below is the same.  Could use string literals?
            elif case(trace_e.ForkWait):
                buf.write('forkwait %d\n' % pid)
            elif case(trace_e.CommandSub):
                buf.write('command sub %d\n' % pid)

            # Async cases
            elif case(trace_e.ProcessSub):
                buf.write('proc sub %d\n' % pid)
            elif case(trace_e.HereDoc):
                buf.write('here doc %d\n' % pid)
            elif case(trace_e.Fork):
                buf.write('fork %d\n' % pid)
            elif case(trace_e.PipelinePart):
                buf.write('part %d\n' % pid)

            else:
                raise AssertionError()

        self.f.write(buf.getvalue())

    def OnProcessEnd(self, pid, status):
        # type: (int, int) -> None
        buf = self._RichTraceBegin(';')
        if not buf:
            return

        buf.write('process %d: status %d\n' % (pid, status))
        self.f.write(buf.getvalue())

    def OnNewProcess(self, child_pid):
        # type: (int) -> None
        """All trace lines have a PID prefix, except those from the root
        process."""
        self.val_pid_str.s = ' %d' % child_pid
        self._Inc()
        self.multi_trace.OnNewProcess(child_pid)

    def PushMessage(self, label, argv):
        # type: (str, Optional[List[str]]) -> None
        """For synchronous constructs that aren't processes."""
        buf = self._RichTraceBegin('>')
        if buf:
            buf.write(label)
            if label in ('proc', 'module-invoke'):
                _PrintYshArgv(argv, buf)
            elif label in ('source', 'use'):
                _PrintYshArgv(argv[1:], buf)
            elif label == 'wait':
                _PrintYshArgv(argv[1:], buf)
            else:
                buf.write('\n')
            self.f.write(buf.getvalue())

        self._Inc()

    def PopMessage(self, label, arg):
        # type: (str, Optional[str]) -> None
        """For synchronous constructs that aren't processes.

        e.g. source or proc
        """
        self._Dec()

        buf = self._RichTraceBegin('<')
        if buf:
            buf.write(label)
            if arg is not None:
                buf.write(' ')
                # TODO: use unquoted -> POSIX '' -> b''
                buf.write(j8_lite.MaybeShellEncode(arg))
            buf.write('\n')
            self.f.write(buf.getvalue())

    def OtherMessage(self, message):
        # type: (str) -> None
        """Can be used when receiving signals."""
        buf = self._RichTraceBegin('!')
        if not buf:
            return

        buf.write(message)
        buf.write('\n')
        self.f.write(buf.getvalue())

    def OnExec(self, argv):
        # type: (List[str]) -> None
        buf = self._RichTraceBegin('.')
        if not buf:
            return
        buf.write('exec')
        _PrintYshArgv(argv, buf)
        self.f.write(buf.getvalue())

    def OnBuiltin(self, builtin_id, argv):
        # type: (builtin_t, List[str]) -> None
        if builtin_id in (builtin_i.eval, builtin_i.source, builtin_i.use,
                          builtin_i.wait):
            return  # These builtins are handled separately

        buf = self._RichTraceBegin('.')
        if not buf:
            return
        buf.write('builtin')
        _PrintYshArgv(argv, buf)
        self.f.write(buf.getvalue())

    #
    # Shell Tracing That Begins with _ShTraceBegin
    #

    def OnSimpleCommand(self, argv):
        # type: (List[str]) -> None
        """For legacy set -x.

        Called before we know if it's a builtin, external, or proc.
        """
        buf = self._ShTraceBegin()
        if not buf:
            return

        # Redundant with OnProcessStart (external), PushMessage (proc), and OnBuiltin
        if self.exec_opts.xtrace_rich():
            return

        # Legacy: Use SHELL encoding, NOT _PrintYshArgv()
        PrintShellArgv(argv, buf)
        buf.write('\n')
        self.f.write(buf.getvalue())

    def OnAssignBuiltin(self, cmd_val):
        # type: (cmd_value.Assign) -> None
        buf = self._ShTraceBegin()
        if not buf:
            return

        for i, arg in enumerate(cmd_val.argv):
            if i != 0:
                buf.write(' ')
            buf.write(arg)

        for pair in cmd_val.pairs:
            buf.write(' ')
            buf.write(pair.var_name)
            buf.write('+=' if pair.plus_eq else '=')
            if pair.rval:
                _PrintShValue(pair.rval, buf)

        buf.write('\n')
        self.f.write(buf.getvalue())

    def OnShAssignment(self, lval, op, val, flags, which_scopes):
        # type: (sh_lvalue_t, assign_op_t, value_t, int, scope_t) -> None
        buf = self._ShTraceBegin()
        if not buf:
            return

        left = '?'
        UP_lval = lval
        with tagswitch(lval) as case:
            if case(sh_lvalue_e.Var):
                lval = cast(LeftName, UP_lval)
                left = lval.name
            elif case(sh_lvalue_e.Indexed):
                lval = cast(sh_lvalue.Indexed, UP_lval)
                left = '%s[%d]' % (lval.name, lval.index)
            elif case(sh_lvalue_e.Keyed):
                lval = cast(sh_lvalue.Keyed, UP_lval)
                left = '%s[%s]' % (lval.name, j8_lite.MaybeShellEncode(
                    lval.key))
        buf.write(left)

        # Only two possibilities here
        buf.write('+=' if op == assign_op_e.PlusEqual else '=')

        _PrintShValue(val, buf)

        buf.write('\n')
        self.f.write(buf.getvalue())

    def OnControlFlow(self, keyword, arg):
        # type: (str, int) -> None

        # This is NOT affected by xtrace_rich or xtrace_details.  Works in both.
        if not self.exec_opts.xtrace():
            return

        prefix = self._EvalPS4('+')
        buf = mylib.BufWriter()
        buf.write(prefix)

        buf.write(keyword)
        buf.write(' ')
        buf.write(str(arg))  # Note: 'return' is equivalent to 'return 0'
        buf.write('\n')

        self.f.write(buf.getvalue())

    def PrintSourceCode(self, left_tok, right_tok, arena):
        # type: (Token, Token, alloc.Arena) -> None
        """For (( )) and [[ ]].

        Bash traces these.
        """
        buf = self._ShTraceBegin()
        if not buf:
            return

        line = left_tok.line.content
        start = left_tok.col

        if left_tok.line == right_tok.line:
            end = right_tok.col + right_tok.length
            buf.write(line[start:end])
        else:
            # Print first line only
            end = -1 if line.endswith('\n') else len(line)
            buf.write(line[start:end])
            buf.write(' ...')

        buf.write('\n')
        self.f.write(buf.getvalue())
