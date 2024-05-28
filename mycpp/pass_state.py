"""
pass_state.py
"""
from __future__ import print_function

import os
from collections import defaultdict

from mycpp.util import join_name, log, SymbolPath

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


class FunctionCall(Fact):
    def __init__(self, callee: str) -> None:
        self.callee = callee

    def name(self) -> str:
        return 'call'

    def Generate(self, func: str, statement: int) -> str:
        return '{}\t{}\t{}\n'.format(func, statement, self.callee)


class ControlFlowGraph(object):
    """
    A simple control-flow graph.

    Every statement in the program is represented as a node in a graph with
    unique a numeric ID. Control flow is represented as directed edges through
    the graph. Loops can introduce back-edges. Every node in the graph will
    satisfy at least one of the following conditions:

        - Its indegree is at least one.

        - Its outdegree is at least one.

    For simple linear graphs all you need is the AddStatement method. For more
    complex flows there is a set of context managers below to help simplify
    construction.

        - For branches-like statements (e.g. if- and try- statements) use
          CfgBranchContext. It will take care of the details associated with
          stitching the different branches to statements in the next statement.

        - For loops, use CfgLoopContext. It will take care of adding back-edges
          and connecting break statements to any statements that proceed the
          loop.

        - CfgBlockContext can be used for simple cases where you just want to
          track the beginning and end of a sequence of statements.

    Statements can carry annotations called facts, which are used as inputs to
    datalog programs to perform dataflow diffrent kinds of dataflow analyses.
    To annotate a statement, use the AddFact method with any object that
    implements the Fact interface.

    See the unit tests in pass_state_test.py and the mycpp phase in
    control_flow_pass.py for detailed examples of usage.
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
        Add a directed edge from pred to succ. If pred is a deadend, its
        non-deadends will be used instead.
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

    def AddStatement(self) -> int:
        """
        Add a new statement and return its ID.
        """
        if len(self.predecessors) == 0:
            if len(self.block_stack):
                self.predecessors.add(self.block_stack[-1])
            else:
                self.predecessors.add(self.statement_counter)

        self.statement_counter += 1
        for pred in self.predecessors:
            self.AddEdge(pred, self.statement_counter)

        self.predecessors = set({})

        if len(self.block_stack):
            self.block_stack[-1] = self.statement_counter

        return self.statement_counter
    
    def AddFact(self, statement: int, fact: Fact) -> None:
        """
        Annotate a statement with a fact.
        """
        self.facts[statement].append(fact)

    def _PushBlock(self, begin: Optional[int] = None) -> int:
        """
        Start a block at the given statement ID. If a beginning statement isn't
        provided one will be created and its ID will be returend.

        Direct use of this function is discouraged. Consider using one of the
        block context managers below instead.
        """
        if begin is None:
            begin = self.AddStatement()
        else:
            self.predecessors.add(begin)

        self.block_stack.append(begin)
        return begin

    def _PopBlock(self) -> int:
        """
        Pop a block from the top of the stack and return the ID of the block's
        last statement.

        Direct use of this function is discouraged. Consider using one of the
        block context managers below instead.
        """
        assert len(self.block_stack)
        last = self.block_stack.pop()
        if len(self.block_stack) and last not in self.deadends:
            self.block_stack[-1] = last

        return last


class CfgBlockContext(object):
    """
    Context manager to make dealing with things like with-statements easier.
    """
    def __init__(self, cfg: ControlFlowGraph, begin: Optional[int] = None) -> None:
        self.cfg = cfg
        if cfg is None:
            return

        self.entry = self.cfg._PushBlock(begin)
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
    def __init__(self, cfg: ControlFlowGraph, branch_point: int) -> None:
        self.cfg = cfg
        self.entry = branch_point
        self.exit = self.entry
        if cfg is None:
            return

        self.arms = []
        self.pushed = False

    def AddBranch(self, entry: Optional[int] = None):
        if not self.cfg:
            return CfgBranchContext(None, None)

        self.arms.append(CfgBranchContext(self.cfg, entry or self.entry))
        self.cfg._PushBlock(self.arms[-1].entry)
        self.arms[-1].pushed = True
        return self.arms[-1]

    def __enter__(self) -> None:
        return self

    def __exit__(self, *args) -> None:
        if not self.cfg:
            return

        if self.pushed:
            self.exit = self.cfg._PopBlock()

        for arm in self.arms:
            if arm.exit not in self.cfg.deadends:
                self.cfg.predecessors.add(arm.exit)



class CfgLoopContext(object):
    """
    Context manager to make dealing with loops easier.
    """
    def __init__(self, cfg: ControlFlowGraph, entry: Optional[int] = None) -> None:
        self.cfg = cfg
        self.breaks = set({})
        if cfg is None:
            return

        self.entry = self.cfg._PushBlock(entry)
        self.exit = self.entry

    def AddBreak(self, statement: int) -> None:
        assert self.cfg
        self.breaks.add(statement)
        self.cfg.AddDeadend(statement)

    def AddContinue(self, statement: int) -> None:
        self.cfg.AddEdge(statement, self.entry)
        self.cfg.AddDeadend(statement)

    def __enter__(self) -> None:
        return self if self.cfg else None

    def __exit__(self, *args) -> None:
        if not self.cfg:
            return

        self.exit = self.cfg._PopBlock()
        self.cfg.AddEdge(self.exit, self.entry)
        for pred in self.cfg.predecessors:
            self.cfg.AddEdge(pred, self.entry)

        # If we had any breaks, arm the predecessor set with the current
        # statement and the break statements.
        if len(self.breaks):
            if len(self.cfg.block_stack):
                self.cfg.predecessors.add(self.cfg.block_stack[-1])
            else:
                self.cfg.predecessors.add(self.cfg.statement_counter)

        for b in self.breaks:
            self.cfg.deadends.remove(b)
            self.cfg.predecessors.add(b)


def DumpControlFlowGraphs(cfgs: dict[str, ControlFlowGraph], facts_dir='_tmp/mycpp-facts') -> None:
    """
    Dump the given control flow graphs and associated facts into the given
    directory as text files that can be consumed by datalog.
    """
    edge_facts = '{}/cf_edge.facts'.format(facts_dir)
    fact_files = {}
    os.makedirs(facts_dir, exist_ok=True)
    with open(edge_facts, 'w') as cfg_f:
        for func, cfg in sorted(cfgs.items()):
            joined = join_name(func, delim='.')
            for (u, v) in sorted(cfg.edges):
                cfg_f.write('{}\t{}\t{}\n'.format(joined, u, v))

            for statement, facts in sorted(cfg.facts.items()):
                for fact in facts: # already sorted temporally
                    fact_f = fact_files.get(fact.name())
                    if not fact_f:
                        fact_f = open('{}/{}.facts'.format(facts_dir, fact.name()), 'w')
                        fact_files[fact.name()] = fact_f

                    fact_f.write(fact.Generate(joined, statement))

    for f in fact_files.values():
        f.close()
