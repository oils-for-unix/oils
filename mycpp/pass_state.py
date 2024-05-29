"""
pass_state.py
"""
from __future__ import print_function

from collections import defaultdict

from mycpp.util import log, SymbolPath

from typing import Optional

_ = log


class Virtual(object):
    """
  See unit test for example usage.
  """

    def __init__(self) -> None:
        self.methods: dict[SymbolPath, list[str]] = defaultdict(list)
        self.subclasses: dict[SymbolPath, list[tuple[str]]] = defaultdict(list)
        self.virtuals: dict[tuple[SymbolPath, str], Optional[tuple[SymbolPath, str]]] = {}
        self.has_vtable: dict[SymbolPath, bool] = {}
        self.can_reorder_fields: dict[SymbolPath, bool] = {}

        # _Executor -> vm::_Executor
        self.base_class_unique: dict[str, SymbolPath] = {}

    # These are called on the Forward Declare pass
    def OnMethod(self, class_name: SymbolPath, method_name: str) -> None:
        #log('OnMethod %s %s', class_name, method_name)

        # __init__ and so forth don't count
        if method_name.startswith('__') and method_name.endswith('__'):
            return

        self.methods[class_name].append(method_name)

    def OnSubclass(self, base_class: SymbolPath, subclass: SymbolPath) -> None:
        if len(base_class) > 1:
            # Hack for
            #
            # class _Executor: pass
            #   versus
            # class MyExecutor(vm._Executor): pass
            base_key = base_class[-1]

            # Fail if we have two base classes in different namespaces with the same
            # name.
            if base_key in self.base_class_unique:
                # Make sure we don't have collisions
                assert self.base_class_unique[base_key] == base_class or base_class in self.subclasses[self.base_class_unique[base_key]], base_class
            else:
                self.base_class_unique[base_key] = base_class

        else:
            base_key = base_class

        self.subclasses[base_class].append(subclass)

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
                    self.virtuals[(base_class, method)] = None
                    self.virtuals[(subclass, method)] = (base_class, method)
                if overlapping:
                    self.has_vtable[base_class] = True
                    self.has_vtable[subclass] = True

    # These is called on the Decl pass
    def IsVirtual(self, class_name: SymbolPath, method_name: str) -> bool:
        return (class_name, method_name) in self.virtuals

    def HasVTable(self, class_name: SymbolPath) -> bool:
        return class_name in self.has_vtable

    def CanReorderFields(self, class_name: SymbolPath) -> bool:
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
        self.block_stack: list[int] = []
        self.predecessors: set[int] = set({})
        self.deadends: set[int] = set({})

        # order doesn't actually matter here, but sets require elements to be
        # hashable
        self.facts: dict[int, list[Fact]] = defaultdict(list)

    def AddEdge(self, pred: int, succ: int) -> None:
        """
        Add a directed edge from pred to succ.
        """
        if pred in self.deadends:
            for w in [u for (u, v) in self.edges if v == pred]:
                self.AddEdge(w, succ)
        else:
            self.edges.add((pred, succ))

    def AddDeadend(self, statement: int):
        """
        Mark a statement as a dead-end (e.g. return or continue).
        """
        self.deadends.add(statement)

    def CurrentStatement(self) -> int:
        """
        Get the ID of the current statement.
        """
        return self.statement_counter

    def AddStatement(self) -> int:
        """
        Add a new statement and return its ID. If pred is set, it will be used
        as the new statement's predecessor instead of the last statement
        created.
        """
        if len(self.predecessors) and len(self.block_stack) == 0:
            self.statement_counter += 1
            self._PopPredecessors(self.statement_counter)

        else:
            pred = self.statement_counter
            if len(self.block_stack):
                pred = self.block_stack[-1]

            self.statement_counter += 1
            self.AddEdge(pred, self.statement_counter)

        if len(self.block_stack):
            self.block_stack[-1] = self.statement_counter

        return self.statement_counter
    
    def AddFact(self, statement: int, fact: Fact) -> None:
        """
        Annotate a statement with a fact.
        """
        self.facts[statement].append(fact)

    def _PopPredecessors(self, succ: Optional[int] = None) -> None:
        preds = self.predecessors
        if preds is not None and succ is not None:
            for s in preds:
                self.AddEdge(s, succ)

        self.predecessors = set({})

    def _PushBlock(self, begin: Optional[int] = None) -> None:
        """
        Start a block at the given statement ID.
        """
        if begin is None:
            begin = self.AddStatement()
            self._PopPredecessors(begin)

        self.block_stack.append(begin)
        return begin

    def _PopBlock(self, was_if_arm: bool = False) -> int:
        """
        Pop a block from the top of the stack and return the ID of the block's
        last statement.
        """
        assert len(self.block_stack)
        last = self.block_stack.pop()
        if len(self.block_stack) and last not in self.deadends:
            self.block_stack[-1] = last

        if was_if_arm and last not in self.deadends:
            self.predecessors.add(last)

        return last


class CfgBlockContext(object):
    """
    Context manager to make dealing with things like try-except blocks easier.
    """
    def __init__(self, cfg: ControlFlowGraph, pred: Optional[int] = None) -> None:
        self.cfg = cfg
        if cfg is None:
            return

        self.entry = self.cfg._PushBlock(pred)
        self.exit = self.entry

    def __enter__(self) -> None:
        return self if self.cfg else None

    def __exit__(self, *args) -> None:
        if not self.cfg:
            return

        self.exit = self.cfg._PopBlock()


class CfgBranchContext(object):
    """
    Context manager to make dealing with if-else blocks easier.
    """
    def __init__(self, cfg: ControlFlowGraph, pred: int) -> None:
        self.cfg = cfg
        self.entry = pred
        self.exit = self.entry
        if cfg is None:
            return

        self.cfg._PushBlock(pred)

    def __enter__(self) -> None:
        return self if self.cfg else None

    def __exit__(self, *args) -> None:
        if not self.cfg:
            return

        self.exit = self.cfg._PopBlock(was_if_arm=True)


class CfgLoopContext(object):
    """
    Context manager to make dealing with loops easier.
    """
    def __init__(self, cfg: ControlFlowGraph) -> None:
        self.cfg = cfg
        if cfg is None:
            return

        self.entry = self.cfg._PushBlock()
        self.exit = self.entry

    def __enter__(self) -> None:
        return self if self.cfg else None

    def __exit__(self, *args) -> None:
        if not self.cfg:
            return

        self.exit = self.cfg._PopBlock()
        self.cfg.AddEdge(self.exit, self.entry)
