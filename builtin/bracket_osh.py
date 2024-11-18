"""Builtin_bracket.py."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import loc, word, word_e, word_t, bool_expr
from _devbuild.gen.types_asdl import lex_mode_e
from _devbuild.gen.value_asdl import value

from core import error
from core.error import e_usage, p_die
from core import vm
from frontend import match
from frontend import typed_args
from mycpp.mylib import log
from osh import bool_parse
from osh import sh_expr_eval
from osh import word_parse
from osh import word_eval

_ = log

from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from _devbuild.gen.syntax_asdl import bool_expr_t
    from _devbuild.gen.types_asdl import lex_mode_t
    from core import optview
    from core import state
    from display import ui


class _StringWordEmitter(word_parse.WordEmitter):
    """For test/[, we need a word parser that returns String.

    The BoolParser calls word_.BoolId(w), and deals with Kind.BoolUnary,
    Kind.BoolBinary, etc.  This is instead of Compound/Token (as in the
    [[ case.
    """

    def __init__(self, cmd_val):
        # type: (cmd_value.Argv) -> None
        self.cmd_val = cmd_val
        self.i = 0
        self.n = len(cmd_val.argv)

    def ReadWord(self, unused_lex_mode):
        # type: (lex_mode_t) -> word.String
        """Interface for bool_parse.py.

        TODO: This should probably be word_t
        """
        if self.i == self.n:
            # Does it make sense to define Eof_Argv or something?
            # TODO: Add a way to show this location.
            w = word.String(Id.Eof_Real, '', None)
            return w

        #log('ARGV %s i %d', self.argv, self.i)
        s = self.cmd_val.argv[self.i]
        arg_loc = self.cmd_val.arg_locs[self.i]

        self.i += 1

        # chained lookup; default is an operand word
        id_ = match.BracketUnary(s)
        if id_ == Id.Undefined_Tok:
            id_ = match.BracketBinary(s)
        if id_ == Id.Undefined_Tok:
            id_ = match.BracketOther(s)
        if id_ == Id.Undefined_Tok:
            id_ = Id.Word_Compound

        return word.String(id_, s, arg_loc)

    def Read(self):
        # type: () -> word.String
        """Interface used for special cases below."""
        return self.ReadWord(lex_mode_e.ShCommand)

    def Peek(self, offset):
        # type: (int) -> str
        """For special cases."""
        return self.cmd_val.argv[self.i + offset]

    def Rewind(self, offset):
        # type: (int) -> None
        """For special cases."""
        self.i -= offset


class _WordEvaluator(word_eval.StringWordEvaluator):

    def __init__(self):
        # type: () -> None
        word_eval.StringWordEvaluator.__init__(self)

    def EvalWordToString(self, w, eval_flags=0):
        # type: (word_t, int) -> value.Str
        # do_fnmatch: for the [[ == ]] semantics which we don't have!
        # I think I need another type of node
        # Maybe it should be BuiltinEqual and BuiltinDEqual?  Parse it into a
        # different tree.
        assert w.tag() == word_e.String
        string_word = cast(word.String, w)
        return value.Str(string_word.s)


def _TwoArgs(w_parser):
    # type: (_StringWordEmitter) -> bool_expr_t
    """Returns an expression tree to be evaluated."""
    w0 = w_parser.Read()
    w1 = w_parser.Read()

    s0 = w0.s
    if s0 == '!':
        return bool_expr.LogicalNot(bool_expr.WordTest(w1))

    unary_id = Id.Undefined_Tok

    # YSH prefers long flags
    if w0.s.startswith('--'):
        if s0 == '--dir':
            unary_id = Id.BoolUnary_d
        elif s0 == '--exists':
            unary_id = Id.BoolUnary_e
        elif s0 == '--file':
            unary_id = Id.BoolUnary_f
        elif s0 == '--symlink':
            unary_id = Id.BoolUnary_L
        elif s0 == '--true':
            unary_id = Id.BoolUnary_true
        elif s0 == '--false':
            unary_id = Id.BoolUnary_false

    if unary_id == Id.Undefined_Tok:
        unary_id = match.BracketUnary(w0.s)

    if unary_id == Id.Undefined_Tok:
        p_die('Expected unary operator, got %r (2 args)' % w0.s, loc.Word(w0))

    return bool_expr.Unary(unary_id, w1)


def _ThreeArgs(w_parser):
    # type: (_StringWordEmitter) -> bool_expr_t
    """Returns an expression tree to be evaluated."""
    w0 = w_parser.Read()
    w1 = w_parser.Read()
    w2 = w_parser.Read()

    # NOTE: Order is important here.

    binary_id = match.BracketBinary(w1.s)
    if binary_id != Id.Undefined_Tok:
        return bool_expr.Binary(binary_id, w0, w2)

    if w1.s == '-a':
        return bool_expr.LogicalAnd(bool_expr.WordTest(w0),
                                    bool_expr.WordTest(w2))

    if w1.s == '-o':
        return bool_expr.LogicalOr(bool_expr.WordTest(w0),
                                   bool_expr.WordTest(w2))

    if w0.s == '!':
        w_parser.Rewind(2)
        child = _TwoArgs(w_parser)
        return bool_expr.LogicalNot(child)

    if w0.s == '(' and w2.s == ')':
        return bool_expr.WordTest(w1)

    p_die('Expected binary operator, got %r (3 args)' % w1.s, loc.Word(w1))


class Test(vm._Builtin):

    def __init__(self, need_right_bracket, exec_opts, mem, errfmt):
        # type: (bool, optview.Exec, state.Mem, ui.ErrorFormatter) -> None
        self.need_right_bracket = need_right_bracket
        self.exec_opts = exec_opts
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        """The test/[ builtin.

        The only difference between test and [ is that [ needs a
        matching ].
        """
        typed_args.DoesNotAccept(cmd_val.proc_args)  # Disallow test (42)

        if self.need_right_bracket:  # Preprocess right bracket
            if self.exec_opts.simple_test_builtin():
                e_usage("should be invoked as 'test' (simple_test_builtin)",
                        loc.Missing)

            strs = cmd_val.argv
            if len(strs) == 0 or strs[-1] != ']':
                self.errfmt.Print_('missing closing ]',
                                   blame_loc=cmd_val.arg_locs[0])
                return 2
            # Remove the right bracket
            cmd_val.argv.pop()
            cmd_val.arg_locs.pop()

        w_parser = _StringWordEmitter(cmd_val)
        w_parser.Read()  # dummy: advance past argv[0]
        b_parser = bool_parse.BoolParser(w_parser)

        # There is a fundamental ambiguity due to poor language design, in cases like:
        # [ -z ]
        # [ -z -a ]
        # [ -z -a ] ]
        #
        # See posixtest() in bash's test.c:
        # "This is an implementation of a Posix.2 proposal by David Korn."
        # It dispatches on expressions of length 0, 1, 2, 3, 4, and N args.  We do
        # the same here.
        #
        # Another ambiguity:
        # -a is both a unary prefix operator and an infix operator.  How to fix this
        # ambiguity?

        bool_node = None  # type: bool_expr_t
        n = len(cmd_val.argv) - 1

        if self.exec_opts.simple_test_builtin() and n > 3:
            e_usage(
                "should only have 3 arguments or fewer (simple_test_builtin)",
                loc.Missing)

        try:
            if n == 0:
                return 1  # [ ] is False
            elif n == 1:
                w = w_parser.Read()
                bool_node = bool_expr.WordTest(w)
            elif n == 2:
                bool_node = _TwoArgs(w_parser)
            elif n == 3:
                bool_node = _ThreeArgs(w_parser)
            if n == 4:
                a0 = w_parser.Peek(0)
                if a0 == '!':
                    w_parser.Read()  # skip !
                    child = _ThreeArgs(w_parser)
                    bool_node = bool_expr.LogicalNot(child)
                elif a0 == '(' and w_parser.Peek(3) == ')':
                    w_parser.Read()  # skip ')'
                    bool_node = _TwoArgs(w_parser)
                else:
                    pass  # fallthrough

            if bool_node is None:
                bool_node = b_parser.ParseForBuiltin()

        except error.Parse as e:
            self.errfmt.PrettyPrintError(e, prefix='(test) ')
            return 2

        word_ev = _WordEvaluator()

        # We technically don't need mem because we don't support BASH_REMATCH here.
        # We want [ a -eq a ] to always be an error, unlike [[ a -eq a ]].  This is
        # a weird case of [[ being less strict.
        bool_ev = sh_expr_eval.BoolEvaluator(self.mem,
                                             self.exec_opts,
                                             None,
                                             None,
                                             self.errfmt,
                                             bracket=True)
        bool_ev.word_ev = word_ev
        bool_ev.CheckCircularDeps()
        try:
            b = bool_ev.EvalB(bool_node)
        except error._ErrorWithLocation as e:
            # We want to catch e_die() and e_strict().  Those are both FatalRuntime
            # errors now, but it might not make sense later.

            # NOTE: This doesn't seem to happen.  We have location info for all
            # errors that arise out of [.
            #if not e.HasLocation():
            #  raise

            self.errfmt.PrettyPrintError(e, prefix='(test) ')
            return 2  # 1 means 'false', and this usage error is like a parse error.

        status = 0 if b else 1
        return status
