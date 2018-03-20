from . import ast, pyassem, misc, symbols
from .visitor import ASTVisitor
from .consts import (
    SC_LOCAL, SC_GLOBAL_IMPLICIT, SC_GLOBAL_EXPLICIT, SC_FREE, SC_CELL)

# NOTE: removed CO_NESTED because it is unused
from .consts import (
    CO_VARARGS, CO_VARKEYWORDS, CO_NEWLOCALS,
    CO_GENERATOR, CO_FUTURE_DIVISION,
    CO_FUTURE_ABSIMPORT, CO_FUTURE_WITH_STATEMENT, CO_FUTURE_PRINT_FUNCTION)

callfunc_opcode_info = {
    # (Have *args, Have **args) : opcode
    (0,0) : "CALL_FUNCTION",
    (1,0) : "CALL_FUNCTION_VAR",
    (0,1) : "CALL_FUNCTION_KW",
    (1,1) : "CALL_FUNCTION_VAR_KW",
}

LOOP = 1
EXCEPT = 2
TRY_FINALLY = 3
END_FINALLY = 4


# TODO: Move this mutable global somewhere.
gLambdaCounter = 0


class LocalNameFinder(ASTVisitor):
    """Find local names in scope"""
    def __init__(self, names=None):
        ASTVisitor.__init__(self)
        self.names = names or set()
        self.globals = set()

    # XXX list comprehensions and for loops

    def getLocals(self):
        # TODO: set difference
        for elt in self.globals:
            if elt in self.names:
                self.names.remove(elt)
        return self.names

    def visitDict(self, node):
        pass

    def visitGlobal(self, node):
        for name in node.names:
            self.globals.add(name)

    def visitFunction(self, node):
        self.names.add(node.name)

    def visitLambda(self, node):
        pass

    def visitImport(self, node):
        for name, alias in node.names:
            self.names.add(alias or name)

    def visitFrom(self, node):
        for name, alias in node.names:
            self.names.add(alias or name)

    def visitClass(self, node):
        self.names.add(node.name)

    def visitAssName(self, node):
        self.names.add(node.name)


def is_constant_false(node):
    if isinstance(node, ast.Const):
        if not node.value:
            return 1
    return 0


class Stack(list):

    def push(self, elt):
        self.append(elt)

    def top(self):
        return self[-1]


class CodeGenerator(ASTVisitor):
    """Defines basic code generator for Python bytecode

    This class is an abstract base class.  Concrete subclasses must
    define an __init__() that defines self.graph and then calls the
    __init__() defined in this class.
    """
    optimized = 0  # is namespace access optimized?
    class_name = None  # provide default for instance variable

    def __init__(self, graph, ctx):
        ASTVisitor.__init__(self)
        self.graph = graph
        self.ctx = ctx  # passed down to child CodeGenerator instances

        self.locals = Stack()
        self.setups = Stack()
        self.last_lineno = None
        self._div_op = "BINARY_DIVIDE"

        # Set up methods
        self.emit = self.graph.emit
        self.newBlock = self.graph.newBlock
        self.startBlock = self.graph.startBlock
        self.nextBlock = self.graph.nextBlock
        self.setDocstring = self.graph.setDocstring

        # Set flags based on future features
        for feature in ctx.futures:
            if feature == "division":
                self.graph.setFlag(CO_FUTURE_DIVISION)
                self._div_op = "BINARY_TRUE_DIVIDE"
            elif feature == "absolute_import":
                self.graph.setFlag(CO_FUTURE_ABSIMPORT)
            elif feature == "with_statement":
                self.graph.setFlag(CO_FUTURE_WITH_STATEMENT)
            elif feature == "print_function":
                self.graph.setFlag(CO_FUTURE_PRINT_FUNCTION)

    #
    # Two methods that subclasses must implement.
    #

    def _Start(self):
        raise NotImplementedError

    def Finish(self):
        raise NotImplementedError

    def Start(self):
        self.graph.setFreeVars(self.scope.get_free_vars())
        self.graph.setCellVars(self.scope.get_cell_vars())
        self._Start()

    def mangle(self, name):
        return misc.mangle(name, self.class_name)

    def parseSymbols(self, tree):
        s = symbols.SymbolVisitor()
        s.Dispatch(tree)
        return s.scopes

    # Next five methods handle name access

    def storeName(self, name):
        self._nameOp('STORE', name)

    def loadName(self, name):
        self._nameOp('LOAD', name)

    def delName(self, name):
        self._nameOp('DELETE', name)

    def _nameOp(self, prefix, name):
        name = self.mangle(name)
        scope = self.scope.check_name(name)
        if scope == SC_LOCAL:
            if not self.optimized:
                self.emit(prefix + '_NAME', name)
            else:
                self.emit(prefix + '_FAST', name)
        elif scope == SC_GLOBAL_EXPLICIT:
            self.emit(prefix + '_GLOBAL', name)
        elif scope == SC_GLOBAL_IMPLICIT:
            if not self.optimized:
                self.emit(prefix + '_NAME', name)
            else:
                self.emit(prefix + '_GLOBAL', name)
        elif scope == SC_FREE or scope == SC_CELL:
            self.emit(prefix + '_DEREF', name)
        else:
            raise RuntimeError, "unsupported scope for var %s: %d" % \
                  (name, scope)

    def _implicitNameOp(self, prefix, name):
        """Emit name ops for names generated implicitly by for loops

        The interpreter generates names that start with a period or
        dollar sign.  The symbol table ignores these names because
        they aren't present in the program text.
        """
        if self.optimized:
            self.emit(prefix + '_FAST', name)
        else:
            self.emit(prefix + '_NAME', name)

    # The set_lineno() function and the explicit emit() calls for
    # SET_LINENO below are only used to generate the line number table.
    # As of Python 2.3, the interpreter does not have a SET_LINENO
    # instruction.  pyassem treats SET_LINENO opcodes as a special case.

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

    def visitModule(self, node):
        self.scopes = self.parseSymbols(node)
        self.scope = self.scopes[node]
        self.emit('SET_LINENO', 0)
        if node.doc:
            self.emit('LOAD_CONST', node.doc)
            self.storeName('__doc__')

        lnf = LocalNameFinder()
        lnf.Dispatch(node.node)

        self.locals.push(lnf.getLocals())
        self.visit(node.node)
        self.emit('LOAD_CONST', None)
        self.emit('RETURN_VALUE')

    def visitExpression(self, node):
        self.set_lineno(node)
        self.scopes = self.parseSymbols(node)
        self.scope = self.scopes[node]
        self.visit(node.node)
        self.emit('RETURN_VALUE')

    # Differences between functions and lambdas:
    # - lambdas need an auto-generated name for the code object
    # - lamdbda don't have docstrings
    # - lambdas can't have decorators
    # - code gen: non-lambdas need an extra LOAD_CONST at the end, see Finish()

    def visitFunction(self, node):
        if node.decorators:
            for decorator in node.decorators.nodes:
                self.visit(decorator)
            ndecorators = len(node.decorators.nodes)
        else:
            ndecorators = 0

        _CheckNoTupleArgs(node)
        graph = pyassem.PyFlowGraph(node.name, self.ctx.filename, optimized=1)
        graph.setArgs(node.argnames)

        gen = FunctionCodeGenerator(graph, self.ctx, node, self.scopes,
                                    self.class_name)

        self._funcOrLambda(node, gen, ndecorators)

        # TODO: This seems like a bug.  We already setDocstring in FindLocals()
        # on the FunctionCodeGenerator below.  This seems to mean that the
        # MODULE gets the docstring of the last function?  But this changes the
        # output.
        if node.doc:
            self.setDocstring(node.doc)
        self.storeName(node.name)

    def visitLambda(self, node):
        global gLambdaCounter
        obj_name = "<lambda.%d>" % gLambdaCounter
        gLambdaCounter += 1

        _CheckNoTupleArgs(node)
        graph = pyassem.PyFlowGraph(obj_name, self.ctx.filename, optimized=1)
        graph.setArgs(node.argnames)

        gen = LambdaCodeGenerator(graph, self.ctx, node, self.scopes,
                                  self.class_name)

        self._funcOrLambda(node, gen, 0)

    def _funcOrLambda(self, node, gen, ndecorators):
        gen.Start()
        gen.FindLocals()
        gen.Dispatch(node.code)
        gen.Finish()

        self.set_lineno(node)
        for default in node.defaults:
            self.visit(default)
        self._makeClosure(gen, len(node.defaults))
        for i in xrange(ndecorators):
            self.emit('CALL_FUNCTION', 1)

    def visitClass(self, node):
        graph = pyassem.PyFlowGraph(node.name, self.ctx.filename,
                                    optimized=0, klass=1)
        gen = ClassCodeGenerator(graph, self.ctx, node, self.scopes)

        gen.Start()
        gen.FindLocals()
        gen.Dispatch(node.code)
        gen.Finish()

        self.set_lineno(node)
        self.emit('LOAD_CONST', node.name)
        for base in node.bases:
            self.visit(base)
        self.emit('BUILD_TUPLE', len(node.bases))
        self._makeClosure(gen, 0)
        self.emit('CALL_FUNCTION', 0)
        self.emit('BUILD_CLASS')
        self.storeName(node.name)

    # The next few implement control-flow statements

    def visitIf(self, node):
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

    def visitWhile(self, node):
        self.set_lineno(node)

        loop = self.newBlock()
        else_ = self.newBlock()

        after = self.newBlock()
        self.emit('SETUP_LOOP', after)

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

    def visitFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()
        after = self.newBlock()
        self.setups.push((LOOP, start))

        self.set_lineno(node)
        self.emit('SETUP_LOOP', after)
        self.visit(node.list)
        self.emit('GET_ITER')

        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emit('FOR_ITER', anchor)
        self.visit(node.assign)
        self.visit(node.body)
        self.emit('JUMP_ABSOLUTE', start)
        self.nextBlock(anchor)
        self.emit('POP_BLOCK')
        self.setups.pop()
        if node.else_:
            self.visit(node.else_)
        self.nextBlock(after)

    def visitBreak(self, node):
        if not self.setups:
            raise SyntaxError, "'break' outside loop (%s, %d)" % \
                  (self.ctx.filename, node.lineno)
        self.set_lineno(node)
        self.emit('BREAK_LOOP')

    def visitContinue(self, node):
        if not self.setups:
            raise SyntaxError, "'continue' outside loop (%s, %d)" % \
                  (self.ctx.filename, node.lineno)
        kind, block = self.setups.top()
        if kind == LOOP:
            self.set_lineno(node)
            self.emit('JUMP_ABSOLUTE', block)
            self.nextBlock()
        elif kind == EXCEPT or kind == TRY_FINALLY:
            self.set_lineno(node)
            # find the block that starts the loop
            top = len(self.setups)
            while top > 0:
                top = top - 1
                kind, loop_block = self.setups[top]
                if kind == LOOP:
                    break
            if kind != LOOP:
                raise SyntaxError, "'continue' outside loop (%s, %d)" % \
                      (self.ctx.filename, node.lineno)
            self.emit('CONTINUE_LOOP', loop_block)
            self.nextBlock()
        elif kind == END_FINALLY:
            msg = "'continue' not allowed inside 'finally' clause (%s, %d)"
            raise SyntaxError, msg % (self.ctx.filename, node.lineno)

    def visitTest(self, node, jump):
        end = self.newBlock()
        for child in node.nodes[:-1]:
            self.visit(child)
            self.emit(jump, end)
            self.nextBlock()
        self.visit(node.nodes[-1])
        self.nextBlock(end)

    def visitAnd(self, node):
        self.visitTest(node, 'JUMP_IF_FALSE_OR_POP')

    def visitOr(self, node):
        self.visitTest(node, 'JUMP_IF_TRUE_OR_POP')

    def visitIfExp(self, node):
        endblock = self.newBlock()
        elseblock = self.newBlock()
        self.visit(node.test)
        self.emit('POP_JUMP_IF_FALSE', elseblock)
        self.visit(node.then)
        self.emit('JUMP_FORWARD', endblock)
        self.nextBlock(elseblock)
        self.visit(node.else_)
        self.nextBlock(endblock)

    def visitCompare(self, node):
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

    # list comprehensions
    def visitListComp(self, node):
        self.set_lineno(node)
        # setup list
        self.emit('BUILD_LIST', 0)

        stack = []
        for i, for_ in enumerate(node.quals):
            start, anchor = self.visit(for_)
            cont = None
            for if_ in for_.ifs:
                if cont is None:
                    cont = self.newBlock()
                self.visit(if_, cont)
            stack.insert(0, (start, cont, anchor))

        self.visit(node.expr)
        self.emit('LIST_APPEND', len(node.quals) + 1)

        for start, cont, anchor in stack:
            if cont:
                self.nextBlock(cont)
            self.emit('JUMP_ABSOLUTE', start)
            self.startBlock(anchor)

    def visitSetComp(self, node):
        self.set_lineno(node)
        # setup list
        self.emit('BUILD_SET', 0)

        stack = []
        for i, for_ in enumerate(node.quals):
            start, anchor = self.visit(for_)
            cont = None
            for if_ in for_.ifs:
                if cont is None:
                    cont = self.newBlock()
                self.visit(if_, cont)
            stack.insert(0, (start, cont, anchor))

        self.visit(node.expr)
        self.emit('SET_ADD', len(node.quals) + 1)

        for start, cont, anchor in stack:
            if cont:
                self.nextBlock(cont)
            self.emit('JUMP_ABSOLUTE', start)
            self.startBlock(anchor)

    def visitDictComp(self, node):
        self.set_lineno(node)
        # setup list
        self.emit('BUILD_MAP', 0)

        stack = []
        for i, for_ in enumerate(node.quals):
            start, anchor = self.visit(for_)
            cont = None
            for if_ in for_.ifs:
                if cont is None:
                    cont = self.newBlock()
                self.visit(if_, cont)
            stack.insert(0, (start, cont, anchor))

        self.visit(node.value)
        self.visit(node.key)
        self.emit('MAP_ADD', len(node.quals) + 1)

        for start, cont, anchor in stack:
            if cont:
                self.nextBlock(cont)
            self.emit('JUMP_ABSOLUTE', start)
            self.startBlock(anchor)

    def visitListCompFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()

        self.visit(node.list)
        self.emit('GET_ITER')
        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emit('FOR_ITER', anchor)
        self.nextBlock()
        self.visit(node.assign)
        return start, anchor

    def visitListCompIf(self, node, branch):
        self.set_lineno(node, force=True)
        self.visit(node.test)
        self.emit('POP_JUMP_IF_FALSE', branch)
        self.newBlock()

    def _makeClosure(self, gen, args):
        frees = gen.scope.get_free_vars()
        if frees:
            for name in frees:
                self.emit('LOAD_CLOSURE', name)
            self.emit('BUILD_TUPLE', len(frees))
            self.emit('LOAD_CONST', gen)
            self.emit('MAKE_CLOSURE', args)
        else:
            self.emit('LOAD_CONST', gen)
            self.emit('MAKE_FUNCTION', args)

    def visitGenExpr(self, node):
        isLambda = 1  # TODO: Shouldn't be a lambda?  Note Finish().
        if isLambda:
            global gLambdaCounter
            obj_name = "<lambda.%d>" % gLambdaCounter
            gLambdaCounter += 1
        else:
            # TODO: enable this.  This is more like CPython.  Note that I worked
            # worked around a bug in byterun due to NOT having this.
            # http://bugs.python.org/issue19611
            # That workaround may no longer be necessary if we switch.
            obj_name = '<genexpr>'

        graph = pyassem.PyFlowGraph(obj_name, self.ctx.filename, optimized=1)
        graph.setArgs(node.argnames)
        gen = GenExprCodeGenerator(graph, self.ctx, node, self.scopes,
                                   self.class_name)

        gen.Start()
        gen.FindLocals()
        gen.Dispatch(node.code)
        gen.Finish()

        self.set_lineno(node)
        self._makeClosure(gen, 0)
        # precomputation of outmost iterable
        self.visit(node.code.quals[0].iter)
        self.emit('GET_ITER')
        self.emit('CALL_FUNCTION', 1)

    def visitGenExprInner(self, node):
        self.set_lineno(node)
        # setup list

        stack = []
        for i, for_ in enumerate(node.quals):
            start, anchor, end = self.visit(for_)
            cont = None
            for if_ in for_.ifs:
                if cont is None:
                    cont = self.newBlock()
                self.visit(if_, cont)
            stack.insert(0, (start, cont, anchor, end))

        self.visit(node.expr)
        self.emit('YIELD_VALUE')
        self.emit('POP_TOP')

        for start, cont, anchor, end in stack:
            if cont:
                self.nextBlock(cont)
            self.emit('JUMP_ABSOLUTE', start)
            self.startBlock(anchor)
            self.emit('POP_BLOCK')
            self.setups.pop()
            self.nextBlock(end)

        self.emit('LOAD_CONST', None)

    def visitGenExprFor(self, node):
        start = self.newBlock()
        anchor = self.newBlock()
        end = self.newBlock()

        self.setups.push((LOOP, start))
        self.emit('SETUP_LOOP', end)

        if node.is_outmost:
            self.loadName('.0')
        else:
            self.visit(node.iter)
            self.emit('GET_ITER')

        self.nextBlock(start)
        self.set_lineno(node, force=True)
        self.emit('FOR_ITER', anchor)
        self.nextBlock()
        self.visit(node.assign)
        return start, anchor, end

    def visitGenExprIf(self, node, branch):
        self.set_lineno(node, force=True)
        self.visit(node.test)
        self.emit('POP_JUMP_IF_FALSE', branch)
        self.newBlock()

    # exception related

    def visitAssert(self, node):
        # XXX would be interesting to implement this via a
        # transformation of the AST before this stage
        if __debug__:
            end = self.newBlock()
            self.set_lineno(node)
            # XXX AssertionError appears to be special case -- it is always
            # loaded as a global even if there is a local name.  I guess this
            # is a sort of renaming op.
            self.nextBlock()
            self.visit(node.test)
            self.emit('POP_JUMP_IF_TRUE', end)
            self.nextBlock()
            self.emit('LOAD_GLOBAL', 'AssertionError')
            if node.fail:
                self.visit(node.fail)
                self.emit('RAISE_VARARGS', 2)
            else:
                self.emit('RAISE_VARARGS', 1)
            self.nextBlock(end)

    def visitRaise(self, node):
        self.set_lineno(node)
        n = 0
        if node.expr1:
            self.visit(node.expr1)
            n = n + 1
        if node.expr2:
            self.visit(node.expr2)
            n = n + 1
        if node.expr3:
            self.visit(node.expr3)
            n = n + 1
        self.emit('RAISE_VARARGS', n)

    def visitTryExcept(self, node):
        body = self.newBlock()
        handlers = self.newBlock()
        end = self.newBlock()
        if node.else_:
            lElse = self.newBlock()
        else:
            lElse = end
        self.set_lineno(node)
        self.emit('SETUP_EXCEPT', handlers)
        self.nextBlock(body)
        self.setups.push((EXCEPT, body))
        self.visit(node.body)
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emit('JUMP_FORWARD', lElse)
        self.startBlock(handlers)

        last = len(node.handlers) - 1
        for i, (expr, target, body) in enumerate(node.handlers):
            expr, target, body = node.handlers[i]
            self.set_lineno(expr)
            if expr:
                self.emit('DUP_TOP')
                self.visit(expr)
                self.emit('COMPARE_OP', 'exception match')
                next = self.newBlock()
                self.emit('POP_JUMP_IF_FALSE', next)
                self.nextBlock()
            self.emit('POP_TOP')
            if target:
                self.visit(target)
            else:
                self.emit('POP_TOP')
            self.emit('POP_TOP')
            self.visit(body)
            self.emit('JUMP_FORWARD', end)
            if expr:
                self.nextBlock(next)
            else:
                self.nextBlock()
        self.emit('END_FINALLY')
        if node.else_:
            self.nextBlock(lElse)
            self.visit(node.else_)
        self.nextBlock(end)

    def visitTryFinally(self, node):
        body = self.newBlock()
        final = self.newBlock()
        self.set_lineno(node)
        self.emit('SETUP_FINALLY', final)
        self.nextBlock(body)
        self.setups.push((TRY_FINALLY, body))
        self.visit(node.body)
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emit('LOAD_CONST', None)
        self.nextBlock(final)
        self.setups.push((END_FINALLY, final))
        self.visit(node.final)
        self.emit('END_FINALLY')
        self.setups.pop()

    __with_count = 0

    def visitWith(self, node):
        body = self.newBlock()
        final = self.newBlock()
        self.__with_count += 1
        valuevar = "_[%d]" % self.__with_count
        self.set_lineno(node)
        self.visit(node.expr)
        self.emit('DUP_TOP')
        self.emit('LOAD_ATTR', '__exit__')
        self.emit('ROT_TWO')
        self.emit('LOAD_ATTR', '__enter__')
        self.emit('CALL_FUNCTION', 0)
        if node.vars is None:
            self.emit('POP_TOP')
        else:
            self._implicitNameOp('STORE', valuevar)
        self.emit('SETUP_FINALLY', final)
        self.nextBlock(body)
        self.setups.push((TRY_FINALLY, body))
        if node.vars is not None:
            self._implicitNameOp('LOAD', valuevar)
            self._implicitNameOp('DELETE', valuevar)
            self.visit(node.vars)
        self.visit(node.body)
        self.emit('POP_BLOCK')
        self.setups.pop()
        self.emit('LOAD_CONST', None)
        self.nextBlock(final)
        self.setups.push((END_FINALLY, final))
        self.emit('WITH_CLEANUP')
        self.emit('END_FINALLY')
        self.setups.pop()
        self.__with_count -= 1

    # misc

    def visitDiscard(self, node):
        self.set_lineno(node)
        self.visit(node.expr)
        self.emit('POP_TOP')

    def visitConst(self, node):
        self.emit('LOAD_CONST', node.value)

    def visitKeyword(self, node):
        self.emit('LOAD_CONST', node.name)
        self.visit(node.expr)

    def visitGlobal(self, node):
        # no code to generate
        pass

    def visitName(self, node):
        self.set_lineno(node)
        self.loadName(node.name)

    def visitPass(self, node):
        self.set_lineno(node)

    def visitImport(self, node):
        self.set_lineno(node)
        level = 0 if self.graph.checkFlag(CO_FUTURE_ABSIMPORT) else -1
        for name, alias in node.names:
            self.emit('LOAD_CONST', level)
            self.emit('LOAD_CONST', None)
            self.emit('IMPORT_NAME', name)
            mod = name.split(".")[0]
            if alias:
                self._resolveDots(name)
                self.storeName(alias)
            else:
                self.storeName(mod)

    def visitFrom(self, node):
        self.set_lineno(node)
        level = node.level
        if level == 0 and not self.graph.checkFlag(CO_FUTURE_ABSIMPORT):
            level = -1
        fromlist = tuple(name for (name, alias) in node.names)
        self.emit('LOAD_CONST', level)
        self.emit('LOAD_CONST', fromlist)
        self.emit('IMPORT_NAME', node.modname)
        for name, alias in node.names:
            if name == '*':
                self.namespace = 0
                self.emit('IMPORT_STAR')
                # There can only be one name w/ from ... import *
                assert len(node.names) == 1
                return
            else:
                self.emit('IMPORT_FROM', name)
                self._resolveDots(name)
                self.storeName(alias or name)
        self.emit('POP_TOP')

    def _resolveDots(self, name):
        elts = name.split(".")
        if len(elts) == 1:
            return
        for elt in elts[1:]:
            self.emit('LOAD_ATTR', elt)

    def visitGetattr(self, node):
        self.visit(node.expr)
        self.emit('LOAD_ATTR', self.mangle(node.attrname))

    # next five implement assignments

    def visitAssign(self, node):
        self.set_lineno(node)
        self.visit(node.expr)
        dups = len(node.nodes) - 1
        for i, elt in enumerate(node.nodes):
            if i < dups:
                self.emit('DUP_TOP')
            if isinstance(elt, ast.Node):
                self.visit(elt)

    def visitAssName(self, node):
        if node.flags == 'OP_ASSIGN':
            self.storeName(node.name)
        elif node.flags == 'OP_DELETE':
            self.set_lineno(node)
            self.delName(node.name)
        else:
            print("oops", node.flags)

    def visitAssAttr(self, node):
        self.visit(node.expr)
        if node.flags == 'OP_ASSIGN':
            self.emit('STORE_ATTR', self.mangle(node.attrname))
        elif node.flags == 'OP_DELETE':
            self.emit('DELETE_ATTR', self.mangle(node.attrname))
        else:
            print("warning: unexpected flags:", node.flags)
            print(node)

    def _visitAssSequence(self, node, op='UNPACK_SEQUENCE'):
        if findOp(node) != 'OP_DELETE':
            self.emit(op, len(node.nodes))
        for child in node.nodes:
            self.visit(child)

    visitAssTuple = _visitAssSequence
    visitAssList = _visitAssSequence

    # augmented assignment

    def visitAugAssign(self, node):
        self.set_lineno(node)
        aug_node = wrap_aug(node.node)
        self.visit(aug_node, "load")
        self.visit(node.expr)
        self.emit(self._augmented_opcode[node.op])
        self.visit(aug_node, "store")

    _augmented_opcode = {
        '+=' : 'INPLACE_ADD',
        '-=' : 'INPLACE_SUBTRACT',
        '*=' : 'INPLACE_MULTIPLY',
        '/=' : 'INPLACE_DIVIDE',
        '//=': 'INPLACE_FLOOR_DIVIDE',
        '%=' : 'INPLACE_MODULO',
        '**=': 'INPLACE_POWER',
        '>>=': 'INPLACE_RSHIFT',
        '<<=': 'INPLACE_LSHIFT',
        '&=' : 'INPLACE_AND',
        '^=' : 'INPLACE_XOR',
        '|=' : 'INPLACE_OR',
        }

    def visitAugName(self, node, mode):
        if mode == "load":
            self.loadName(node.name)
        elif mode == "store":
            self.storeName(node.name)

    def visitAugGetattr(self, node, mode):
        if mode == "load":
            self.visit(node.expr)
            self.emit('DUP_TOP')
            self.emit('LOAD_ATTR', self.mangle(node.attrname))
        elif mode == "store":
            self.emit('ROT_TWO')
            self.emit('STORE_ATTR', self.mangle(node.attrname))

    def visitAugSlice(self, node, mode):
        if mode == "load":
            self.visitSlice(node, 1)
        elif mode == "store":
            slice = 0
            if node.lower:
                slice = slice | 1
            if node.upper:
                slice = slice | 2
            if slice == 0:
                self.emit('ROT_TWO')
            elif slice == 3:
                self.emit('ROT_FOUR')
            else:
                self.emit('ROT_THREE')
            self.emit('STORE_SLICE+%d' % slice)

    def visitAugSubscript(self, node, mode):
        if mode == "load":
            self.visitSubscript(node, 1)
        elif mode == "store":
            self.emit('ROT_THREE')
            self.emit('STORE_SUBSCR')

    def visitExec(self, node):
        self.visit(node.expr)
        if node.locals is None:
            self.emit('LOAD_CONST', None)
        else:
            self.visit(node.locals)
        if node.globals is None:
            self.emit('DUP_TOP')
        else:
            self.visit(node.globals)
        self.emit('EXEC_STMT')

    def visitCallFunc(self, node):
        pos = 0
        kw = 0
        self.set_lineno(node)
        self.visit(node.node)
        for arg in node.args:
            self.visit(arg)
            if isinstance(arg, ast.Keyword):
                kw = kw + 1
            else:
                pos = pos + 1
        if node.star_args is not None:
            self.visit(node.star_args)
        if node.dstar_args is not None:
            self.visit(node.dstar_args)
        have_star = node.star_args is not None
        have_dstar = node.dstar_args is not None
        opcode = callfunc_opcode_info[have_star, have_dstar]
        self.emit(opcode, kw << 8 | pos)

    def visitPrint(self, node, newline=0):
        self.set_lineno(node)
        if node.dest:
            self.visit(node.dest)
        for child in node.nodes:
            if node.dest:
                self.emit('DUP_TOP')
            self.visit(child)
            if node.dest:
                self.emit('ROT_TWO')
                self.emit('PRINT_ITEM_TO')
            else:
                self.emit('PRINT_ITEM')
        if node.dest and not newline:
            self.emit('POP_TOP')

    def visitPrintnl(self, node):
        self.visitPrint(node, newline=1)
        if node.dest:
            self.emit('PRINT_NEWLINE_TO')
        else:
            self.emit('PRINT_NEWLINE')

    def visitReturn(self, node):
        self.set_lineno(node)
        self.visit(node.value)
        self.emit('RETURN_VALUE')

    def visitYield(self, node):
        self.set_lineno(node)
        self.visit(node.value)
        self.emit('YIELD_VALUE')

    # slice and subscript stuff

    def visitSlice(self, node, aug_flag=None):
        # aug_flag is used by visitAugSlice
        self.visit(node.expr)
        slice = 0
        if node.lower:
            self.visit(node.lower)
            slice = slice | 1
        if node.upper:
            self.visit(node.upper)
            slice = slice | 2
        if aug_flag:
            if slice == 0:
                self.emit('DUP_TOP')
            elif slice == 3:
                self.emit('DUP_TOPX', 3)
            else:
                self.emit('DUP_TOPX', 2)
        if node.flags == 'OP_APPLY':
            self.emit('SLICE+%d' % slice)
        elif node.flags == 'OP_ASSIGN':
            self.emit('STORE_SLICE+%d' % slice)
        elif node.flags == 'OP_DELETE':
            self.emit('DELETE_SLICE+%d' % slice)
        else:
            print("weird slice", node.flags)
            raise

    def visitSubscript(self, node, aug_flag=None):
        self.visit(node.expr)
        for sub in node.subs:
            self.visit(sub)
        if len(node.subs) > 1:
            self.emit('BUILD_TUPLE', len(node.subs))
        if aug_flag:
            self.emit('DUP_TOPX', 2)
        if node.flags == 'OP_APPLY':
            self.emit('BINARY_SUBSCR')
        elif node.flags == 'OP_ASSIGN':
            self.emit('STORE_SUBSCR')
        elif node.flags == 'OP_DELETE':
            self.emit('DELETE_SUBSCR')

    # binary ops

    def binaryOp(self, node, op):
        self.visit(node.left)
        self.visit(node.right)
        self.emit(op)

    def visitAdd(self, node):
        return self.binaryOp(node, 'BINARY_ADD')

    def visitSub(self, node):
        return self.binaryOp(node, 'BINARY_SUBTRACT')

    def visitMul(self, node):
        return self.binaryOp(node, 'BINARY_MULTIPLY')

    def visitDiv(self, node):
        return self.binaryOp(node, self._div_op)

    def visitFloorDiv(self, node):
        return self.binaryOp(node, 'BINARY_FLOOR_DIVIDE')

    def visitMod(self, node):
        return self.binaryOp(node, 'BINARY_MODULO')

    def visitPower(self, node):
        return self.binaryOp(node, 'BINARY_POWER')

    def visitLeftShift(self, node):
        return self.binaryOp(node, 'BINARY_LSHIFT')

    def visitRightShift(self, node):
        return self.binaryOp(node, 'BINARY_RSHIFT')

    # unary ops

    def unaryOp(self, node, op):
        self.visit(node.expr)
        self.emit(op)

    def visitInvert(self, node):
        return self.unaryOp(node, 'UNARY_INVERT')

    def visitUnarySub(self, node):
        return self.unaryOp(node, 'UNARY_NEGATIVE')

    def visitUnaryAdd(self, node):
        return self.unaryOp(node, 'UNARY_POSITIVE')

    def visitUnaryInvert(self, node):
        return self.unaryOp(node, 'UNARY_INVERT')

    def visitNot(self, node):
        return self.unaryOp(node, 'UNARY_NOT')

    def visitBackquote(self, node):
        return self.unaryOp(node, 'UNARY_CONVERT')

    # bit ops

    def bitOp(self, nodes, op):
        self.visit(nodes[0])
        for node in nodes[1:]:
            self.visit(node)
            self.emit(op)

    def visitBitand(self, node):
        return self.bitOp(node.nodes, 'BINARY_AND')

    def visitBitor(self, node):
        return self.bitOp(node.nodes, 'BINARY_OR')

    def visitBitxor(self, node):
        return self.bitOp(node.nodes, 'BINARY_XOR')

    # object constructors

    def visitEllipsis(self, node):
        self.emit('LOAD_CONST', Ellipsis)

    def visitTuple(self, node):
        self.set_lineno(node)
        for elt in node.nodes:
            self.visit(elt)
        self.emit('BUILD_TUPLE', len(node.nodes))

    def visitList(self, node):
        self.set_lineno(node)
        for elt in node.nodes:
            self.visit(elt)
        self.emit('BUILD_LIST', len(node.nodes))

    def visitSet(self, node):
        self.set_lineno(node)
        for elt in node.nodes:
            self.visit(elt)
        self.emit('BUILD_SET', len(node.nodes))

    def visitSliceobj(self, node):
        for child in node.nodes:
            self.visit(child)
        self.emit('BUILD_SLICE', len(node.nodes))

    def visitDict(self, node):
        self.set_lineno(node)
        self.emit('BUILD_MAP', 0)
        for k, v in node.items:
            self.emit('DUP_TOP')
            self.visit(k)
            self.visit(v)
            self.emit('ROT_THREE')
            self.emit('STORE_SUBSCR')


class TopLevelCodeGenerator(CodeGenerator):

    def Finish(self):
        pass


class InteractiveCodeGenerator(TopLevelCodeGenerator):

    def visitDiscard(self, node):
        # XXX Discard means it's an expression.  Perhaps this is a bad
        # name.
        self.visit(node.expr)
        self.emit('PRINT_EXPR')

    def Finish(self):
        # Not sure why I need this?
        self.emit('RETURN_VALUE')


# NOTE: This feature removed in Python 3!  I didn't even know about it!
#
# https://www.python.org/dev/peps/pep-3113/
# def fxn(a, (b, c), d):
#    pass

def _CheckNoTupleArgs(func):
    for i, arg in enumerate(func.argnames):
        if isinstance(arg, tuple):
            raise RuntimeError(
                'Tuple args are not supported: %s in function %s' %
                (arg, func.name))


class _FunctionCodeGenerator(CodeGenerator):
    """Abstract class."""
    optimized = 1

    def __init__(self, graph, ctx, func, scopes, class_name):
        CodeGenerator.__init__(self, graph, ctx)
        self.func = func
        self.scopes = scopes
        self.class_name = class_name

        self.scope = scopes[func]

    def FindLocals(self):
        func = self.func 

        lnf = LocalNameFinder(set(self.func.argnames))
        lnf.Dispatch(func.code)
        self.locals.push(lnf.getLocals())

        if func.varargs:
            self.graph.setFlag(CO_VARARGS)
        if func.kwargs:
            self.graph.setFlag(CO_VARKEYWORDS)
        self.set_lineno(func)


class FunctionCodeGenerator(_FunctionCodeGenerator):

    def _Start(self):
        if self.scope.generator is not None:  # does it have yield in it?
            self.graph.setFlag(CO_GENERATOR)
        if self.func.doc:
            self.setDocstring(self.func.doc)

    def Finish(self):
        self.graph.startExitBlock()
        self.emit('LOAD_CONST', None)
        self.emit('RETURN_VALUE')


class LambdaCodeGenerator(_FunctionCodeGenerator):

    def _Start(self):
        if self.scope.generator is not None:  # does it have yield in it?
            self.graph.setFlag(CO_GENERATOR)

    def Finish(self):
        self.graph.startExitBlock()
        self.emit('RETURN_VALUE')


class GenExprCodeGenerator(_FunctionCodeGenerator):

    def _Start(self):
        self.graph.setFlag(CO_GENERATOR)  # It's always a generator

    def Finish(self):
        self.graph.startExitBlock()
        self.emit('RETURN_VALUE')


class ClassCodeGenerator(CodeGenerator):

    def __init__(self, graph, ctx, klass, scopes):
        CodeGenerator.__init__(self, graph, ctx)

        self.klass = klass
        self.scopes = scopes

        self.class_name = klass.name
        self.scope = scopes[klass]

    def _Start(self):
        self.set_lineno(self.klass)
        self.emit("LOAD_GLOBAL", "__name__")
        self.storeName("__module__")
        if self.klass.doc:
            self.emit("LOAD_CONST", self.klass.doc)
            self.storeName('__doc__')

    def FindLocals(self):
        lnf = LocalNameFinder()
        lnf.Dispatch(self.klass.code)
        self.locals.push(lnf.getLocals())

        self.graph.setFlag(CO_NEWLOCALS)
        if self.klass.doc:
            self.setDocstring(self.klass.doc)

    def Finish(self):
        self.graph.startExitBlock()
        self.emit('LOAD_LOCALS')
        self.emit('RETURN_VALUE')


def findOp(node):
    """Find the op (DELETE, LOAD, STORE) in an AssTuple tree"""
    v = OpFinder()
    v.Dispatch(node)
    return v.op


class OpFinder(ASTVisitor):

    def __init__(self):
        ASTVisitor.__init__(self)
        self.op = None

    def visitAssName(self, node):
        if self.op is None:
            self.op = node.flags
        elif self.op != node.flags:
            raise ValueError, "mixed ops in stmt"
    visitAssAttr = visitAssName
    visitSubscript = visitAssName


# TODO: I don't understand this.  It looks like it does nothing, but removing
# wrap_aug() breaks.
class Delegator(object):
    """Base class to support delegation for augmented assignment nodes

    To generator code for augmented assignments, we use the following
    wrapper classes.  In visitAugAssign, the left-hand expression node
    is visited twice.  The first time the visit uses the normal method
    for that node .  The second time the visit uses a different method
    that generates the appropriate code to perform the assignment.
    These delegator classes wrap the original AST nodes in order to
    support the variant visit methods.
    """
    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, attr):
        return getattr(self.obj, attr)

class AugGetattr(Delegator):
    pass

class AugName(Delegator):
    pass

class AugSlice(Delegator):
    pass

class AugSubscript(Delegator):
    pass

AUG_WRAPPER = {
    ast.Getattr: AugGetattr,
    ast.Name: AugName,
    ast.Slice: AugSlice,
    ast.Subscript: AugSubscript,
    }

def wrap_aug(node):
    return AUG_WRAPPER[node.__class__](node)
