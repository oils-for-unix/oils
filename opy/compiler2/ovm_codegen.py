#!/usr/bin/python
from __future__ import print_function
"""
ovm_codegen.py
"""

from . import ast
from . import pyassem
from . import pycodegen
from .visitor import ASTVisitor

Frame = pyassem.Frame
#CodeGenerator = pycodegen.TopLevelCodeGenerator


class CodeGenerator(ASTVisitor):

    def __init__(self, ctx, frame, graph):
        ASTVisitor.__init__(self)
        self.ctx = ctx  # passed down to child CodeGenerator instances
        self.frame = frame
        self.graph = graph

    def _Default(self, node):
        raise AssertionError('%s is unhandled' % node.__class__)

    def Start(self):
        # NOTE: Not used at the top level?
        print('Start')

    def Finish(self):
        print('Finish')

    # Ignore imports
    def visitFrom(self, node):
      pass

    def visitDiscard(self, node):
        self.visit(node.expr)
        #self.emit('POP_TOP')

    def visitModule(self, node):
        print('Module')
        print(node)
        self.visit(node.node)

    def visitStmt(self, node):
        print('Stmt')
        for child in node.nodes:
          self.visit(child)

    def visitWhile(self, node):
        print('While')
        self.visit(node.test)
        self.visit(node.body)
        if node.else_:
            raise AssertionError('else not allowed')

    def visitIf(self, node):
        print('If')
        #print(dir(node))
        for i, (test, suite) in enumerate(node.tests):
            self.visit(test)
            self.visit(suite)
        if node.else_:
            self.visit(node.else_)

    def visitBreak(self, node):
        print('Break')

    def visitName(self, node):
        print('Name')
        #self.loadName(node.name)
        pass

    def visitAssName(self, node):
        print('AssName')
        if node.flags == 'OP_ASSIGN':
            #self.storeName(node.name)
            pass
        elif node.flags == 'OP_DELETE':
            #self.delName(node.name)
            pass
        else:
            print("oops", node.flags)

    # When are there multiple assignments?
    def visitAssign(self, node):
        print('Assign')
        self.visit(node.expr)
        dups = len(node.nodes) - 1
        for i, elt in enumerate(node.nodes):
            if i < dups:
                self.emit('DUP_TOP')
            if isinstance(elt, ast.Node):
                self.visit(elt)

    def binaryOp(self, node, op):
        self.visit(node.left)
        self.visit(node.right)
        #self.emit(op)

    def visitAdd(self, node):
        print('Add')
        return self.binaryOp(node, 'BINARY_ADD')

    def visitCompare(self, node):
        print('Compare')
        self.visit(node.expr)
        # I guess this is 1 < a < b < 2 ?
        return
        cleanup = self.newBlock()
        for op, code in node.ops[:-1]:
            self.visit(code)
            self.emit('DUP_TOP')
            self.emit('ROT_THREE')
            self.emit('COMPARE_OP', op)
            self.emit('JUMP_IF_FALSE_OR_POP', cleanup)
            self.nextBlock()
        # now do the last comparison
        if node.ops:
            op, code = node.ops[-1]
            self.visit(code)
            self.emit('COMPARE_OP', op)
        if len(node.ops) > 1:
            end = self.newBlock()
            self.emit('JUMP_FORWARD', end)
            self.startBlock(cleanup)
            self.emit('ROT_TWO')
            self.emit('POP_TOP')
            self.nextBlock(end)

    # For Fibonacci, this is always print().
    # TODO: Look up type or at least arity statically?

    def visitCallFunc(self, node):
        print('CallFunc')
        self.visit(node.node)
        for arg in node.args:
            self.visit(arg)
        # NOTE: Don't support these?  We do use *args, but they can be
        # evaluated at compile-time?
        if node.star_args is not None:
            self.visit(node.star_args)
        if node.dstar_args is not None:
            self.visit(node.dstar_args)

    def visitConst(self, node):
        print('Const')
        #self.emit('LOAD_CONST', node.value)
        pass
