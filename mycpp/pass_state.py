"""
pass_state.py
"""
from __future__ import print_function

from collections import defaultdict

from mycpp.util import log

from typing import Optional

_ = log


class Virtual(object):
    """
  See unit test for example usage.
  """

    def __init__(self) -> None:
        self.methods: dict[str, list[str]] = defaultdict(list)
        self.subclasses: dict[str, list[str]] = defaultdict(list)
        self.virtuals: list[tuple[str, str]] = []
        self.has_vtable: dict[str, bool] = {}
        self.can_reorder_fields: dict[str, bool] = {}

        # _Executor -> vm::_Executor
        self.base_class_unique: dict[str, str] = {}

    # These are called on the Forward Declare pass
    def OnMethod(self, class_name: str, method_name: str) -> None:
        #log('OnMethod %s %s', class_name, method_name)

        # __init__ and so forth don't count
        if method_name.startswith('__') and method_name.endswith('__'):
            return

        self.methods[class_name].append(method_name)

    def OnSubclass(self, base_class: str, subclass: str) -> None:
        if '::' in base_class:
            # Hack for
            #
            # class _Executor: pass
            #   versus
            # class MyExecutor(vm._Executor): pass
            base_key = base_class.split('::')[1]

            # Fail if we have two base classes in different namespaces with the same
            # name.
            if base_key in self.base_class_unique:
                # Make sure we don't have collisions
                assert self.base_class_unique[base_key] == base_class
            else:
                self.base_class_unique[base_key] = base_class

        else:
            base_key = base_class

        self.subclasses[base_key].append(subclass)

    def Calculate(self) -> None:
        """
    Call this after the forward declare pass.

    TODO: Are there bugs based on conflicting class names?
    """
        for base_class, subclasses in self.subclasses.items():
            self.can_reorder_fields[base_class] = False

            for subclass in subclasses:
                self.can_reorder_fields[subclass] = False

                b_methods = self.methods[base_class]
                s_methods = self.methods[subclass]
                overlapping = set(b_methods) & set(s_methods)
                for method in overlapping:
                    self.virtuals.append((base_class, method))
                    self.virtuals.append((subclass, method))
                if overlapping:
                    self.has_vtable[base_class] = True
                    self.has_vtable[subclass] = True

    # These is called on the Decl pass
    def IsVirtual(self, class_name: str, method_name: str) -> bool:
        return (class_name, method_name) in self.virtuals

    def HasVTable(self, class_name: str) -> bool:
        return class_name in self.has_vtable

    def CanReorderFields(self, class_name: str) -> bool:
        if class_name in self.can_reorder_fields:
            return self.can_reorder_fields[class_name]
        else:
            return True  # by default they can be reordered


class Fact(object):
    """
    An abstract fact. These can be used to build up datalog programs.
    """
    def __init__(self) -> None:
        pass

    def name(self) -> str:
        raise NotImplementedError()

    def Generate(self, func: str, statement: int) -> str:
        raise NotImplementedError()


class ControlFlowGraph(object):
    """
    A simple control-flow graph. See unit tests for usage.

    Statements are assigned unique numeric IDs. Control flow is represented as
    directed edges between statements.

    Statements can carry annotations called facts.
    """

    def __init__(self) -> None:
        self.statement_counter: int = 0
        self.edges: set[tuple[int, int]] = set({})
        self.loop_stack: list[int] = []
        self.branch_exits: list[int] = None

        # order doesn't actually matter here, but sets require elements to be
        # hashable
        self.facts: dict[int, list[Fact]] = defaultdict(list)

    def AddEdge(self, pred: int, succ: int) -> None:
        """
        Add a directed edge from pred to succ.
        """
        self.edges.add((pred, succ))

    def AddStatement(self, pred: Optional[int] = None) -> int:
        """
        Add a new statement and return its ID. If pred is set, it will be used
        as the new statement's predecessor instead of the last statement
        created.
        """
        if self.branch_exits is not None:
            assert pred is None
            self.statement_counter += 1
            for s in self.branch_exits:
                self.AddEdge(s, self.statement_counter)

            self.branch_exits = None

        else:
            pred = pred or self.statement_counter
            self.statement_counter += 1
            self.AddEdge(pred, self.statement_counter)

        return self.statement_counter
    
    def AddFact(self, statement: int, fact: Fact) -> None:
        """
        Annotate a statement with a fact.
        """
        self.facts[statement].append(fact)

    def SetBranchExits(self, exits: list[int]) -> None:
        """
        Set a list of if statement arm exit points.
        """
        assert self.branch_exits is None
        self.branch_exits = list(exits)

    def CurrentLoop(self) -> Optional[int]:
        """
        Return the statement ID that corresponds to the entry point of the loop
        on the top of the loop stack. This can be used for things like continue
        statements.
        """
        if len(self.loop_stack):
            return self.loop_stack[-1]

        return None

    def PushLoop(self) -> None:
        """
        Push the current statement onto the loop stack. It will be treated as
        the entry point for the loop.
        """
        self.loop_stack.append(self.statement_counter)

    def PopLoop(self) -> None:
        """
        Pop the current loop from the stack and add back-edges from the final
        statement(s) of the loop to the entry point.
        """
        loop_entrance = self.loop_stack.pop()
        if self.branch_exits is not None:
            exits = self.branch_exits
            if len(self.loop_stack) == 0:
                self.branch_exits = None

            for s in exits:
                self.AddEdge(s, loop_entrance)

        self.AddEdge(self.statement_counter, loop_entrance)


class CfgLoopContext(object):
    """
    Context manager to make dealing with loops easier.  
    """
    def __init__(self, cfg: ControlFlowGraph) -> None:
        self.cfg = cfg
        self.entry = self.cfg.AddStatement()
        self.cfg.PushLoop()

    def __enter__(self) -> None:
        return self

    def __exit__(self, *args) -> None:
        self.cfg.PopLoop()
