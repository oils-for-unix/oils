#!/usr/bin/python
from __future__ import print_function
"""
ovm_codegen.py

NOTE: This is a static subset of Python.

Constructs to audit the code for:
- **kwargs (I know I have *args)
- yield -- there are a few
  - StopIteration -- is that special?
- 1 < x < 2 (probably not used)

Static assumptions:
- s % (a,) is (string, tuple)
- a + b is int or float addition

- "function pointers" like self.newBlock = self.graph.newBlock
"""



from . import ast
from . import pyassem
from . import pycodegen
from .visitor import ASTVisitor
from .pycodegen import LocalNameFinder
from .consts import (
    SC_LOCAL, SC_GLOBAL_IMPLICIT, SC_GLOBAL_EXPLICIT, SC_FREE, SC_CELL)

Frame = pyassem.Frame

# Block type?
LOOP = 1


def is_constant_false(node):
    return isinstance(node, ast.Const) and not node.value


class CodeGenerator(ASTVisitor):

    def __init__(self, ctx, frame, graph):
        ASTVisitor.__init__(self)
        self.ctx = ctx  # passed down to child CodeGenerator instances
        self.frame = frame
        self.graph = graph

        self.locals = pycodegen.Stack()
        self.setups = pycodegen.Stack()

        self.emit = self.graph.emit
        self.newBlock = self.graph.newBlock
        self.startBlock = self.graph.startBlock
        self.nextBlock = self.graph.nextBlock

        self.last_lineno = None

    def set_lineno(self, node, force=False):
        """Emit SET_LINENO if necessary.

        The instruction is considered necessary if the node has a
        lineno attribute and it is different than the last lineno
        emitted.

        Returns true if SET_LINENO was emitted.

        There are no rules for when an AST node should have a lineno
        attribute.  The transformer and AST code need to be reviewed
        and a consistent policy implemented and documented.  Until
        then, this method works around missing line numbers.
        """
        lineno = getattr(node, 'lineno', None)
        if lineno is not None and (lineno != self.last_lineno or force):
            self.emit('SET_LINENO', lineno)
            self.last_lineno = lineno
            return True
        return False

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
        self.set_lineno(node)
        self.visit(node.expr)
        self.emit('POP_TOP')

    def visitModule(self, node):
        print('Module')
        self.scope = self.ctx.scopes[node]
        self.emit('SET_LINENO', 0)

        lnf = LocalNameFinder()
        lnf.Dispatch(node.node)

        self.locals.push(lnf.getLocals())
        self.visit(node.node)
        self.emit('LOAD_CONST', None)
        self.emit('RETURN_VALUE')

    def visitStmt(self, node):
        print('Stmt')
        for child in node.nodes:
          self.visit(child)

    def visitWhile(self, node):
        print('While')
        self.set_lineno(node)

        loop = self.newBlock()
        else_ = self.newBlock()

        # After is where 'break' should jump to!
        after = self.newBlock()
        self.emit('SETUP_LOOP', after)

        # 'loop' is where 'continue' should jump to!
        self.nextBlock(loop)
        self.setups.push((LOOP, loop))

        self.set_lineno(node, force=True)
        self.visit(node.test)
        self.emit('POP_JUMP_IF_FALSE', else_ or after)

        self.nextBlock()
        self.visit(node.body)
        self.emit('JUMP_ABSOLUTE', loop)

        self.startBlock(else_) # or just the POPs if not else clause
        self.emit('POP_BLOCK')
        self.setups.pop()
        if node.else_:
            self.visit(node.else_)
        self.nextBlock(after)

    def visitIf(self, node):
        print('If')
        end = self.newBlock()
        for i, (test, suite) in enumerate(node.tests):
            if is_constant_false(test):
                # XXX will need to check generator stuff here
                continue
            self.set_lineno(test)
            self.visit(test)
            nextTest = self.newBlock()
            self.emit('POP_JUMP_IF_FALSE', nextTest)
            self.nextBlock()
            self.visit(suite)
            self.emit('JUMP_FORWARD', end)
            self.startBlock(nextTest)
        if node.else_:
            self.visit(node.else_)
        self.nextBlock(end)

    def visitBreak(self, node):
        print('Break')
        if not self.setups:
            raise SyntaxError("'break' outside loop (%s, %d)" %
                              (self.ctx.filename, node.lineno))
        self.set_lineno(node)

        # TODO: Emit a jump here!  JUMP_FORWARD or something else?
        # We need to know what the next block is!
        self.emit('BREAK_LOOP')

    def visitContinue(self, node):
        print('Continue')
        if not self.setups:
            raise SyntaxError("'continue' outside loop (%s, %d)" %
                              (self.ctx.filename, node.lineno))

        kind, block = self.setups.top()
        if kind == LOOP:
            self.set_lineno(node)
            self.emit('JUMP_ABSOLUTE', block)
            self.nextBlock()
        else:
            msg = "'continue' not handled here (%s, %d)"
            raise SyntaxError(msg % (self.ctx.filename, node.lineno))

    def _nameOp(self, prefix, name):
        # Don't mangle
        #name = self._mangle(name)
        scope = self.scope.check_name(name)

        if scope == SC_LOCAL:
            #suffix = 'FAST' if self._optimized() else 'NAME'
            # TODO: LOAD_FAST
            suffix = 'NAME'
            self.emit('%s_%s' % (prefix, suffix), name)

        elif scope == SC_GLOBAL_EXPLICIT:
            self.emit(prefix + '_GLOBAL', name)

        elif scope == SC_GLOBAL_IMPLICIT:
            #suffix = 'GLOBAL' if self._optimized() else 'NAME'
            # TODO: LOAD_GLOBAL
            suffix = 'NAME'
            self.emit('%s_%s' % (prefix, suffix), name)

        elif scope == SC_FREE or scope == SC_CELL:
            self.emit(prefix + '_DEREF', name)

        else:
            raise RuntimeError, "unsupported scope for var %s: %d" % \
                  (name, scope)

    def loadName(self, name):
        self._nameOp('LOAD', name)

    def visitName(self, node):
        print('Name')
        self.set_lineno(node)
        self.loadName(node.name)

    def storeName(self, name):
        self._nameOp('STORE', name)

    def visitAssName(self, node):
        print('AssName')
        if node.flags == 'OP_ASSIGN':
            self.storeName(node.name)
        elif node.flags == 'OP_DELETE':
            self.set_lineno(node)
            self.delName(node.name)
        else:
            print("oops", node.flags)

    # When are there multiple assignments?
    def visitAssign(self, node):
        print('Assign')
        self.set_lineno(node)
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
        self.emit(op)

    def visitAdd(self, node):
        print('Add')
        return self.binaryOp(node, 'BINARY_ADD')

    def visitCompare(self, node):
        print('Compare')
        # I guess this is 1 < x < y < 3
        self.visit(node.expr)
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
        pos = 0
        kw = 0
        self.set_lineno(node)
        self.visit(node.node)
        for arg in node.args:
            self.visit(arg)
            if isinstance(arg, ast.Keyword):
                kw += 1
            else:
                pos += 1
        self.emit('CALL_FUNCTION', pos)

        return
        # Unused code for f(*args, **kwargs)
        if node.star_args is not None:
            self.visit(node.star_args)
        if node.dstar_args is not None:
            self.visit(node.dstar_args)
        have_star = node.star_args is not None
        have_dstar = node.dstar_args is not None
        #opcode = _CALLFUNC_OPCODE_INFO[have_star, have_dstar]
        #self.emit(opcode, kw << 8 | pos)

    def visitConst(self, node):
        print('Const')
        self.emit('LOAD_CONST', node.value)
