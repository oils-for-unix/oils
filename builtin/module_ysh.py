from __future__ import print_function

from core import state
from display import ui
from core import vm
from frontend import flag_util
from mycpp.mylib import log

from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from core import optview

_ = log


class IsMain(vm._Builtin):
    """is-main builtin.
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        return 0 if self.mem.is_main else 1


class SourceGuard(vm._Builtin):
    """source-guard builtin.

    source-guard main || return
    """

    def __init__(self, guards, exec_opts, errfmt):
        # type: (Dict[str, bool], optview.Exec, ui.ErrorFormatter) -> None
        self.guards = guards
        self.exec_opts = exec_opts
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('source-guard', cmd_val)
        name, _ = arg_r.ReadRequired2('requires a name')
        #log('guards %s', self.guards)
        if name in self.guards:
            # already defined
            if self.exec_opts.redefine_module():
                self.errfmt.PrintMessage(
                    '(interactive) Reloading source file %r' % name)
                return 0
            else:
                return 1
        self.guards[name] = True
        return 0


class Use(vm._Builtin):
    """
    Module system with all the power of Python, but still a proc

    use util.ysh  # util is a value.Obj

    # Importing a bunch of words
    use dialect-ninja.ysh { all }  # requires 'provide' in dialect-ninja
    use dialect-github.ysh { all }

    # This declares some names
    use --extern grep sed

    # Renaming
    use util.ysh (&myutil)

    # Ignore
    use util.ysh (&_)

    # Picking specifics
    use util.ysh {
      pick log die
      pick foo (&myfoo)
    }

    # A long way to write this is:

    use util.ysh
    const log = util.log
    const die = util.die
    const myfoo = util.foo

    Another way is:
    for name in log die {
      call setVar(name, util[name])

      # value.Obj may not support [] though
      # get(propView(util), name, null) is a long way of writing it
    }

    Other considerations:

    - Statically parseable subset?  For fine-grained static tree-shaking
      - We're doing coarse dynamic tree-shaking first though

    - if TYPE_CHECKING is an issue
      - that can create circular dependencies, especially with gradual typing,
        when you go dynamic to static (like Oils did)
      - I guess you can have
        - use --static parse_lib.ysh { pick ParseContext } 
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('use', cmd_val)

        mod_path, _ = arg_r.ReadRequired2('requires a module path')

        log('m %s', mod_path)

        arg_r.Done()

        # TODO on usage:
        # - typed arg is value.Place
        # - block arg binds 'pick' and 'all'

        # TODO:
        # with ctx_Module
        # and then do something very similar to 'source'

        return 0
