from __future__ import print_function

from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.runtime_asdl import (scope_e, HayNode)
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.value_asdl import (value, value_e, value_t, LiteralBlock,
                                      cmd_frag, cmd_frag_e)

from asdl import format as fmt
from core import alloc
from core.error import e_usage, e_die
from core import num
from core import state
from display import ui
from core import vm
from frontend import args
from frontend import consts
from frontend import location
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import tagswitch, iteritems, NewDict, log

from typing import List, Dict, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from osh.cmd_eval import CommandEvaluator

_ = log

_HAY_ACTION_ERROR = "builtin expects 'define', 'reset' or 'pp'"


class ctx_HayNode(object):
    """Haynode builtin makes new names in the tree visible."""

    def __init__(self, hay_state, hay_name):
        # type: (HayState, Optional[str]) -> None
        #log('pairs %s', pairs)
        self.hay_state = hay_state
        self.hay_state.Push(hay_name)

    def __enter__(self):
        # type: () -> None
        return

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.hay_state.Pop()


class ctx_HayEval(object):
    """
    - Turn on shopt ysh:all and _running_hay
    - Disallow recursive 'hay eval'
    - Ensure result is isolated for 'hay eval :result'

    More leakage:

    External:
    - execute programs (ext_prog)
    - redirect
    - pipelines, subshell, & etc?
      - do you have to put _running_hay() checks everywhere?

    Internal:

    - state.Mem()
      - should we at least PushTemp()?
      - But then they can do setglobal
    - Option state

    - Disallow all builtins except echo/write/printf?
      - maybe could do that at the top level
      - source builtin, read builtin
      - cd / pushd / popd
      - trap -- hm yeah this one is bad

    - procs?  Not strictly necessary
      - you should be able to define them, but not call the user ...

    """

    def __init__(self, hay_state, mutable_opts, mem):
        # type: (HayState, state.MutableOpts, state.Mem) -> None
        self.hay_state = hay_state
        self.mutable_opts = mutable_opts
        self.mem = mem

        if mutable_opts.Get(option_i._running_hay):
            # This blames the right 'hay' location
            e_die("Recursive 'hay eval' not allowed")

        for opt_num in consts.YSH_ALL:
            mutable_opts.Push(opt_num, True)
        mutable_opts.Push(option_i._running_hay, True)

        self.hay_state.PushEval()
        self.mem.PushTemp()

    def __enter__(self):
        # type: () -> None
        return

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None

        self.mem.PopTemp()
        self.hay_state.PopEval()

        self.mutable_opts.Pop(option_i._running_hay)
        for opt_num in consts.YSH_ALL:
            self.mutable_opts.Pop(opt_num)


class HayState(object):
    """State for DSLs."""

    def __init__(self):
        # type: () -> None
        ch = NewDict()  # type: Dict[str, HayNode]
        self.root_defs = HayNode(ch)
        self.cur_defs = self.root_defs  # Same as ClearDefs()
        self.def_stack = [self.root_defs]

        node = self._MakeOutputNode()
        self.result_stack = [node]  # type: List[Dict[str, value_t]]
        self.output = None  # type: Dict[str, value_t]

    def _MakeOutputNode(self):
        # type: () -> Dict[str, value_t]
        d = NewDict()  # type: Dict[str, value_t]
        d['source'] = value.Null
        d['children'] = value.List([])
        return d

    def PushEval(self):
        # type: () -> None

        # remove previous results
        node = self._MakeOutputNode()
        self.result_stack = [node]

        self.output = None  # remove last result

    def PopEval(self):
        # type: () -> None

        # Save the result
        self.output = self.result_stack[0]

        # Clear results
        node = self._MakeOutputNode()
        self.result_stack = [node]

    def AppendResult(self, d):
        # type: (Dict[str, value_t]) -> None
        """Called by haynode builtin."""
        UP_children = self.result_stack[-1]['children']
        assert UP_children.tag() == value_e.List, UP_children
        children = cast(value.List, UP_children)
        children.items.append(value.Dict(d))

    def Result(self):
        # type: () -> Dict[str, value_t]
        """Called by hay eval and eval_hay()"""
        return self.output

    def HayRegister(self):
        # type: () -> Dict[str, value_t]
        """Called by _hay() function."""
        return self.result_stack[0]

    def Resolve(self, first_word):
        # type: (str) -> bool
        return first_word in self.cur_defs.children

    def DefinePath(self, path):
        # type: (List[str]) -> None
        """Fill a tree from the given path."""
        current = self.root_defs
        for name in path:
            if name not in current.children:
                ch = NewDict()  # type: Dict[str, HayNode]
                current.children[name] = HayNode(ch)
            current = current.children[name]

    def Reset(self):
        # type: () -> None

        # reset definitions
        ch = NewDict()  # type: Dict[str, HayNode]
        self.root_defs = HayNode(ch)
        self.cur_defs = self.root_defs

        # reset output
        self.PopEval()

    def Push(self, hay_name):
        # type: (Optional[str]) -> None
        """
        Package cppunit {
        }   # pushes a namespace

        haynode package cppunit {
        }   # just assumes every TYPE 'package' is valid.
        """
        top = self.result_stack[-1]
        # TODO: Store this more efficiently?  See osh/builtin_pure.py
        children = cast(value.List, top['children'])
        last_child = cast(value.Dict, children.items[-1])
        self.result_stack.append(last_child.d)

        #log('> PUSH')
        if hay_name is None:
            self.def_stack.append(self.cur_defs)  # no-op
        else:
            # Caller should ensure this
            assert hay_name in self.cur_defs.children, hay_name

            self.cur_defs = self.cur_defs.children[hay_name]
            self.def_stack.append(self.cur_defs)

    def Pop(self):
        # type: () -> None
        self.def_stack.pop()
        self.cur_defs = self.def_stack[-1]

        self.result_stack.pop()


class Hay(vm._Builtin):
    """hay builtin

    hay define -- package user
    hay define -- user/foo user/bar  # second level
    hay pp
    hay reset
    """

    def __init__(self, hay_state, mutable_opts, mem, cmd_ev):
        # type: (HayState, state.MutableOpts, state.Mem, CommandEvaluator) -> None
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

            cmd = typed_args.RequiredBlockAsFrag(cmd_val)

            with ctx_HayEval(self.hay_state, self.mutable_opts, self.mem):
                # Note: we want all haynode invocations in the block to appear as
                # our 'children', recursively
                unused = self.cmd_ev.EvalCommandFrag(cmd)

            result = self.hay_state.Result()

            val = value.Dict(result)
            self.mem.SetNamed(location.LName(var_name), val, scope_e.LocalOnly)

        elif action == 'reset':
            self.hay_state.Reset()

        elif action == 'pp':
            h = self.hay_state.root_defs.PrettyTree(False)
            f = mylib.Stdout()
            fmt.HNodePrettyPrint(h, f)
            f.write('\n')

        else:
            e_usage(_HAY_ACTION_ERROR, action_loc)

        return 0


def OptionalLiteralBlock(cmd_val):
    # type: (cmd_value.Argv) -> Optional[LiteralBlock]
    """Helper for Hay """

    if cmd_val.proc_args:
        r = typed_args.ReaderForProc(cmd_val)
        cmd = r.OptionalCommand()
        r.Done()

        if cmd:
            frag = cmd.frag
            with tagswitch(frag) as case:
                if case(cmd_frag_e.LiteralBlock):
                    lit = cast(LiteralBlock, frag)
                    return lit
                elif case(cmd_frag_e.Expr):
                    c = cast(cmd_frag.Expr, frag).c
                    # This can happen with Node (; ; ^(echo hi))
                    # The problem is that it doesn't have "backing lines",
                    # which the Hay API uses.
                    e_die("Hay expected block literal, like { echo x }",
                          loc.Command(c))
                else:
                    raise AssertionError()

    return None


class HayNode_(vm._Builtin):
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
        # type: (HayState, state.Mem, CommandEvaluator) -> None
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

        lit_block = OptionalLiteralBlock(cmd_val)

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

            # We can only extract code if the block arg is literal like package
            # foo { ... }, not if it's like package foo (myblock)

            brace_group = lit_block.brace_group
            # BraceGroup has location for {
            line = brace_group.left.line

            # for the user to pass back to --location-str
            result['location_str'] = value.Str(ui.GetLineSourceString(line))
            result['location_start_line'] = num.ToBig(line.line_num)

            # Between { and }
            code_str = alloc.SnipCodeBlock(brace_group.left, brace_group.right,
                                           lit_block.lines)

            result['code_str'] = value.Str(code_str)

            # Append after validation
            self.hay_state.AppendResult(result)

        else:
            # Must be done before EvalCommand
            self.hay_state.AppendResult(result)

            if lit_block:  # 'package foo' is OK
                result['children'] = value.List([])

                # Evaluate in its own stack frame so that we can capture the
                # dictionary.

                # TODO:
                # - there is a dynamic scope hack here?
                # - this should be like evalToDict()?  with ctx_EnclosedFrame
                # - then the LiteralBlock needs to capture?
                #   - the backing lines are an issue - it is self.block_arg

                with state.ctx_Temp(self.mem):
                    with ctx_HayNode(self.hay_state, hay_name):
                        # Note: we want all haynode invocations in the block to appear as
                        # our 'children', recursively
                        self.cmd_ev.EvalCommandFrag(lit_block.brace_group)

                    # Treat the vars as a Dict
                    block_attrs = self.mem.CurrentFrame()

                attrs = NewDict()  # type: Dict[str, value_t]
                for name, cell in iteritems(block_attrs):

                    # User can hide variables with _ suffix
                    # e.g. for i_ in foo bar { echo $i_ }
                    if name.endswith('_'):
                        continue

                    attrs[name] = cell.val

                result['attrs'] = value.Dict(attrs)

        return 0
