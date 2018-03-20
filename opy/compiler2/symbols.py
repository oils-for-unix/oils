"""Module symbol-table generator"""
from __future__ import print_function

from . import ast
from . import misc
from .consts import SC_LOCAL, SC_GLOBAL_IMPLICIT, SC_GLOBAL_EXPLICIT, \
    SC_FREE, SC_CELL, SC_UNKNOWN
from .visitor import ASTVisitor

import sys
import types


class Scope(object):
    # XXX how much information do I need about each name?
    def __init__(self, name, module, klass=None):
        self.name = name
        self.module = module

        self.defs = set()
        self.uses = set()
        self.globals = set()
        self.params = set()
        self.frees = set()
        self.cells = set()

        self.children = []
        # nested is true if the class could contain free variables,
        # i.e. if it is nested within another function.
        self.nested = None
        self.generator = None
        self.klass = None
        if klass is not None:
            # Strip leading _.  I guess this is for name mangling; you don't
            # want more than one _.
            self.klass = klass.lstrip('_')

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)

    def DebugDump(self):
        print(self.name, self.nested and "nested" or "", file=sys.stderr)
        print("\tglobals: ", self.globals, file=sys.stderr)
        print("\tcells: ", self.cells, file=sys.stderr)
        print("\tdefs: ", self.defs, file=sys.stderr)
        print("\tuses: ", self.uses, file=sys.stderr)
        print("\tfrees:", self.frees, file=sys.stderr)

    def mangle(self, name):
        return misc.mangle(name, self.klass)

    def add_def(self, name):
        self.defs.add(self.mangle(name))

    def add_use(self, name):
        self.uses.add(self.mangle(name))

    def add_global(self, name):
        name = self.mangle(name)
        if name in self.uses or name in self.defs:
            pass # XXX warn about global following def/use
        if name in self.params:
            raise SyntaxError, "%s in %s is global and parameter" % \
                  (name, self.name)
        self.globals.add(name)
        self.module.add_def(name)

    def add_param(self, name):
        name = self.mangle(name)
        self.defs.add(name)
        self.params.add(name)

    def get_names(self):
        return list(self.defs | self.uses | self.globals)  # union

    def add_child(self, child):
        self.children.append(child)

    def get_children(self):
        return self.children

    def check_name(self, name):
        """Return scope of name.

        The scope of a name could be LOCAL, GLOBAL, FREE, or CELL.
        """
        if name in self.globals:
            return SC_GLOBAL_EXPLICIT
        if name in self.cells:
            return SC_CELL
        if name in self.defs:
            return SC_LOCAL
        if self.nested and (name in self.frees or name in self.uses):
            return SC_FREE
        if self.nested:
            return SC_UNKNOWN
        else:
            return SC_GLOBAL_IMPLICIT

    def get_free_vars(self):
        """Variables not defined in this scope, and that are not globals either.

        It must be like this:
        # def MakeAdder(inc):
        #  def Adder(x):
        #    return x + inc  # x is a local, inc is a free var?
        #  return Adder
        """
        if not self.nested:
            return []
        free = set()
        free.update(self.frees)
        for name in self.uses:
            if name not in self.defs and name not in self.globals:
                free.add(name)
        return list(free)

    def get_cell_vars(self):
        return list(self.cells)

    def handle_children(self):
        for child in self.children:
            frees = child.get_free_vars()
            globals_ = self.add_frees(frees)
            for name in globals_:
                child.force_global(name)

    def force_global(self, name):
        """Force name to be global in scope.

        Some child of the current node had a free reference to name.
        When the child was processed, it was labelled a free
        variable.  Now that all its enclosing scope have been
        processed, the name is known to be a global or builtin.  So
        walk back down the child chain and set the name to be global
        rather than free.

        Be careful to stop if a child does not think the name is
        free.
        """
        self.globals.add(name)
        if name in self.frees:
            self.frees.remove(name)
        for child in self.children:
            if child.check_name(name) == SC_FREE:
                child.force_global(name)

    def add_frees(self, names):
        """Process list of free vars from nested scope.

        Returns a list of names that are either 1) declared global in the
        parent or 2) undefined in a top-level parent.  In either case,
        the nested scope should treat them as globals.
        """
        child_globals = []
        for name in names:
            sc = self.check_name(name)
            if self.nested:
                if sc == SC_UNKNOWN or sc == SC_FREE \
                   or isinstance(self, ClassScope):
                    self.frees.add(name)
                elif sc == SC_GLOBAL_IMPLICIT:
                    child_globals.append(name)
                elif isinstance(self, FunctionScope) and sc == SC_LOCAL:
                    self.cells.add(name)
                elif sc != SC_CELL:
                    child_globals.append(name)
            else:
                if sc == SC_LOCAL:
                    self.cells.add(name)
                elif sc != SC_CELL:
                    child_globals.append(name)
        return child_globals


class ModuleScope(Scope):

    def __init__(self):
        Scope.__init__(self, "global", self)


class FunctionScope(Scope):
    pass


class GenExprScope(Scope):

    def __init__(self, name, module, klass=None):
        Scope.__init__(self, name, module, klass)
        self.add_param('.0')

    def get_names(self):
        keys = Scope.get_names(self)
        return keys


class LambdaScope(FunctionScope):
    pass


class ClassScope(Scope):
    pass



gLambdaCounter = 1
gGenExprCounter = 1


class SymbolVisitor(ASTVisitor):
    def __init__(self):
        ASTVisitor.__init__(self)
        self.scopes = {}  # node -> Scope instance, the "return value".
        self.klass = None

    # Nodes that define new scopes

    def visitModule(self, node):
        scope = self.module = self.scopes[node] = ModuleScope()
        self.visit(node.node, scope)

    visitExpression = visitModule

    def visitFunction(self, node, parent):
        if node.decorators:
            self.visit(node.decorators, parent)
        parent.add_def(node.name)
        for n in node.defaults:
            self.visit(n, parent)
        scope = FunctionScope(node.name, self.module, self.klass)
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1
        self.scopes[node] = scope
        self._do_args(scope, node.argnames)
        self.visit(node.code, scope)
        self.handle_free_vars(scope, parent)

    def visitGenExpr(self, node, parent):
        global gGenExprCounter
        obj_name = "generator expression<%d>" % gGenExprCounter
        gGenExprCounter += 1 

        scope = GenExprScope(obj_name, self.module, self.klass)

        if parent.nested or isinstance(parent, (FunctionScope, GenExprScope)):
            scope.nested = 1

        self.scopes[node] = scope
        self.visit(node.code, scope)

        self.handle_free_vars(scope, parent)

    def visitGenExprInner(self, node, scope):
        for genfor in node.quals:
            self.visit(genfor, scope)

        self.visit(node.expr, scope)

    def visitGenExprFor(self, node, scope):
        self.visit(node.assign, scope, 1)
        self.visit(node.iter, scope)
        for if_ in node.ifs:
            self.visit(if_, scope)

    def visitGenExprIf(self, node, scope):
        self.visit(node.test, scope)

    def visitLambda(self, node, parent, assign=0):
        # Lambda is an expression, so it could appear in an expression
        # context where assign is passed.  The transformer should catch
        # any code that has a lambda on the left-hand side.
        assert not assign

        for n in node.defaults:
            self.visit(n, parent)

        global gLambdaCounter
        obj_name = "lambda.%d" % gLambdaCounter
        gLambdaCounter += 1

        scope = LambdaScope(obj_name, self.module, klass=self.klass)

        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1
        self.scopes[node] = scope
        self._do_args(scope, node.argnames)
        self.visit(node.code, scope)
        self.handle_free_vars(scope, parent)

    def _do_args(self, scope, args):
        for name in args:
            if type(name) == types.TupleType:
                self._do_args(scope, name)
            else:
                scope.add_param(name)

    def handle_free_vars(self, scope, parent):
        parent.add_child(scope)
        scope.handle_children()

    def visitClass(self, node, parent):
        parent.add_def(node.name)
        for n in node.bases:
            self.visit(n, parent)
        scope = ClassScope(node.name, self.module)
        if parent.nested or isinstance(parent, FunctionScope):
            scope.nested = 1
        if node.doc is not None:
            scope.add_def('__doc__')
        scope.add_def('__module__')
        self.scopes[node] = scope
        prev = self.klass
        self.klass = node.name
        self.visit(node.code, scope)
        self.klass = prev
        self.handle_free_vars(scope, parent)

    # name can be a def or a use

    # XXX a few calls and nodes expect a third "assign" arg that is
    # true if the name is being used as an assignment.  only
    # expressions contained within statements may have the assign arg.

    def visitName(self, node, scope, assign=0):
        if assign:
            scope.add_def(node.name)
        else:
            scope.add_use(node.name)

    # operations that bind new names

    def visitFor(self, node, scope):
        self.visit(node.assign, scope, 1)
        self.visit(node.list, scope)
        self.visit(node.body, scope)
        if node.else_:
            self.visit(node.else_, scope)

    def visitFrom(self, node, scope):
        for name, asname in node.names:
            if name == "*":
                continue
            scope.add_def(asname or name)

    def visitImport(self, node, scope):
        for name, asname in node.names:
            i = name.find(".")
            if i > -1:
                name = name[:i]
            scope.add_def(asname or name)

    def visitGlobal(self, node, scope):
        for name in node.names:
            scope.add_global(name)

    def visitAssign(self, node, scope):
        """Propagate assignment flag down to child nodes.

        The Assign node doesn't itself contains the variables being
        assigned to.  Instead, the children in node.nodes are visited
        with the assign flag set to true.  When the names occur in
        those nodes, they are marked as defs.

        Some names that occur in an assignment target are not bound by
        the assignment, e.g. a name occurring inside a slice.  The
        visitor handles these nodes specially; they do not propagate
        the assign flag to their children.
        """
        for n in node.nodes:
            self.visit(n, scope, 1)
        self.visit(node.expr, scope)

    def visitAssName(self, node, scope, assign=1):
        scope.add_def(node.name)

    def visitAssAttr(self, node, scope, assign=0):
        self.visit(node.expr, scope, 0)

    def visitSubscript(self, node, scope, assign=0):
        self.visit(node.expr, scope, 0)
        for n in node.subs:
            self.visit(n, scope, 0)

    def visitSlice(self, node, scope, assign=0):
        self.visit(node.expr, scope, 0)
        if node.lower:
            self.visit(node.lower, scope, 0)
        if node.upper:
            self.visit(node.upper, scope, 0)

    def visitAugAssign(self, node, scope):
        # If the LHS is a name, then this counts as assignment.
        # Otherwise, it's just use.
        self.visit(node.node, scope)
        if isinstance(node.node, ast.Name):
            self.visit(node.node, scope, 1) # XXX worry about this
        self.visit(node.expr, scope)

    # prune if statements if tests are false

    _CONST_TYPES = (types.StringType, types.IntType, types.FloatType)

    def visitIf(self, node, scope):
        for test, body in node.tests:
            if isinstance(test, ast.Const):
                if isinstance(test.value, self._CONST_TYPES):
                    if not test.value:
                        continue
            self.visit(test, scope)
            self.visit(body, scope)
        if node.else_:
            self.visit(node.else_, scope)

    # a yield statement signals a generator

    def visitYield(self, node, scope):
        scope.generator = 1
        self.visit(node.value, scope)
