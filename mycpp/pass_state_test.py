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
        arm0_a = cfg.AddStatement(branch_point)
        arm0_b = cfg.AddStatement(arm0_a) # block statement 2
        arm0_c = cfg.AddStatement(arm0_b) # block statement 3

        # frist statement in elif block
        arm1_a = cfg.AddStatement(branch_point)
        arm1_b = cfg.AddStatement(arm1_a) # block statement 2

        # frist statement in else block
        arm2_a = cfg.AddStatement(branch_point)
        arm2_b = cfg.AddStatement(arm2_a) # block statement 2

        cfg.SetBranchExits([arm0_c, arm1_b, arm2_b])

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


    def testLoops(self):
        cfg = pass_state.ControlFlowGraph()

        with pass_state.CfgLoopContext(cfg) as loopA:
            branch_point = cfg.AddStatement()
            arm0_a = cfg.AddStatement(branch_point)
            arm0_b = cfg.AddStatement(arm0_a)

            arm1_a = cfg.AddStatement(branch_point)
            arm1_b = cfg.AddStatement(arm1_a)
            cfg.SetBranchExits([arm0_b, arm1_b])

            with pass_state.CfgLoopContext(cfg) as loopB:
                innerB = cfg.AddStatement()

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


if __name__ == '__main__':
    unittest.main()
