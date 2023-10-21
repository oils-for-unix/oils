from __future__ import print_function

from errno import EINTR

from _devbuild.gen import arg_types
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import value, value_t

from core.error import e_die_status
from frontend import flag_spec
from frontend import lexer
from frontend import match
from core import optview
from core import pyos
from core import vm
from mycpp import mylib
from mycpp.mylib import log
from osh import word_compile

import posix_ as posix

from typing import List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value

_ = log


class Echo(vm._Builtin):
    """echo builtin.

    shopt -s simple_echo disables -e and -n.
    """

    def __init__(self, exec_opts):
        # type: (optview.Exec) -> None
        self.exec_opts = exec_opts
        self.f = mylib.Stdout()

        # Reuse this constant instance
        self.simple_flag = None  # type: arg_types.echo

    def _SimpleFlag(self):
        # type: () -> arg_types.echo
        """For arg.e and arg.n without parsing."""
        if self.simple_flag is None:
            attrs = {}  # type: Dict[str, value_t]
            attrs['e'] = value.Bool(False)
            attrs['n'] = value.Bool(False)
            self.simple_flag = arg_types.echo(attrs)
        return self.simple_flag

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        argv = cmd_val.argv[1:]

        if self.exec_opts.simple_echo():
            # Avoid parsing -e -n
            arg = self._SimpleFlag()
        else:
            attrs, arg_r = flag_spec.ParseLikeEcho('echo', cmd_val)
            arg = arg_types.echo(attrs.attrs)
            argv = arg_r.Rest()

        backslash_c = False  # \c terminates input

        if arg.e:
            new_argv = []  # type: List[str]
            for a in argv:
                parts = []  # type: List[str]
                lex = match.EchoLexer(a)
                while not backslash_c:
                    id_, s = lex.Next()
                    if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
                        break

                    # Note: DummyToken is OK because EvalCStringToken() doesn't have any
                    # syntax errors.
                    tok = lexer.DummyToken(id_, s)
                    p = word_compile.EvalCStringToken(tok)

                    # Unusual behavior: '\c' prints what is there and aborts processing!
                    if p is None:
                        backslash_c = True
                        break

                    parts.append(p)

                new_argv.append(''.join(parts))
                if backslash_c:  # no more args either
                    break

            # Replace it
            argv = new_argv

        #log('echo argv %s', argv)
        for i, a in enumerate(argv):
            if i != 0:
                self.f.write(' ')  # arg separator
            self.f.write(a)

        if not arg.n and not backslash_c:
            self.f.write('\n')

        return 0


class Cat(vm._Builtin):
    """Internal implementation detail for $(< file).

    Maybe expose this as 'builtin cat' ?
    """

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        vm._Builtin.__init__(self)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        chunks = []  # type: List[str]
        while True:
            n, err_num = pyos.Read(0, 4096, chunks)

            if n < 0:
                if err_num == EINTR:
                    pass  # retry
                else:
                    # Like the top level IOError handler
                    e_die_status(2,
                                 'osh I/O error: %s' % posix.strerror(err_num))
                    # TODO: Maybe just return 1?

            elif n == 0:  # EOF
                break

            else:
                # Stream it to stdout
                assert len(chunks) == 1
                mylib.Stdout().write(chunks[0])
                chunks.pop()

        return 0
