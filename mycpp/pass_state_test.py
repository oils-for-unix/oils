#!/usr/bin/env python3
"""
pass_state_test.py: Tests for pass_state.py
"""
from __future__ import print_function

import unittest

import pass_state  # module under test


class VirtualTest(unittest.TestCase):

    def testVirtual(self):
        """
    Example:

    class Base(object):
      def method(self):  # we don't know if this is virtual yet
        pass
      def x(self):
        pass

    class Derived(Base):
      def method(self):  # now it's virtual!
        pass
      def y(self):
        pass
    """
        v = pass_state.Virtual()
        v.OnMethod('Base', 'method')
        v.OnMethod('Base', 'x')
        v.OnSubclass('Base', 'Derived')
        v.OnMethod('Derived', 'method')
        v.OnMethod('Derived', 'y')

        v.Calculate()

        print(v.virtuals)
        self.assertEqual([('Base', 'method'), ('Derived', 'method')],
                         v.virtuals)

        self.assertEqual(True, v.IsVirtual('Base', 'method'))
        self.assertEqual(True, v.IsVirtual('Derived', 'method'))
        self.assertEqual(False, v.IsVirtual('Derived', 'y'))

        self.assertEqual(False, v.IsVirtual('Klass', 'z'))

        self.assertEqual(True, v.HasVTable('Base'))
        self.assertEqual(True, v.HasVTable('Derived'))

        self.assertEqual(False, v.HasVTable('Klass'))

    def testNoInit(self):
        v = pass_state.Virtual()
        v.OnMethod('Base', '__init__')
        v.OnSubclass('Base', 'Derived')
        v.OnMethod('Derived', '__init__')
        v.Calculate()
        self.assertEqual(False, v.HasVTable('Base'))
        self.assertEqual(False, v.HasVTable('Derived'))

    def testCanReorderFields(self):
        """
    class Base(object):
      def __init__(self):
        self.s = ''  # pointer
        self.i = 42

    class Derived(Base):
      def __init__(self):
        Base.__init__()
        self.mylist = []  # type: List[str]

    Note: we can't reorder these, even though there are no virtual methods.
    """
        v = pass_state.Virtual()
        v.OnSubclass('Base2', 'Derived2')
        v.Calculate()

        self.assertEqual(False, v.CanReorderFields('Base2'))
        self.assertEqual(False, v.CanReorderFields('Derived2'))

        self.assertEqual(True, v.CanReorderFields('Klass2'))


class DummyFact(pass_state.Fact):
    def __init__(self, n: int) -> None:
        self.n = n

    def name(self): return 'dummy'

    def Generate(self, func: str, statement: int) -> str:
        return '{},{},{}'.format(func, statement, self.n)


class ControlFlowGraphTest(unittest.TestCase):

    def testLinear(self):
        cfg = pass_state.ControlFlowGraph()

        a = cfg.AddStatement()
        b = cfg.AddStatement()
        c = cfg.AddStatement()
        d = cfg.AddStatement()

        cfg.AddFact(b, DummyFact(1))
        cfg.AddFact(d, DummyFact(99))
        cfg.AddFact(d, DummyFact(7))

        expected_edges = {
            (0, a), (a, b), (b, c), (c, d),
        }
        self.assertEqual(expected_edges, cfg.edges)

        self.assertEqual(1, len(cfg.facts[b]))
        self.assertEqual('foo,1,1', cfg.facts[b][0].Generate('foo', 1))
        self.assertEqual('dummy', cfg.facts[b][0].name())
        self.assertEqual(2, len(cfg.facts[d]))
        self.assertEqual('bar,1,99', cfg.facts[d][0].Generate('bar', 1))
        self.assertEqual('bar,2,7', cfg.facts[d][1].Generate('bar', 2))

    def testBranches(self):
        cfg = pass_state.ControlFlowGraph()

        main0 = cfg.AddStatement()

        # branch condition facts all get attached to this statement
        branch_point = cfg.AddStatement()

        # first statement in if block
        with pass_state.CfgBranchContext(cfg, branch_point) as arm0:
            arm0_a = cfg.AddStatement() # block statement 2
            arm0_b = cfg.AddStatement() # block statement 2
            arm0_c = cfg.AddStatement() # block statement 3

        # frist statement in elif block
        with pass_state.CfgBranchContext(cfg, branch_point) as arm1:
            arm1_a = cfg.AddStatement()
            arm1_b = cfg.AddStatement() # block statement 2

        # frist statement in else block
        with pass_state.CfgBranchContext(cfg, branch_point) as arm2:
            arm2_a = cfg.AddStatement()
            arm2_b = cfg.AddStatement() # block statement 2

        self.assertEqual(arm0_c, arm0.exit)
        self.assertEqual(arm1_b, arm1.exit)
        self.assertEqual(arm2_b, arm2.exit)

        join = cfg.AddStatement()
        end = cfg.AddStatement()

        """
        We expecte a graph like this.

                    begin
                      |
                    main0
                      |
                      v
                 branch_point
                /     |      \
             arm0_a  arm1_a  arm2_a
               |      |       |
             arm0_b  arm1_b  arm2_b
               |      |       |
             arm0_c   |       |
               |      |       /
                \     |      /
                 \    |     /
                  \   |    /
                   \  |   /
                     join
                      |
                     end
        """
        expected_edges = {
            (0, main0),
            (main0, branch_point),
            (branch_point, arm0_a), (branch_point, arm1_a), (branch_point, arm2_a),
            (arm0_a, arm0_b), (arm0_b, arm0_c),
            (arm1_a, arm1_b),
            (arm2_a, arm2_b),
            (arm0_c, join), (arm1_b, join), (arm2_b, join),
            (join, end),
        }
        self.assertEqual(expected_edges, cfg.edges)

    def testDeadends(self):
        """
        Make sure we don't create orphans in the presence of continue, return,
        raise, etc...
        """

        cfg = pass_state.ControlFlowGraph()
        with pass_state.CfgBranchContext(cfg, cfg.AddStatement()) as branchA:
            ret = cfg.AddStatement() # return
            cfg.AddDeadend(ret)

        with pass_state.CfgLoopContext(cfg) as loop:
            branch_point = cfg.AddStatement()
            with pass_state.CfgBranchContext(cfg, branch_point) as branchB: # if
                cont = cfg.AddStatement() # continue
                cfg.AddEdge(cont, loop.entry)
                cfg.AddDeadend(cont)

            with pass_state.CfgBranchContext(cfg, branch_point) as branchC: # else
                innerC = cfg.AddStatement()

        end = cfg.AddStatement()
        expected_edges = {
            (0, branchA.entry),
            (branchA.entry, loop.entry),
            (loop.entry, branchB.entry),
            (branch_point, cont),
            (branch_point, innerC),
            (innerC, end),
        }

    def testNedstedIf(self):
        """
        The mypy AST represents else-if as nested if-statements inside the else arm.
        """
        cfg = pass_state.ControlFlowGraph()

        outer_branch_point = cfg.AddStatement()
        with pass_state.CfgBranchContext(cfg, outer_branch_point) as branch0: # if
            branch0_a = cfg.AddStatement()

        with pass_state.CfgBranchContext(cfg, outer_branch_point) as branch1: # else
            with pass_state.CfgBranchContext(cfg, cfg.AddStatement()) as branch2: # else if
                branch2_a = cfg.AddStatement()

            branch1_a = cfg.AddStatement()

        end = cfg.AddStatement()

        """
        We expect a graph like this.

                    begin
                      |
                outer_branch_point +------
                      |            |       \
                  branch0_a        |      branch2.entry
                      |            |           |
                      |            |        branch2_a
                      |            |           |
                      |            |          /
                      |            |         /
                      |            |        /
                      |            branch1_a
                      |            /
                      |           /
                      |          /
                      |         /
                      end _____/
        """
        expected_edges = {
            (0, outer_branch_point),
            (outer_branch_point, branch0_a),
            (outer_branch_point, branch2.entry),
            (branch2.entry, branch2_a),
            (branch2_a, branch1_a),
            (branch0.exit, end),
            (branch1.exit, end),
            (branch2.exit, end),
        }
        self.assertEqual(expected_edges, cfg.edges)


    def testLoops(self):
        cfg = pass_state.ControlFlowGraph()

        with pass_state.CfgLoopContext(cfg) as loopA:
            branch_point = cfg.AddStatement()
            with pass_state.CfgBranchContext(cfg, branch_point) as arm0:
                arm0_a = cfg.AddStatement()
                arm0_b = cfg.AddStatement()

            with pass_state.CfgBranchContext(cfg, branch_point) as arm1:
                arm1_a = cfg.AddStatement()
                arm1_b = cfg.AddStatement()

            self.assertEqual(arm0_b, arm0.exit)
            self.assertEqual(arm1_b, arm1.exit)

            with pass_state.CfgLoopContext(cfg) as loopB:
                innerB = cfg.AddStatement()

            self.assertEqual(innerB, loopB.exit)

        end = cfg.AddStatement()

        """
        We expecte a graph like this:.

                    begin
                      |
                    loopA <------+
                      |          |
                      v          |
                 branch_point    |
                   /      \      |
                arm0_a   arm2_a  |
                  |        |     |
                arm0_b   arm2_b  |
                   \      /      |
                    \    /       |
                     loopB <-+   |
                      |      |   |
                     innerB -+---+
                      |
                      end
        """
        expected_edges = {
            (0, loopA.entry),
            (loopA.entry, branch_point),
            (branch_point, arm0_a), (branch_point, arm1_a),
            (arm0_a, arm0_b),
            (arm1_a, arm1_b),
            (arm0_b, loopB.entry), (arm1_b, loopB.entry),
            (loopB.entry, innerB),
            (innerB, loopA.entry), (innerB, loopB.entry),
            (innerB, end),
        }
        self.assertEqual(expected_edges, cfg.edges)


    def testLoops2(self):
        cfg = pass_state.ControlFlowGraph()

        with pass_state.CfgLoopContext(cfg) as loopA:
            with pass_state.CfgLoopContext(cfg) as loopB:
                innerB = cfg.AddStatement()

            innerA = cfg.AddStatement()

        end = cfg.AddStatement()

        expected_edges = {
            (0, loopA.entry),
            (loopA.entry, loopB.entry),
            (loopB.entry, innerB),
            (innerB, innerA),
            (innerB, loopB.entry),
            (innerA, loopA.entry),
            (innerA, end),
        }
        self.assertEqual(expected_edges, cfg.edges)

    def testDeepTry(self):
        """
        A code snippet like the following.

        1 while i < n:
        2   for prog in cases:
        3      try:
        4        result = f(prog)
               except ParseError as e:
        5        num_exceptions += 1
        6        continue
        7   i += 1

        8   mylib.MaybeCollect()  # manual GC point

        9 log('num_exceptions = %d', num_exceptions)
        """
        cfg = pass_state.ControlFlowGraph()

        with pass_state.CfgLoopContext(cfg) as loopA:
            with pass_state.CfgLoopContext(cfg) as loopB:
                with pass_state.CfgBlockContext(cfg) as try_block:
                    try_s0 = cfg.AddStatement()

                with pass_state.CfgBlockContext(cfg, try_block.exit) as except_block:
                    except_s0 = cfg.AddStatement()
                    cont = cfg.AddStatement()
                    cfg.AddEdge(cont, loopB.entry)
                    cfg.AddDeadend(cont)

            a_s0 = cfg.AddStatement()
            a_s1 = cfg.AddStatement()

        log_stmt = cfg.AddStatement()
        end = cfg.AddStatement()

        expected_edges = {
            (0, loopA.entry),
            (loopA.entry, loopB.entry),
            (loopB.entry, try_block.entry),
            (try_block.entry, try_s0),
            (try_s0, except_s0),
            (try_s0, loopB.entry),
            (except_s0, cont),
            (cont, loopB.entry),
            (try_block.exit, a_s0),
            (a_s0, a_s1),
            (a_s1, loopA.entry),
            (a_s1, log_stmt),
            (log_stmt, end),
        }
        self.assertEqual(expected_edges, cfg.edges)



if __name__ == '__main__':
    unittest.main()
