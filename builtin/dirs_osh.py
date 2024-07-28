from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from core import error
from core.error import e_usage
from core import pyos
from core import state
from display import ui
from core import vm
from frontend import flag_util
from frontend import typed_args
from mycpp.mylib import log
from pylib import os_path

import libc
import posix_ as posix

from typing import List, Optional, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from osh.cmd_eval import CommandEvaluator

_ = log


class DirStack(object):
    """For pushd/popd/dirs."""

    def __init__(self):
        # type: () -> None
        self.stack = []  # type: List[str]
        self.Reset()  # Invariant: it always has at least ONE entry.

    def Reset(self):
        # type: () -> None
        """ For dirs -c """
        del self.stack[:]
        self.stack.append(posix.getcwd())

    def Replace(self, d):
        # type: (str) -> None
        """ For cd / """
        self.stack[-1] = d

    def Push(self, entry):
        # type: (str) -> None
        self.stack.append(entry)

    def Pop(self):
        # type: () -> Optional[str]
        if len(self.stack) <= 1:
            return None
        self.stack.pop()  # remove last
        return self.stack[-1]  # return second to last

    def Iter(self):
        # type: () -> List[str]
        """Iterate in reverse order."""
        # mycpp REWRITE:
        #return reversed(self.stack)
        ret = []  # type: List[str]
        ret.extend(self.stack)
        ret.reverse()
        return ret


class ctx_CdBlock(object):

    def __init__(self, dir_stack, dest_dir, mem, errfmt, out_errs):
        # type: (DirStack, str, state.Mem, ui.ErrorFormatter, List[bool]) -> None
        dir_stack.Push(dest_dir)

        self.dir_stack = dir_stack
        self.mem = mem
        self.errfmt = errfmt
        self.out_errs = out_errs

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        _PopDirStack('cd', self.mem, self.dir_stack, self.errfmt,
                     self.out_errs)


class Cd(vm._Builtin):

    def __init__(self, mem, dir_stack, cmd_ev, errfmt):
        # type: (state.Mem, DirStack, CommandEvaluator, ui.ErrorFormatter) -> None
        self.mem = mem
        self.dir_stack = dir_stack
        self.cmd_ev = cmd_ev  # To run blocks
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('cd',
                                             cmd_val,
                                             accept_typed_args=True)
        arg = arg_types.cd(attrs.attrs)

        # If a block is passed, we do additional syntax checks
        cmd = typed_args.OptionalBlock(cmd_val)

        dest_dir, arg_loc = arg_r.Peek2()
        if dest_dir is None:
            if cmd:
                raise error.Usage(
                    'requires an argument when a block is passed',
                    cmd_val.arg_locs[0])
            else:
                try:
                    dest_dir = state.GetString(self.mem, 'HOME')
                except error.Runtime as e:
                    self.errfmt.Print_(e.UserErrorString())
                    return 1

        # At most 1 arg is accepted
        arg_r.Next()
        extra, extra_loc = arg_r.Peek2()
        if extra is not None:
            raise error.Usage('got too many arguments', extra_loc)

        if dest_dir == '-':
            try:
                dest_dir = state.GetString(self.mem, 'OLDPWD')
                print(dest_dir)  # Shells print the directory
            except error.Runtime as e:
                self.errfmt.Print_(e.UserErrorString())
                return 1

        try:
            pwd = state.GetString(self.mem, 'PWD')
        except error.Runtime as e:
            self.errfmt.Print_(e.UserErrorString())
            return 1

        # Calculate new directory, chdir() to it, then set PWD to it.  NOTE: We
        # can't call posix.getcwd() because it can raise OSError if the
        # directory was removed (ENOENT.)
        abspath = os_path.join(pwd, dest_dir)  # make it absolute, for cd ..
        if arg.P:
            # -P means resolve symbolic links, then process '..'
            real_dest_dir = libc.realpath(abspath)
        else:
            # -L means process '..' first.  This just does string manipulation.
            # (But realpath afterward isn't correct?)
            real_dest_dir = os_path.normpath(abspath)

        err_num = pyos.Chdir(real_dest_dir)
        if err_num != 0:
            self.errfmt.Print_("cd %r: %s" %
                               (real_dest_dir, posix.strerror(err_num)),
                               blame_loc=arg_loc)
            return 1

        state.ExportGlobalString(self.mem, 'PWD', real_dest_dir)

        # WEIRD: We need a copy that is NOT PWD, because the user could mutate
        # PWD.  Other shells use global variables.
        self.mem.SetPwd(real_dest_dir)

        if cmd:
            out_errs = []  # type: List[bool]
            with ctx_CdBlock(self.dir_stack, real_dest_dir, self.mem,
                             self.errfmt, out_errs):
                unused = self.cmd_ev.EvalCommand(cmd)
            if len(out_errs):
                return 1

        else:  # No block
            state.ExportGlobalString(self.mem, 'OLDPWD', pwd)
            self.dir_stack.Replace(real_dest_dir)  # for pushd/popd/dirs

        return 0


WITH_LINE_NUMBERS = 1
WITHOUT_LINE_NUMBERS = 2
SINGLE_LINE = 3


def _PrintDirStack(dir_stack, style, home_dir):
    # type: (DirStack, int, Optional[str]) -> None
    """ Helper for 'dirs' builtin """

    if style == WITH_LINE_NUMBERS:
        for i, entry in enumerate(dir_stack.Iter()):
            print('%2d  %s' % (i, ui.PrettyDir(entry, home_dir)))

    elif style == WITHOUT_LINE_NUMBERS:
        for entry in dir_stack.Iter():
            print(ui.PrettyDir(entry, home_dir))

    elif style == SINGLE_LINE:
        parts = [ui.PrettyDir(entry, home_dir) for entry in dir_stack.Iter()]
        s = ' '.join(parts)
        print(s)


class Pushd(vm._Builtin):

    def __init__(self, mem, dir_stack, errfmt):
        # type: (state.Mem, DirStack, ui.ErrorFormatter) -> None
        self.mem = mem
        self.dir_stack = dir_stack
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('pushd', cmd_val)

        dir_arg, dir_arg_loc = arg_r.Peek2()
        if dir_arg is None:
            # TODO: It's suppose to try another dir before doing this?
            self.errfmt.Print_('pushd: no other directory')
            # bash oddly returns 1, not 2
            return 1

        arg_r.Next()
        extra, extra_loc = arg_r.Peek2()
        if extra is not None:
            e_usage('got too many arguments', extra_loc)

        # TODO: 'cd' uses normpath?  Is that inconsistent?
        dest_dir = os_path.abspath(dir_arg)
        err_num = pyos.Chdir(dest_dir)
        if err_num != 0:
            self.errfmt.Print_("pushd: %r: %s" %
                               (dest_dir, posix.strerror(err_num)),
                               blame_loc=dir_arg_loc)
            return 1

        self.dir_stack.Push(dest_dir)
        _PrintDirStack(self.dir_stack, SINGLE_LINE,
                       state.MaybeString(self.mem, 'HOME'))
        state.ExportGlobalString(self.mem, 'PWD', dest_dir)
        self.mem.SetPwd(dest_dir)
        return 0


def _PopDirStack(label, mem, dir_stack, errfmt, out_errs):
    # type: (str, state.Mem, DirStack, ui.ErrorFormatter, List[bool]) -> bool
    """ Helper for popd and cd { ... } """
    dest_dir = dir_stack.Pop()
    if dest_dir is None:
        errfmt.Print_('%s: directory stack is empty' % label)
        out_errs.append(True)  # "return" to caller
        return False

    err_num = pyos.Chdir(dest_dir)
    if err_num != 0:
        # Happens if a directory is deleted in pushing and popping
        errfmt.Print_('%s: %r: %s' %
                      (label, dest_dir, posix.strerror(err_num)))
        out_errs.append(True)  # "return" to caller
        return False

    state.SetGlobalString(mem, 'PWD', dest_dir)
    mem.SetPwd(dest_dir)
    return True


class Popd(vm._Builtin):

    def __init__(self, mem, dir_stack, errfmt):
        # type: (state.Mem, DirStack, ui.ErrorFormatter) -> None
        self.mem = mem
        self.dir_stack = dir_stack
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('pushd', cmd_val)

        extra, extra_loc = arg_r.Peek2()
        if extra is not None:
            e_usage('got extra argument', extra_loc)

        out_errs = []  # type: List[bool]
        _PopDirStack('popd', self.mem, self.dir_stack, self.errfmt, out_errs)
        if len(out_errs):
            return 1  # error

        _PrintDirStack(self.dir_stack, SINGLE_LINE,
                       state.MaybeString(self.mem, ('HOME')))
        return 0


class Dirs(vm._Builtin):

    def __init__(self, mem, dir_stack, errfmt):
        # type: (state.Mem, DirStack, ui.ErrorFormatter) -> None
        self.mem = mem
        self.dir_stack = dir_stack
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('dirs', cmd_val)
        arg = arg_types.dirs(attrs.attrs)

        home_dir = state.MaybeString(self.mem, 'HOME')
        style = SINGLE_LINE

        # Following bash order of flag priority
        if arg.l:
            home_dir = None  # disable pretty ~
        if arg.c:
            self.dir_stack.Reset()
            return 0
        elif arg.v:
            style = WITH_LINE_NUMBERS
        elif arg.p:
            style = WITHOUT_LINE_NUMBERS

        _PrintDirStack(self.dir_stack, style, home_dir)
        return 0


class Pwd(vm._Builtin):
    """
  NOTE: pwd doesn't just call getcwd(), which returns a "physical" dir (not a
  symlink).
  """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('pwd', cmd_val)
        arg = arg_types.pwd(attrs.attrs)

        # NOTE: 'pwd' will succeed even if the directory has disappeared.  Other
        # shells behave that way too.
        pwd = self.mem.pwd

        # '-L' is the default behavior; no need to check it
        # TODO: ensure that if multiple flags are provided, the *last* one overrides
        # the others
        if arg.P:
            pwd = libc.realpath(pwd)
        print(pwd)
        return 0
