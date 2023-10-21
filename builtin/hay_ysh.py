from __future__ import print_function

from _devbuild.gen.runtime_asdl import scope_e, value, value_t
from _devbuild.gen.syntax_asdl import loc

from asdl import format as fmt
from core import alloc
from core.error import e_usage
from core import state
from core import ui
from core import vm
from frontend import args
from frontend import location
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import iteritems, NewDict, log

from typing import List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from osh.cmd_eval import CommandEvaluator

_ = log

_HAY_ACTION_ERROR = "builtin expects 'define', 'reset' or 'pp'"


class Hay(vm._Builtin):
    """hay builtin

    hay define -- package user
    hay define -- user/foo user/bar  # second level
    hay pp
    hay reset
    """

    def __init__(self, hay_state, mutable_opts, mem, cmd_ev):
        # type: (state.Hay, state.MutableOpts, state.Mem, CommandEvaluator) -> None
        self.hay_state = hay_state
        self.mutable_opts = mutable_opts
        self.mem = mem
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()  # skip 'hay'

        action, action_loc = arg_r.Peek2()
        if action is None:
            e_usage(_HAY_ACTION_ERROR, action_loc)
        arg_r.Next()

        if action == 'define':
            # TODO: accept --
            #arg, arg_r = flag_spec.ParseCmdVal('hay-define', cmd_val)

            # arg = args.Parse(JSON_WRITE_SPEC, arg_r)
            first, _ = arg_r.Peek2()
            if first is None:
                e_usage('define expected a name', action_loc)

            names, name_locs = arg_r.Rest2()
            for i, name in enumerate(names):
                path = name.split('/')
                for p in path:
                    if len(p) == 0:
                        e_usage(
                            "got invalid path %r.  Parts can't be empty." %
                            name, name_locs[i])
                self.hay_state.DefinePath(path)

        elif action == 'eval':
            # hay eval :myvar { ... }
            #
            # - turn on ysh:all
            # - set _running_hay -- so that hay "first words" are visible
            # - then set the variable name to the result

            var_name, _ = arg_r.ReadRequired2("expected variable name")
            if var_name.startswith(':'):
                var_name = var_name[1:]
                # TODO: This could be fatal?

            cmd = typed_args.OptionalCommand(cmd_val)
            if not cmd:  # 'package foo' is OK
                e_usage('eval expected a block', loc.Missing)

            with state.ctx_HayEval(self.hay_state, self.mutable_opts,
                                   self.mem):
                # Note: we want all haynode invocations in the block to appear as
                # our 'children', recursively
                unused = self.cmd_ev.EvalCommand(cmd)

            result = self.hay_state.Result()

            val = value.Dict(result)
            self.mem.SetValue(location.LName(var_name), val, scope_e.LocalOnly)

        elif action == 'reset':
            self.hay_state.Reset()

        elif action == 'pp':
            tree = self.hay_state.root_defs.PrettyTree()
            ast_f = fmt.DetectConsoleOutput(mylib.Stdout())
            fmt.PrintTree(tree, ast_f)
            ast_f.write('\n')

        else:
            e_usage(_HAY_ACTION_ERROR, action_loc)

        return 0


class HayNode(vm._Builtin):
    """The FIXED builtin that is run after 'hay define'.

    It evaluates a SUBTREE

    Example:

      package cppunit {
        version = '1.0'
        user bob
      }

    is short for

      haynode package cppunit {
        version = '1.0'
        haynode user bob
      }
    """

    def __init__(self, hay_state, mem, cmd_ev):
        # type: (state.Hay, state.Mem, CommandEvaluator) -> None
        self.hay_state = hay_state
        self.mem = mem  # isolation with mem.PushTemp
        self.cmd_ev = cmd_ev  # To run blocks
        self.arena = cmd_ev.arena  # To extract code strings

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)

        hay_name, arg0_loc = arg_r.Peek2()
        if hay_name == 'haynode':  # haynode package glib { ... }
            arg_r.Next()
            hay_name = None  # don't validate

        # Should we call hay_state.AddChild() so it can be mutated?
        result = NewDict()  # type: Dict[str, value_t]

        node_type, _ = arg_r.Peek2()
        result['type'] = value.Str(node_type)

        arg_r.Next()
        arguments = arg_r.Rest()

        lit_block = typed_args.OptionalLiteralBlock(cmd_val)

        # package { ... } is not valid
        if len(arguments) == 0 and lit_block is None:
            e_usage('expected at least 1 arg, or a literal block { }',
                    arg0_loc)

        items = [value.Str(s) for s in arguments]  # type: List[value_t]
        result['args'] = value.List(items)

        if node_type.isupper():  # TASK build { ... }
            if lit_block is None:
                e_usage('command node requires a literal block argument',
                        loc.Missing)

            if 0:  # self.hay_state.to_expr ?
                result['expr'] = lit_block  # UNEVALUATED block
            else:
                # We can only extract code if the block arg is literal like package
                # foo { ... }, not if it's like package foo (myblock)

                brace_group = lit_block.brace_group
                # BraceGroup has location for {
                line = brace_group.left.line

                # for the user to pass back to --location-str
                result['location_str'] = value.Str(
                    ui.GetLineSourceString(line))
                result['location_start_line'] = value.Int(line.line_num)

                # Between { and }
                code_str = alloc.SnipCodeBlock(brace_group.left,
                                               brace_group.right,
                                               lit_block.lines)

                result['code_str'] = value.Str(code_str)

            # Append after validation
            self.hay_state.AppendResult(result)

        else:
            # Must be done before EvalCommand
            self.hay_state.AppendResult(result)

            if lit_block:  # 'package foo' is OK
                result['children'] = value.List([])

                # Evaluate in its own stack frame.  TODO: Turn on dynamic scope?
                with state.ctx_Temp(self.mem):
                    with state.ctx_HayNode(self.hay_state, hay_name):
                        # Note: we want all haynode invocations in the block to appear as
                        # our 'children', recursively
                        self.cmd_ev.EvalCommand(lit_block.brace_group)

                    # Treat the vars as a Dict
                    block_attrs = self.mem.TopNamespace()

                attrs = NewDict()  # type: Dict[str, value_t]
                for name, cell in iteritems(block_attrs):

                    # User can hide variables with _ suffix
                    # e.g. for i_ in foo bar { echo $i_ }
                    if name.endswith('_'):
                        continue

                    attrs[name] = cell.val

                result['attrs'] = value.Dict(attrs)

        return 0
